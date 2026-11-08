"""Unit tests for infrastructure/player_miniaudio.py.

The miniaudio module is replaced with an in-memory fake so no audio device is
opened; the frame-counting stream is driven directly with ``send()``.
"""

from __future__ import annotations

import array
import sys
import types

import pytest

from domain.interfaces import BackendUnavailableError
from infrastructure import player_miniaudio
from infrastructure.player_miniaudio import MiniaudioBackend, _apply_gain


class FakeSampleFormat:
    SIGNED16 = "SIGNED16"


class FakeDevice:
    instances: list[FakeDevice] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = None
        self.closed = 0
        self.close_error: Exception | None = None
        FakeDevice.instances.append(self)

    def start(self, stream) -> None:
        self.started = stream

    def close(self) -> None:
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


class FakeInfo:
    def __init__(self, duration: float | None) -> None:
        self.duration = duration


def make_miniaudio_module():
    module = types.ModuleType("miniaudio")
    module.SampleFormat = FakeSampleFormat
    module.PlaybackDevice = FakeDevice
    module.chunks: list = []
    module.duration = 10.0

    module.get_file_info = lambda path: FakeInfo(module.duration)
    module.stream_file = lambda *args, **kwargs: iter(module.chunks)
    return module


@pytest.fixture()
def miniaudio(monkeypatch):
    module = make_miniaudio_module()
    monkeypatch.setitem(sys.modules, "miniaudio", module)
    FakeDevice.instances.clear()
    return module


@pytest.fixture()
def backend(miniaudio):
    return MiniaudioBackend()


def _load(backend: MiniaudioBackend, path="/m/song.mp3", duration=10.0) -> None:
    backend._miniaudio.duration = duration
    backend.load(path)


# -- helpers / availability --


def test_apply_gain_scales_signed16_samples():
    chunk = array.array("h", [100, -100, 0])
    assert _apply_gain(chunk, 0.5) is chunk
    assert list(chunk) == [50, -50, 0]


def test_apply_gain_clamps_to_int16_range():
    chunk = array.array("h", [32767, -32768])
    _apply_gain(chunk, 2.0)
    assert list(chunk) == [32767, -32768]


def test_is_available_false_without_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "miniaudio", None)
    assert player_miniaudio.is_available() is False


def test_is_available_delegates_to_subprocess_probe(monkeypatch, miniaudio):
    monkeypatch.setattr(player_miniaudio, "_probe_in_subprocess", lambda code: True)
    assert player_miniaudio.is_available() is True
    monkeypatch.setattr(player_miniaudio, "_probe_in_subprocess", lambda code: False)
    assert player_miniaudio.is_available() is False


def test_construction_raises_without_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "miniaudio", None)
    with pytest.raises(BackendUnavailableError, match="miniaudio"):
        MiniaudioBackend()


def test_construction_starts_idle(backend, miniaudio):
    assert backend._miniaudio is miniaudio
    assert backend._device is None
    assert backend._file_path is None
    assert backend._duration == 0.0
    assert backend._frames_played == 0
    assert backend._playing is False
    assert backend._volume == 1.0
    assert backend._end_callback is None


def test_total_frames_uses_sample_rate(backend):
    backend._duration = 2.0
    assert backend._total_frames() == 2 * player_miniaudio._SAMPLE_RATE


# -- counting stream --


def _prime(stream):
    first = next(stream)
    assert isinstance(first, array.array)
    assert len(first) == 0


def test_counting_stream_delivers_exact_frames_and_tracks_position(backend, miniaudio):
    miniaudio.chunks = [array.array("h", [1, 2, 3, 4]), array.array("h", [5, 6])]
    _load(backend)
    backend._stream_token = 1
    stream = backend._counting_stream(0, 1)
    _prime(stream)

    assert list(stream.send(1)) == [1, 2]
    assert list(stream.send(2)) == [3, 4, 5, 6]
    assert backend._frames_played == 3

    with pytest.raises(StopIteration):
        stream.send(1)
    assert backend._playing is False  # _finish_stream marked it stopped


