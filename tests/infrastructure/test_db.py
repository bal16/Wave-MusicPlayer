"""Unit tests for infrastructure/db.py."""

from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from infrastructure import db


def test_db_path_and_url_point_at_repo_data_folder():
    assert db.DB_PATH.is_absolute()
    assert db.DB_PATH == Path(db.__file__).resolve().parent.parent / "data" / "app.db"
    assert db.DB_URL == f"sqlite:///{db.DB_PATH}"


def test_engine_uses_sqlite_and_allows_cross_thread(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/x.db")
    monkeypatch.setattr(db, "engine", engine)
    assert engine.url.database == str(tmp_path / "x.db")


def test_init_db_creates_tables_and_parent_folder(monkeypatch, tmp_path):
    target = tmp_path / "nested" / "app.db"
    engine = create_engine(f"sqlite:///{target}")
    monkeypatch.setattr(db, "DB_PATH", target)
    monkeypatch.setattr(db, "engine", engine)

    db.init_db()

    assert target.parent.is_dir()
    from sqlalchemy import inspect

    assert {"song", "playlist", "playlistsonglink"} <= set(inspect(engine).get_table_names())


def test_init_db_is_idempotent(monkeypatch, tmp_path):
    target = tmp_path / "app.db"
    engine = create_engine(f"sqlite:///{target}")
    monkeypatch.setattr(db, "DB_PATH", target)
    monkeypatch.setattr(db, "engine", engine)

    db.init_db()
    db.init_db()


def test_get_session_yields_working_session(monkeypatch, tmp_path):
    target = tmp_path / "app.db"
    engine = create_engine(f"sqlite:///{target}")
    monkeypatch.setattr(db, "engine", engine)
    SQLModel.metadata.create_all(engine)

    with db.get_session() as session:
        assert isinstance(session, Session)
        assert session.is_active
