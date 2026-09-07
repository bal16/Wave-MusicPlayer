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
    """Owns the play queue, transport state, and engine event fan-out.

    Args:
        backend: Audio engine implementing PlayerBackend. Chosen by
            app/container.py; this service never knows VLC vs miniaudio.

    Events published (subscribe to these, never to the backend directly):
        TRACK_CHANGED_EVENT: fired with the new Song on every track start.
        STATE_CHANGED_EVENT: fired with playing=bool on play/pause/stop/
            mute changes.
    """

    def __init__(self, backend: PlayerBackend):
        """Wire a backend and start with an empty queue (see class docs)."""
        self._backend = backend
        self._queue: list[Song] = []
        self._index = 0
        self._volume = 1.0
        self._muted = False
        self._listeners: dict[str, list[Callable]] = {}
        backend.on_end(self._on_media_end)

    # -- listeners --

    def subscribe(self, event: str, listener: Callable) -> None:
        """Register a listener for a service event.

        Args:
            event: TRACK_CHANGED_EVENT or STATE_CHANGED_EVENT.
            listener: Callable receiving the event payload as kwargs.
        """
        self._listeners.setdefault(event, []).append(listener)

    def _publish(self, event: str, *args, **kwargs) -> None:
        """Synchronously notify listeners on the caller's thread.

        Args:
            event: Event name to fire.
            *args: Positional payload forwarded to each listener.
            **kwargs: Keyword payload forwarded to each listener.
        """
        for listener in list(self._listeners.get(event, [])):
            listener(*args, **kwargs)

    # -- state --

    @property
    def current(self) -> Song | None:
        """The song at the queue cursor.

        Returns:
            The current Song, or None when the queue is empty.
        """
        if 0 <= self._index < len(self._queue):
            return self._queue[self._index]
        return None

    @property
    def is_playing(self) -> bool:
        """Whether the engine is currently producing audio.

        Returns:
            True while playing, False otherwise.
        """
        return self._backend.is_playing()

    @property
    def volume(self) -> float:
        """Effective output gain.

        Returns:
            0.0 when muted, otherwise the stored level in 0.0 - 1.0.
        """
        return 0.0 if self._muted else self._volume

    def get_pos(self) -> float:
        """Current playback position.

        Returns:
            Position in seconds (>= 0.0).
        """
        return self._backend.get_pos()

    def get_duration(self) -> float:
        """Total length of the current track.

        Returns:
            Engine duration in seconds, falling back to the library
            metadata when the engine reports nothing useful.
        """
        duration = self._backend.get_duration()
        if duration <= 0 and self.current is not None:
            return float(self.current.duration or 0.0)
        return duration

    # -- transport --

    def play_queue(self, songs: list[Song], index: int = 0) -> Song | None:
        """Replace the queue and start playing at index.

        Args:
            songs: New queue order (copied; later caller mutations are ignored).
            index: Start position, clamped into range.

        Returns:
            The song that started playing, or None for an empty list.
        """
        if not songs:
            return None
        self._queue = list(songs)
        self._index = max(0, min(index, len(self._queue) - 1))
        self._play_current()
        return self.current

    def play_pause(self) -> bool:
        """Toggle playback.

        Returns:
            True when now playing, False when paused or queue is empty.
        """
        if self.current is None:
            return False
        if self._backend.is_playing():
            self._backend.pause()
        else:
            self._backend.play()
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._backend.is_playing()

    def next(self) -> Song | None:
        """Advance to the next track, wrapping to the first at the end.

        Returns:
            The song that started playing, or None for an empty queue.
        """
        if not self._queue:
            return None
        self._index = (self._index + 1) % len(self._queue)
        self._play_current()
        return self.current

    def prev(self) -> Song | None:
        """Go back, or restart the song when well into it (> 3s).

        Returns:
            The song that started (or restarted) playing, or None for
            an empty queue.
        """
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
        """Jump to a position in the current track.

        Args:
            seconds: Target position; clamped to [0, duration] when the
                duration is known, to >= 0.0 otherwise.

        Returns:
            The applied position in seconds.
        """
        duration = self.get_duration()
        target = max(0.0, min(seconds, duration)) if duration > 0 else max(0.0, seconds)
        self._backend.seek(target)
        return target

    def set_volume(self, level: float) -> float:
        """Set the output gain (also unmutes).

        Args:
            level: Desired gain, clamped to 0.0 - 1.0.

        Returns:
            The stored gain after clamping.
        """
        self._volume = max(0.0, min(level, 1.0))
        self._muted = False
        self._backend.set_volume(self._volume)
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._volume

    def toggle_mute(self) -> bool:
        """Flip the mute flag.

        Returns:
            True when now muted, False when unmuted.
        """
        self._muted = not self._muted
        self._backend.set_volume(0.0 if self._muted else self._volume)
        self._publish(STATE_CHANGED_EVENT, playing=self._backend.is_playing())
        return self._muted

    def stop(self) -> None:
        """Clear the queue, halt the engine, and publish the stopped state."""
        self._queue = []
        self._index = 0
        self._backend.stop()
        self._publish(STATE_CHANGED_EVENT, playing=False)

    def shutdown(self) -> None:
        """Halt playback and release the backend. Called once on app exit,
        before Tk teardown — never leave the device open for __del__."""
        try:
            self.stop()
        finally:
            self._backend.close()

    # -- internals --

    def _play_current(self) -> None:
        """Load and start the queue cursor, then publish both events.

        No-op when the queue is empty.
        """
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
        """Advance on natural track end, wrapping to the first song.

        Arrives on the backend's audio thread (locked decision:
        full-library queue + wrap). No-op for an empty queue.
        """
        # Arrives on the backend's audio thread — wrap to the first song
        # (locked decision: full-library queue + wrap).
        if not self._queue:
            return
        self._index = (self._index + 1) % len(self._queue)
        self._play_current()
