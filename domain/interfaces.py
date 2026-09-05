"""Domain interfaces — contracts between layers.

Services only know the ABCs/protocols here, never SQLModel/VLC/TinyTag.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Protocol

from domain.entities import Song, SongDraft

LIBRARY_CHANGED_EVENT = "library_changed"


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
        raise NotImplementedError

    @abstractmethod
    def toggle_favorite(self, song_id: int) -> bool | None:
        """Flip the flag. Return the new value, or None when id is missing."""
        raise NotImplementedError


class AudioTagger(Protocol):
    def read(self, path: str) -> SongDraft | None: ...


class EventBus:
    """Minimal synchronous bus. Callbacks must not touch widgets directly
    from a worker thread — views must wrap via after(0, ...)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, listener: Callable) -> Callable:
        self._subs.setdefault(event, []).append(listener)

        def _unsub() -> None:
            try:
                self._subs[event].remove(listener)
            except ValueError:
                pass

        return _unsub

    def publish(self, event: str, *args, **kwargs) -> None:
        for listener in list(self._subs.get(event, [])):
            listener(*args, **kwargs)


class PlayerBackend(ABC):
    """Slot for Phase 2 (F3 Play). Defined now so PlayerService never
    knows VLC vs fallback.

    Primary: python-vlc. Fallback: miniaudio/just_playback when libvlc is absent.
    """

    @abstractmethod
    def load(self, file_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def play(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def pause(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def seek(self, seconds: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_volume(self, level: float) -> None:
        """Volume level in 0.0 - 1.0."""
        raise NotImplementedError

    @abstractmethod
    def get_pos(self) -> float:
        """Current position in seconds."""
        raise NotImplementedError

    @abstractmethod
    def get_duration(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def is_playing(self) -> bool:
        raise NotImplementedError

    def on_end(self, callback: Callable[[], None]) -> None:
        """Register a media-end callback (auto-next). No-op by default."""
        return None