def test_counting_stream_applies_stored_volume(backend, miniaudio):
    miniaudio.chunks = [array.array("h", [100, -100])]
    _load(backend)
    backend._volume = 0.5
    backend._stream_token = 1
    stream = backend._counting_stream(0, 1)
    _prime(stream)

    assert list(stream.send(1)) == [50, -50]


def test_counting_stream_stops_when_token_is_superseded(backend, miniaudio):
    miniaudio.chunks = [array.array("h", [1, 2])]
    _load(backend)
    backend._stream_token = 1
    stream = backend._counting_stream(0, 1)
    _prime(stream)

    backend._stream_token = 2
    with pytest.raises(StopIteration):
        stream.send(1)


def test_counting_stream_rechecks_token_after_reading_a_chunk(backend, miniaudio):
    class SupersedingChunks:
        def __iter__(self):
            return self

        def __next__(self):
            backend._stream_token = 2  # a newer stream started mid-read
            return array.array("h", [1, 2])

    miniaudio.stream_file = lambda *a, **k: SupersedingChunks()
    _load(backend)
    backend._stream_token = 1
    stream = backend._counting_stream(0, 1)
    _prime(stream)

    with pytest.raises(StopIteration):
        stream.send(1)
    assert backend._frames_played == 0


def test_counting_stream_skips_empty_requests(backend, miniaudio):
    miniaudio.chunks = [array.array("h", [1, 2])]
    _load(backend)
    backend._stream_token = 1
    stream = backend._counting_stream(0, 1)
    _prime(stream)

    assert len(stream.send(0)) == 0
    assert list(stream.send(1)) == [1, 2]


