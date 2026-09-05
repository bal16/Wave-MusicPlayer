"""SQLModel implementation of SongRepository.

The only file (besides models/db) allowed to import SQLModel outside
the legacy shim.
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, or_, select

from domain.entities import Song as DomainSong
from domain.entities import SongDraft
from domain.interfaces import SongRepository
from infrastructure.audio_tagger import normalize_path
from infrastructure.models import Song as SongRow


def _to_entity(row: SongRow) -> DomainSong:
    return DomainSong(
        id=row.id,
        title=row.title,
        artist=row.artist,
        album=row.album,
        file_path=row.file_path,
        duration=float(row.duration or 0.0),
        is_favorite=bool(row.is_favorite),
        added_at=row.added_at,
    )


class SqlSongRepository(SongRepository):
    def __init__(self, engine: Engine):
        self._engine = engine

    def add_all(self, drafts: list[SongDraft]) -> int:
        # Normalize first, then dedup in memory (absolute paths).
        unique: dict[str, SongDraft] = {}
        for d in drafts:
            abs_path = normalize_path(d.file_path)
            unique[abs_path] = SongDraft(
                title=d.title,
                artist=d.artist,
                album=d.album,
                file_path=abs_path,
                duration=float(d.duration or 0.0),
            )
        if not unique:
            return 0

        with Session(self._engine) as session:
            existing = set(
                session.exec(
                    select(SongRow.file_path).where(col(SongRow.file_path).in_(list(unique)))
                ).all()
            )
            fresh = [
                SongRow(
                    title=d.title,
                    artist=d.artist,
                    album=d.album,
                    file_path=d.file_path,
                    duration=d.duration,
                )
                for p, d in unique.items()
                if p not in existing
            ]
            if fresh:
                session.add_all(fresh)  # single commit per batch
                session.commit()
                logger.info(f"Added {len(fresh)} song(s), skipped {len(existing)} duplicate(s)")
            return len(fresh)

    def list_all(self, query: str = "", favorites_only: bool = False) -> list[DomainSong]:
        with Session(self._engine) as session:
            stmt = select(SongRow).order_by(col(SongRow.added_at).desc())
            if favorites_only:
                stmt = stmt.where(SongRow.is_favorite.is_(True))
            if query:
                like = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        col(SongRow.title).like(like),
                        col(SongRow.artist).like(like),
                        col(SongRow.album).like(like),
                    )
                )
            rows = session.exec(stmt).all()
            return [_to_entity(r) for r in rows]

    def get_by_id(self, song_id: int) -> DomainSong | None:
        with Session(self._engine) as session:
            row = session.get(SongRow, song_id)
            return _to_entity(row) if row else None

    def toggle_favorite(self, song_id: int) -> bool | None:
        with Session(self._engine) as session:
            row = session.get(SongRow, song_id)
            if row is None:
                return None
            row.is_favorite = not row.is_favorite
            session.add(row)
            session.commit()
            session.refresh(row)
            return bool(row.is_favorite)
