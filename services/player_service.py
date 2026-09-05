"""PlayerService — F3 (Play) logic: queue, state, auto-next.

Owns the play queue (full library order, starting at the clicked song) and
player state. Knows only the PlayerBackend ABC — VLC vs miniaudio is chosen
in app/container.py. Backend callbacks arrive on audio threads; listeners
must marshal UI updates themselves (the controller uses view.after).
"""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from domain.entities import Song
from domain.interfaces import PlayerBackend

TRACK_CHANGED_EVENT = "track_changed"
STATE_CHANGED_EVENT = "state_changed"


class PlayerService:
    def __init__(self, backend: PlayerBackend):
        self._backend = backend
        self._queue: list[Song] = []
        self._index = 0
        self._volume = 1.0
        self._muted = False
        self._listeners: dict[str, list[Callable]] = {}
        backend.on_end(self._on_media_end)

    # -- listeners --

    def subscribe(self, event: str, listener: Callable) -> None:
        self._listeners.setdefault(event, []).append(listener)

    def _publish(self, event: str, *args, **kwargs) -> None:
        for listener in list(self._listeners.get(event, [])):
            listener(*args, **kwargs)

    # -- state --

    @property
    def current(self) -> Song | None:
        if 0 <= self._index < len(self._queue):
            return self._queue[self._index]
        return None

    @property
    def is_playing(self) -> bool:
        return self._backend.is_playing()

    @property
    def volume(self) -> float:
        return 0.0 if self._muted else self._volume

    def get_pos(self) -> float:
        return self._backend.get_pos()

    def get_duration(self) -> float:
        duration = self._backend.get_duration()
        if duration <= 0 and self.current is not None:
            return float(self.current.duration or 0.0)
        return duration

    # -- transport --

    def play_queue(self, songs: list[Song], index: int = 0) -> Song | None:
        """Replace the queue and start playing at index."""
        if not songs:
            return None
        self._queue = list(songs)
        self._index = max(0, min(index, len(self._queue) - 1))
        self._play_current()
        return self.current

    def play_pause(self) -> bool:
        """Toggle. Returns True when now playing."""
        if self.current is None:
            return False
        if self._backend.is_playing():
            self._backend.pause()
        else:
            self._backend.play()
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._backend.is_playing()

    def next(self) -> Song | None:
        if not self._queue:
            return None
        self._index = (self._index + 1) % len(self._queue)
        self._play_current()
        return self.current

    def prev(self) -> Song | None:
        if not self._queue:
            return None
        # Restart the song when well into it; otherwise step back.
        if self._backend.get_pos() > 3.0:
            self._backend.seek(0.0)
            return self.current
        self._index = (self._index - 1) % len(self._queue)
        self._play_current()
        return self.current

    def seek(self, seconds: float) -> float:
        """Seek clamped to [0, duration]. Returns the applied position."""
        duration = self.get_duration()
        target = max(0.0, min(seconds, duration)) if duration > 0 else max(0.0, seconds)
        self._backend.seek(target)
        return target

    def set_volume(self, level: float) -> float:
        self._volume = max(0.0, min(1.0, level))
        self._muted = False
        self._backend.set_volume(self._volume)
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._volume

    def toggle_mute(self) -> bool:
        """Returns True when now muted."""
        self._muted = not self._muted
        self._backend.set_volume(0.0 if self._muted else self._volume)
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._muted

    # -- internals --

    def _play_current(self) -> None:
        song = self.current
        if song is None:
            return
        logger.info(f"Now playing: {song.title} - {song.artist}")
        self._backend.load(song.file_path)
        self._backend.set_volume(0.0 if self._muted else self._volume)
        self._backend.play()
        self._publish(TRACK_CHANGED_EVENT, song=song)
        self._publish(STATE_CHANGED_EVENT, playing=True)

    def _on_media_end(self) -> None:
        # Arrives on the backend's audio thread — wrap to the first song
        # (locked decision: full-library queue + wrap).
        if not self._queue:
            return
        self._index = (self._index + 1) % len(self._queue)
        self._play_current()