class ImmediateThread:
    def __init__(self, target, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon

    def start(self):
        self.target(*self.args)


def test_finish_stream_fires_callback_once_on_daemon_thread(monkeypatch, backend):
    calls = []
    backend._end_callback = lambda: calls.append(1)
    threads = []

    def factory(*args, **kwargs):
        thread = ImmediateThread(*args, **kwargs)
        threads.append(thread)
        return thread

    monkeypatch.setattr(player_miniaudio.threading, "Thread", factory)
    backend._stream_token = 1
    backend._playing = True

    backend._finish_stream(1)

    assert calls == [1]
    assert threads[0].daemon is True
    assert backend._playing is False
    assert backend._end_fired is True


def test_finish_stream_ignores_stale_or_repeated(backend):
    calls = []
    backend._end_callback = lambda: calls.append(1)
    backend._stream_token = 2

    backend._finish_stream(1)
    assert calls == []

    backend._stream_token = 2
    backend._end_fired = True
    backend._finish_stream(2)
    assert calls == []


def test_finish_stream_without_callback(backend):
    backend._stream_token = 1
    backend._finish_stream(1)
    assert backend._playing is False


def test_invoke_end_callback_swallows_errors(backend):
    def boom():
        raise RuntimeError("bad callback")

    backend._invoke_end_callback(boom)  # must not raise


# -- device lifecycle --


def test_open_device_closes_previous(backend):
    old = FakeDevice()
    backend._device = old
    backend._open_device()
    assert old.closed == 1
    assert backend._device is not old


def test_close_device_swallows_errors(backend):
    device = FakeDevice()
    device.close_error = RuntimeError("close failed")
    backend._device = device
    backend._close_device()  # must not raise
    assert backend._device is None


def test_start_stream_primes_and_starts_device(backend, monkeypatch):
    opened = []
    monkeypatch.setattr(backend, "_open_device", lambda: opened.append(1))
    backend._stream_token = 7
    device = FakeDevice()
    backend._device = device

    backend._start_stream(0)

    assert opened == [1]
    assert backend._stream_token == 8
    assert backend._end_fired is False
    assert device.started is not None


def test_start_stream_finishes_immediately_when_nothing_to_stream(backend, monkeypatch):
    monkeypatch.setattr(backend, "_open_device", lambda: None)
    finished = []
    monkeypatch.setattr(backend, "_finish_stream", lambda token: finished.append(token))

    def empty():
        if False:
            yield None

    monkeypatch.setattr(backend, "_counting_stream", lambda seek, token: empty())
    backend._stream_token = 1
    backend._start_stream(0)

    assert finished == [2]
    assert backend._device is None


# -- PlayerBackend --


def test_load_probes_file_and_resets_state(backend, miniaudio):
    backend._frames_played = 123
    _load(backend, "/m/a.flac", duration=12.5)
    assert backend._file_path == "/m/a.flac"
    assert backend._duration == 12.5
    assert backend._frames_played == 0
    assert backend._playing is False


def test_load_handles_missing_duration(backend, miniaudio):
    miniaudio.duration = None
    backend.load("/m/a.flac")
    assert backend._duration == 0.0


def test_load_propagates_probe_errors(backend, miniaudio):
    def boom(path):
        raise BackendUnavailableError("cannot probe")

    miniaudio.get_file_info = boom
    with pytest.raises(BackendUnavailableError):
        backend.load("/m/a.mp3")


def test_play_without_file_is_noop(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend.play()
    assert started == []
    assert backend._playing is False


def test_play_when_already_playing_is_noop(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend._file_path = "/m/a.mp3"
    backend._playing = True
    backend.play()
    assert started == []


def test_play_starts_from_stored_frame(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend._file_path = "/m/a.mp3"
    backend._duration = 10.0
    backend._frames_played = player_miniaudio._SAMPLE_RATE * 2
    backend.play()
    assert started == [player_miniaudio._SAMPLE_RATE * 2]
    assert backend._playing is True


def test_play_clamps_start_frame_to_duration(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend._file_path = "/m/a.mp3"
    backend._duration = 1.0
    backend._frames_played = 10**9
    backend.play()
    assert started == [player_miniaudio._SAMPLE_RATE]


def test_pause_when_not_playing_is_noop(backend, monkeypatch):
    closed = []
    monkeypatch.setattr(backend, "_close_device", lambda: closed.append(1))
    backend.pause()
    assert closed == []


def test_pause_retires_stream_and_closes_device(backend, monkeypatch):
    closed = []
    monkeypatch.setattr(backend, "_close_device", lambda: closed.append(1))
    backend._playing = True
    token = getattr(backend, "_stream_token", 0)
    backend.pause()
    assert backend._playing is False
    assert backend._stream_token == token + 1
    assert closed == [1]


def test_stop_resets_state(backend):
    backend._file_path = "/m/a.mp3"
    backend._playing = True
    backend._frames_played = 100
    backend.stop()
    assert backend._playing is False
    assert backend._frames_played == 0


def test_close_resets_state_and_drops_callback(backend):
    device = FakeDevice()
    backend._device = device
    backend._playing = True
    backend._end_callback = lambda: None
    backend.close()
    assert backend._playing is False
    assert backend._end_fired is True
    assert backend._end_callback is None
    assert device.closed == 1


def test_seek_without_file_is_noop(backend):
    backend.seek(5)
    assert backend._frames_played == 0


def test_seek_clamps_and_resumes_when_playing(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend._file_path = "/m/a.mp3"
    backend._duration = 10.0
    backend._playing = True

    backend.seek(999)
    assert backend._frames_played == 10 * player_miniaudio._SAMPLE_RATE
    assert started == [10 * player_miniaudio._SAMPLE_RATE]

    backend.seek(-5)
    assert backend._frames_played == 0


def test_seek_does_not_resume_when_paused(backend, monkeypatch):
    started = []
    monkeypatch.setattr(backend, "_start_stream", lambda frame: started.append(frame))
    backend._file_path = "/m/a.mp3"
    backend._duration = 10.0
    backend._playing = False
    backend.seek(2)
    assert backend._frames_played == 2 * player_miniaudio._SAMPLE_RATE
    assert started == []


def test_set_volume_clamps(backend):
    backend.set_volume(0.5)
    assert backend._volume == 0.5
    backend.set_volume(3)
    assert backend._volume == 1.0
    backend.set_volume(-1)
    assert backend._volume == 0.0


def test_get_pos_get_duration_is_playing(backend):
    backend._frames_played = player_miniaudio._SAMPLE_RATE * 3
    backend._duration = 9.0
    backend._playing = True
    assert backend.get_pos() == 3.0
    assert backend.get_duration() == 9.0
    assert backend.is_playing() is True


def test_on_end_registers_callback(backend):
    def callback() -> None:
        pass

    backend.on_end(callback)
    assert backend._end_callback is callback
