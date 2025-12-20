from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class PlaylistSongLink(SQLModel, table=True):
    playlist_id: Optional[int] = Field(
        default=None, foreign_key="playlist.id", primary_key=True
    )
    song_id: Optional[int] = Field(
        default=None, foreign_key="song.id", primary_key=True
    )

class Song(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    
    file_path: str = Field(unique=True, index=True) 
    duration: float = 0.0
    
    is_favorite: bool = Field(default=False)
    added_at: datetime = Field(default_factory=datetime.now)

    playlists: List["Playlist"] = Relationship(
        back_populates="songs", link_model=PlaylistSongLink
    )

class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Relasi ke Songs
    songs: List["Song"] = Relationship(
        back_populates="playlists", link_model=PlaylistSongLink
    )