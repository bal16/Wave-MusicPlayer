"""Domain interfaces — contracts between layers.

Services only know the ABCs/protocols here, never SQLModel/VLC/TinyTag.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Protocol

from domain.entities import Playlist, Song, SongDraft

LIBRARY_CHANGED_EVENT = "library_changed"
PLAYLIST_CHANGED_EVENT = "playlist_changed"


class BackendUnavailableError(RuntimeError):
    """Raised when an audio backend cannot start (missing libvlc, no device)."""


class SongRepository(ABC):
    """Song persistence. Implemented by infrastructure.song_repository."""

    @abstractmethod
    def add_all(self, drafts: list[SongDraft]) -> int:
        """Insert missing rows (dedup by file_path). Return insert count."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, query: str = "", favorites_only: bool = False) -> list[Song]:
        """All songs, default ORDER BY added_at DESC."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, song_id: int) -> Song | None:
        """Fetch one song by id.

        Args:
            song_id: Primary key of the song row.

        Returns:
            The Song entity, or None when the id does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def toggle_favorite(self, song_id: int) -> bool | None:
        """Flip the flag. Return the new value, or None when id is missing."""
        raise NotImplementedError


class PlaylistRepository(ABC):
    """Playlist + link persistence. Implemented by infrastructure.playlist_repository."""

    @abstractmethod
    def create(self, name: str, description: str = "") -> Playlist:
        """Insert a playlist. Raises ValueError on blank names."""
        raise NotImplementedError

    @abstractmethod
    def rename(self, playlist_id: int, name: str) -> Playlist | None:
        """Rename. Returns None when id is missing; ValueError on blank names."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, playlist_id: int) -> bool:
        """Delete playlist + its links (CASCADE). Songs are never deleted."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Playlist]:
        """All playlists with song counts, ORDER BY created_at DESC."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Fetch one playlist by id.

        Args:
            playlist_id: Primary key of the playlist row.

        Returns:
            The Playlist entity (with song count), or None when missing.
        """
        raise NotImplementedError

    @abstractmethod
    def add_song(self, playlist_id: int, song_id: int) -> bool:
        """Link a song. Idempotent; False when playlist or song is missing."""
        raise NotImplementedError

    @abstractmethod
    def remove_song(self, playlist_id: int, song_id: int) -> bool:
        """Unlink a song (never deletes the song itself)."""
        raise NotImplementedError

    @abstractmethod
    def songs_in_playlist(self, playlist_id: int) -> list[Song]:
        """Songs of a playlist, ORDER BY song added_at DESC."""
        raise NotImplementedError


class AudioTagger(Protocol):
    """Parses audio-file metadata into a SongDraft."""

    def read(self, path: str) -> SongDraft | None:
        """Read tags of one audio file.

        Args:
            path: Absolute file path (may be unsupported — see below).

        Returns:
            A SongDraft, or None for unsupported formats / unreadable files.
        """
        ...


class CoverArtReader(Protocol):
    """Reads embedded cover art bytes from audio files."""

    def read_cover(self, path: str) -> bytes | None:
        """Read embedded cover art of one audio file.

        Args:
            path: Absolute file path.

        Returns:
            Raw image bytes (any common format), or None when the file
            has no embedded art or cannot be read.
        """
        ...


class EventBus:
    """Minimal synchronous bus. Callbacks must not touch widgets directly
    from a worker thread — views must wrap via after(0, ...)."""

    def __init__(self) -> None:
        """Start with an empty subscriber registry."""
        self._subs: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, listener: Callable) -> Callable:
        """Register a listener for an event.

        Args:
            event: Event name (e.g. LIBRARY_CHANGED_EVENT).
            listener: Callable invoked as listener(*args, **kwargs) on publish.

        Returns:
            An unsubscribe callable; calling it twice is safe.
        """
        self._subs.setdefault(event, []).append(listener)

        def _unsub() -> None:
            """Detach the listener; safe to call twice."""
            try:
                self._subs[event].remove(listener)
            except ValueError:
                pass

        return _unsub

    def publish(self, event: str, *args, **kwargs) -> None:
        """Synchronously notify all listeners of an event.

        Args:
            event: Event name to fire.
            *args: Positional payload forwarded to each listener.
            **kwargs: Keyword payload forwarded to each listener.

        Note:
            Runs on the caller's thread. Audio/worker-thread publishers
            must ensure UI listeners marshal via after(0, ...).
        """
        for listener in list(self._subs.get(event, [])):
            listener(*args, **kwargs)


class PlayerBackend(ABC):
    """Audio output contract. Implemented per engine (VLC, miniaudio).

    Primary: python-vlc. Fallback: miniaudio/just_playback when libvlc is absent.
    PlayerService only knows this ABC, so engines are swappable without
    touching services, controllers, or views.

    Threading: end-of-media callbacks fire on the engine's own audio
    thread — implementations must never touch widgets there.
    Time is always float seconds; volume is always 0.0 - 1.0.
    """

    @abstractmethod
    def load(self, file_path: str) -> None:
        """Load a file as the current media (does not start playback).

        Args:
            file_path: Absolute path of the audio file to load.

        Raises:
            BackendUnavailableError: When the file cannot be opened by
                this engine.
        """
        raise NotImplementedError

    @abstractmethod
    def play(self) -> None:
        """Start or resume playback of the loaded media."""
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        """Pause playback, keeping the current position."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Halt playback and reset the position to the start."""
        raise NotImplementedError

    @abstractmethod
    def seek(self, seconds: float) -> None:
        """Jump to a position.

        Args:
            seconds: Target position in seconds (clamped to the track).
        """
        raise NotImplementedError

    @abstractmethod
    def set_volume(self, level: float) -> None:
        """Set the output gain.

        Args:
            level: Volume level in 0.0 - 1.0 (clamped).
        """
        raise NotImplementedError

    @abstractmethod
    def get_pos(self) -> float:
        """Current playback position.

        Returns:
            Position in seconds (>= 0.0).
        """
        raise NotImplementedError

    @abstractmethod
    def get_duration(self) -> float:
        """Total length of the loaded media.

        Returns:
            Duration in seconds, or 0.0 when unknown.
        """
        raise NotImplementedError

    @abstractmethod
    def is_playing(self) -> bool:
        """Whether audio is currently being produced.

        Returns:
            True while playing, False when paused, stopped, or empty.
        """
        raise NotImplementedError

    def on_end(self, callback: Callable[[], None]) -> None:
        """Register a media-end callback (drives auto-next).

        Args:
            callback: Zero-arg callable invoked once per natural track
                end, on the engine's audio thread. No-op by default.
        """
        return None

    def close(self) -> None:
        """Release native resources. Called once on app shutdown, before
        interpreter teardown — never rely on __del__ for audio devices."""
        return None
