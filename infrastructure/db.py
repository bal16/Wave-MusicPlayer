"""Engine + init_db + session factory. Single place where the DB URL is defined.

Absolute path (fixes the relative-CWD bug of the legacy models/database.py):
  <repo>/data/app.db
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from sqlmodel import Session, SQLModel, create_engine

DB_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "app.db"
DB_URL: str = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create tables when missing. Idempotent — safe to call from main()
    as well as from the legacy splash screen."""
    from infrastructure.models import Playlist, PlaylistSongLink, Song  # noqa: F401

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    logger.info(f"Database initialized at {DB_PATH}")


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
