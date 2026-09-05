"""Domain entities — pure Python, no SQLModel / Tk imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SongDraft:
    """Parsed tagger result, no id assigned yet."""

    title: str
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    file_path: str = ""
    duration: float = 0.0


@dataclass(frozen=True, slots=True)
class Song:
    """Entity used by services / controllers / views."""

    id: int | None
    title: str
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    file_path: str = ""
    duration: float = 0.0
    is_favorite: bool = False
    added_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True, slots=True)
class Playlist:
    """Entity used by services / controllers / views."""

    id: int | None
    name: str
    description: str = ""
    song_count: int = 0
    created_at: datetime = field(default_factory=_utcnow)
