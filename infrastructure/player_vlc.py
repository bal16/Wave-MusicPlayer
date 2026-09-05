"""VLC implementation of PlayerBackend (primary).

Requires the python-vlc package plus a system VLC (libvlc). The import is
lazy so modules stay importable when libvlc is absent — construction raises
BackendUnavailableError instead, letting the container fall back.

libvlc 3 vs 4: version 4 removed the event-manager API, media parsing and
media_player_stop. End-of-media is delivered via events when available,
otherwise a small monitor thread polls for the natural end. stop() falls
back to pause + rewind. Duration shortfalls are covered by
PlayerService.get_duration(), which falls back to the song metadata.
"""

from __future__ import annotations

import threading
import time

from loguru import logger

from domain.interfaces import BackendUnavailableError, PlayerBackend

# Position tolerance (seconds) for natural-end detection on the poll path.
_END_EPSILON = 1.0
_POLL_INTERVAL = 0.2


def is_available() -> bool:
    """True when libvlc can instantiate a player on this machine.

    Probes deeper than Instance() alone: some libvlc builds (notably 4.0
    dev snapshots) create an Instance fine but fail at player creation.
    """
    try:
        import vlc

        instance = vlc.Instance("--no-video")
        instance.media_player_new()
        instance.release()
        return True
    except Exception:
        return False


class VlcBackend(PlayerBackend):
    def __init__(self) -> None:
        try:
            import vlc
        except ImportError as e:
            raise BackendUnavailableError(f"python-vlc not installed: {e}") from e
        try:
            self._vlc = vlc
            self._instance = vlc.Instance("--no-video")
            self._player = self._instance.media_player_new()
        except Exception as e:
            raise BackendUnavailableError(f"libvlc unavailable: {e}") from e

        self._end_callback = None
        self._paused_by_user = False
        self._expecting = False
        self._was_playing = False
        self._use_events = self._attach_end_event()
        self._monitor_started = False
        self._monitor_lock = threading.Lock()
        logger.info("Audio backend: VLC")

    # -- end-of-media delivery --

    def _attach_end_event(self) -> bool:
        """Use libvlc events when present (libvlc 3). False on libvlc 4+."""
        try:
            events = self._player.event_manager()
            events.event_attach(
                self._vlc.EventType.MediaPlayerEndReached,
                lambda _event: self._fire_end(),
            )
            return True
        except Exception as e:
            logger.warning(f"VLC event API unavailable, using end polling: {e}")
            return False

    def _ensure_monitor(self) -> None:
        with self._monitor_lock:
            if self._use_events or self._monitor_started:
                return
            self._monitor_started = True
        thread = threading.Thread(target=self._poll_end, daemon=True)
        thread.start()

    def _poll_end(self) -> None:
        while True:
            time.sleep(_POLL_INTERVAL)
            try:
                playing = bool(self._player.is_playing())
            except Exception:
                return
            if playing:
                self._was_playing = True
                continue
            if (
                self._expecting
                and self._was_playing
                and not self._paused_by_user
                and self.get_pos() >= max(0.0, self.get_duration() - _END_EPSILON)
            ):
                self._was_playing = False
                self._expecting = False
                self._fire_end()
            elif not self._expecting:
                self._was_playing = False

    def _fire_end(self) -> None:
        # Invoked on a VLC/poller thread — never touch widgets here.
        if self._end_callback is not None:
            try:
                self._end_callback()
            except Exception as e:
                logger.error(f"Error in media-end callback: {e}")

    def _disarm(self) -> None:
        self._expecting = False
        self._was_playing = False
        self._paused_by_user = False

    # -- PlayerBackend --

    def load(self, file_path: str) -> None:
        media = self._instance.media_new(file_path)
        # Blocking parse of a local file so get_duration() works reliably.
        # Absent on libvlc 4+ — failures are covered by metadata fallback.
        try:
            media.parse_with_options(self._vlc.MediaParseFlag.local, 5000)
        except Exception as e:
            logger.debug(f"VLC parse unavailable for {file_path!r}: {e}")
        self._disarm()
        self._player.set_media(media)

    def play(self) -> None:
        self._ensure_monitor()
        self._paused_by_user = False
        self._expecting = True
        self._player.play()

    def pause(self) -> None:
        self._paused_by_user = True
        self._player.set_pause(1)

    def stop(self) -> None:
        self._disarm()
        try:
            self._player.stop()
        except Exception:
            # libvlc 4 removed media_player_stop: pause + rewind instead.
            try:
                self._player.set_pause(1)
                self._player.set_time(0)
            except Exception as e:
                logger.warning(f"VLC stop fallback failed: {e}")

    def seek(self, seconds: float) -> None:
        self._player.set_time(max(0, int(seconds * 1000)))

    def set_volume(self, level: float) -> None:
        clamped = max(0.0, min(1.0, level))
        self._player.audio_set_volume(int(clamped * 100))

    def get_pos(self) -> float:
        return max(0.0, self._player.get_time() / 1000.0)

    def get_duration(self) -> float:
        media = self._player.get_media()
        duration_ms = None
        if media is not None:
            try:
                duration_ms = media.get_duration()
            except Exception:
                duration_ms = None
        if duration_ms is None or duration_ms < 0:
            try:
                duration_ms = self._player.get_length()
            except Exception:
                duration_ms = None
        return max(0.0, (duration_ms or 0) / 1000.0)

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def on_end(self, callback) -> None:
        self._end_callback = callback
