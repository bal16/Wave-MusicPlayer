"""SQLModel tables — canonical schema source (see docs/schema.md).

Canonical location. models/schema.py stays as a re-export shim so legacy
code and old tests keep working during the gradual migration.
"""

# ruff: noqa: UP006, UP035, UP045, I001 -- annotations mirror the legacy schema verbatim;
# typing.List/Optional are required at runtime by the SQLModel mapper on SA 2.0 (verified).

from datetime import UTC, datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PlaylistSongLink(SQLModel, table=True):
    playlist_id: Optional[int] = Field(default=None, foreign_key="playlist.id", primary_key=True)
    song_id: Optional[int] = Field(default=None, foreign_key="song.id", primary_key=True)


class Song(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"

    file_path: str = Field(unique=True, index=True)
    duration: float = 0.0

    is_favorite: bool = Field(default=False)
    added_at: datetime = Field(default_factory=_utcnow)

    playlists: List["Playlist"] = Relationship(back_populates="songs", link_model=PlaylistSongLink)


class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)

    songs: List["Song"] = Relationship(back_populates="playlists", link_model=PlaylistSongLink)
