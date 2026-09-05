"""miniaudio implementation of PlayerBackend (fallback).

Pure pip install, no system dependency. Playback runs on miniaudio's own
thread; position is tracked by counting decoded frames, which keeps seek
deterministic. Seeking and resume reopen the file stream at a frame offset.
"""

from __future__ import annotations

import threading

from loguru import logger

from domain.interfaces import BackendUnavailableError, PlayerBackend
from infrastructure.probe import probe_in_subprocess as _probe_in_subprocess

_CHANNELS = 2
_SAMPLE_RATE = 44100

_S16_MIN = -32768
_S16_MAX = 32767


def _apply_gain(chunk, gain: float):
    """Scale SIGNED16 samples in place, clamped to int16 range."""
    for i, sample in enumerate(chunk):
        scaled = int(sample * gain)
        chunk[i] = _S16_MIN if scaled < _S16_MIN else _S16_MAX if scaled > _S16_MAX else scaled
    return chunk


def is_available() -> bool:
    """True when a miniaudio playback device can be opened here.

    Probed in a subprocess: device enumeration can abort at C level on
    systems without a usable audio device.
    """
    try:
        import miniaudio  # noqa: F401 -- fast fail when miniaudio is missing
    except ImportError:
        return False
    return _probe_in_subprocess(
        "import miniaudio;"
        " d = miniaudio.PlaybackDevice("
        " output_format=miniaudio.SampleFormat.SIGNED16,"
        " nchannels=2, sample_rate=44100);"
        " d.close()"
    )


class MiniaudioBackend(PlayerBackend):
    def __init__(self) -> None:
        try:
            import miniaudio
        except ImportError as e:
            raise BackendUnavailableError(f"miniaudio not installed: {e}") from e
        self._miniaudio = miniaudio
        self._lock = threading.Lock()
        self._device = None
        self._file_path: str | None = None
        self._duration = 0.0
        self._frames_played = 0
        self._playing = False
        self._volume = 1.0
        self._end_callback = None
        self._end_fired = False
        logger.info("Audio backend: miniaudio (fallback)")

    # -- internals --

    def _total_frames(self) -> int:
        return int(self._duration * _SAMPLE_RATE)

    def _counting_stream(self, seek_frame: int, token: int):
        """Yield decoded chunks while counting frames for position/end.

        Volume is applied here as software gain: pyminiaudio's device
        classes offer no stable volume API across versions, while the
        SIGNED16 samples are always ours to scale.
        """
        miniaudio = self._miniaudio
        stream = miniaudio.stream_file(
            self._file_path,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=_CHANNELS,
            sample_rate=_SAMPLE_RATE,
            seek_frame=seek_frame,
        )
        for chunk in stream:
            with self._lock:
                if token != self._stream_token:
                    return  # superseded by a newer stream
                self._frames_played += len(chunk) // _CHANNELS
                gain = self._volume
            yield chunk if gain >= 1.0 else _apply_gain(chunk, gain)
        self._finish_stream(token)

    def _finish_stream(self, token: int) -> None:
        # Runs on miniaudio's thread — never touch widgets here.
        with self._lock:
            if token != self._stream_token or self._end_fired:
                return
            self._end_fired = True
            self._playing = False
        if self._end_callback is not None:
            try:
                self._end_callback()
            except Exception as e:
                logger.error(f"Error in media-end callback: {e}")

    def _open_device(self) -> None:
        miniaudio = self._miniaudio
        self._close_device()
        self._device = miniaudio.PlaybackDevice(
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=_CHANNELS,
            sample_rate=_SAMPLE_RATE,
        )

    def _close_device(self) -> None:
        if self._device is not None:
            try:
                self._device.close()
            except Exception as e:
                logger.warning(f"Error closing audio device: {e}")
            self._device = None

    def _start_stream(self, seek_frame: int) -> None:
        self._stream_token = getattr(self, "_stream_token", 0) + 1
        self._end_fired = False
        self._open_device()
        stream = self._counting_stream(seek_frame, self._stream_token)
        # Prime the generator: the device sends into it immediately, which
        # raises on a just-started generator. The primed chunk is never
        # heard, so subtract it back from the position count.
        first = next(stream, None)
        if first is None:
            self._finish_stream(self._stream_token)
            return
        with self._lock:
            self._frames_played -= len(first) // _CHANNELS
        self._device.start(stream)

    # -- PlayerBackend --

    def load(self, file_path: str) -> None:
        info = self._miniaudio.get_file_info(file_path)
        with self._lock:
            self.stop_locked()
            self._file_path = file_path
            self._duration = float(info.duration or 0.0)
            self._frames_played = 0

    def play(self) -> None:
        with self._lock:
            if self._file_path is None:
                return
            if self._playing:
                return
            seek_frame = min(self._frames_played, self._total_frames())
            self._playing = True
        self._start_stream(seek_frame)

    def pause(self) -> None:
        with self._lock:
            if not self._playing:
                return
            self._playing = False
            self._stream_token = getattr(self, "_stream_token", 0) + 1
        self._close_device()

    def stop(self) -> None:
        with self._lock:
            self.stop_locked()

    def stop_locked(self) -> None:
        self._playing = False
        self._frames_played = 0
        self._stream_token = getattr(self, "_stream_token", 0) + 1
        self._close_device()

    def seek(self, seconds: float) -> None:
        with self._lock:
            if self._file_path is None:
                return
            target = int(max(0.0, min(seconds, self._duration)) * _SAMPLE_RATE)
            self._frames_played = target
            resume = self._playing
        if resume:
            self._start_stream(target)

    def set_volume(self, level: float) -> None:
        # Stored gain applied per chunk in _counting_stream (no device call).
        with self._lock:
            self._volume = max(0.0, min(1.0, level))

    def get_pos(self) -> float:
        with self._lock:
            return self._frames_played / _SAMPLE_RATE

    def get_duration(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        with self._lock:
            return self._playing

    def on_end(self, callback) -> None:
        self._end_callback = callback
