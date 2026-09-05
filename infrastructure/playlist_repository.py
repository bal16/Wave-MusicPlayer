"""SQLModel implementation of PlaylistRepository."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, func, select

from domain.entities import Playlist as DomainPlaylist
from domain.entities import Song as DomainSong
from domain.interfaces import PlaylistRepository
from infrastructure.models import Playlist as PlaylistRow
from infrastructure.models import PlaylistSongLink as LinkRow
from infrastructure.models import Song as SongRow
from infrastructure.song_repository import _to_entity as _song_to_entity


def _to_entity(row: PlaylistRow, song_count: int = 0) -> DomainPlaylist:
    return DomainPlaylist(
        id=row.id,
        name=row.name,
        description=row.description or "",
        song_count=song_count,
        created_at=row.created_at,
    )


class SqlPlaylistRepository(PlaylistRepository):
    def __init__(self, engine: Engine):
        self._engine = engine

    def create(self, name: str, description: str = "") -> DomainPlaylist:
        clean = name.strip()
        if not clean:
            raise ValueError("Playlist name must not be blank")
        with Session(self._engine) as session:
            row = PlaylistRow(name=clean, description=description or None)
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_entity(row)

    def rename(self, playlist_id: int, name: str) -> DomainPlaylist | None:
        clean = name.strip()
        if not clean:
            raise ValueError("Playlist name must not be blank")
        with Session(self._engine) as session:
            row = session.get(PlaylistRow, playlist_id)
            if row is None:
                return None
            row.name = clean
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_entity(row, self._count_links(session, playlist_id))

    def delete(self, playlist_id: int) -> bool:
        with Session(self._engine) as session:
            row = session.get(PlaylistRow, playlist_id)
            if row is None:
                return False
            # Links go with it via relationship cascade; songs are untouched.
            session.delete(row)
            session.commit()
            return True

    def list_all(self) -> list[DomainPlaylist]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(PlaylistRow).order_by(col(PlaylistRow.created_at).desc())
            ).all()
            return [_to_entity(r, self._count_links(session, r.id)) for r in rows]

    def get_by_id(self, playlist_id: int) -> DomainPlaylist | None:
        with Session(self._engine) as session:
            row = session.get(PlaylistRow, playlist_id)
            if row is None:
                return None
            return _to_entity(row, self._count_links(session, playlist_id))

    def add_song(self, playlist_id: int, song_id: int) -> bool:
        with Session(self._engine) as session:
            if session.get(PlaylistRow, playlist_id) is None:
                return False
            if session.get(SongRow, song_id) is None:
                return False
            existing = session.get(LinkRow, (playlist_id, song_id))
            if existing is not None:
                return True  # idempotent
            session.add(LinkRow(playlist_id=playlist_id, song_id=song_id))
            session.commit()
            return True

    def remove_song(self, playlist_id: int, song_id: int) -> bool:
        with Session(self._engine) as session:
            link = session.get(LinkRow, (playlist_id, song_id))
            if link is None:
                return False
            session.delete(link)
            session.commit()
            return True

    def songs_in_playlist(self, playlist_id: int) -> list[DomainSong]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(SongRow)
                .join(LinkRow, LinkRow.song_id == SongRow.id)
                .where(LinkRow.playlist_id == playlist_id)
                .order_by(col(SongRow.added_at).desc())
            ).all()
            return [_song_to_entity(r) for r in rows]

    @staticmethod
    def _count_links(session: Session, playlist_id: int) -> int:
        result = session.exec(
            select(func.count()).select_from(LinkRow).where(LinkRow.playlist_id == playlist_id)
        ).one()
        return int(result)
