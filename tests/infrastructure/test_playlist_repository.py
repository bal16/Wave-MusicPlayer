"""Unit tests for infrastructure/playlist_repository.py (isolated SQLite)."""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from infrastructure.models import Playlist as PlaylistRow
from infrastructure.models import Song as SongRow
from infrastructure.playlist_repository import SqlPlaylistRepository, _to_entity


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/pl.db")
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def repo(engine):
    return SqlPlaylistRepository(engine)


@pytest.fixture()
def song_ids(engine):
    with Session(engine) as session:
        session.add(SongRow(title="A", file_path="/m/a.mp3", duration=200.0))
        session.add(SongRow(title="B", file_path="/m/b.mp3", duration=180.0))
        session.commit()
        rows = session.exec(select(SongRow)).all()
        return [row.id for row in rows]


def test_create_and_list_with_counts(repo, song_ids):
    playlist = repo.create("Chill", "Evening")
    assert playlist.id is not None
    assert playlist.description == "Evening"
    assert playlist.song_count == 0

    assert repo.add_song(playlist.id, song_ids[0]) is True
    assert repo.add_song(playlist.id, song_ids[0]) is True  # idempotent
    (listed,) = repo.list_all()
    assert (listed.name, listed.song_count) == ("Chill", 1)


def test_create_strips_name(repo):
    playlist = repo.create("  Chill  ")
    assert playlist.name == "Chill"


def test_create_blank_is_rejected(repo):
    with pytest.raises(ValueError):
        repo.create("   ")


def test_create_empty_description_becomes_blank(repo):
    assert repo.create("P", "").description == ""


def test_rename_and_missing(repo):
    playlist = repo.create("Old")
    renamed = repo.rename(playlist.id, " New ")
    assert renamed.name == "New"
    assert renamed.id == playlist.id
    assert repo.rename(9999, "X") is None
    with pytest.raises(ValueError):
        repo.rename(playlist.id, "  ")


def test_rename_counts_existing_links(repo, song_ids):
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    assert repo.rename(playlist.id, "Q").song_count == 1


def test_add_song_missing_ids(repo, song_ids):
    playlist = repo.create("P")
    assert repo.add_song(9999, song_ids[0]) is False
    assert repo.add_song(playlist.id, 9999) is False


def test_remove_and_delete_keep_songs(repo, engine, song_ids):
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    assert repo.remove_song(playlist.id, song_ids[0]) is True
    assert repo.remove_song(playlist.id, song_ids[0]) is False
    assert repo.songs_in_playlist(playlist.id) == []

    repo.add_song(playlist.id, song_ids[1])
    assert repo.delete(playlist.id) is True
    assert repo.delete(playlist.id) is False
    assert repo.songs_in_playlist(playlist.id) == []
    with Session(engine) as session:
        assert len(session.exec(select(SongRow)).all()) == 2


def test_songs_ordered_by_song_added_at_desc(repo, song_ids):
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    repo.add_song(playlist.id, song_ids[1])
    assert [s.title for s in repo.songs_in_playlist(playlist.id)] == ["B", "A"]


def test_list_all_orders_newest_first(repo, engine):
    from datetime import UTC, datetime

    first = repo.create("First")
    second = repo.create("Second")
    with Session(engine) as session:
        row = session.get(PlaylistRow, first.id)
        row.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        row = session.get(PlaylistRow, second.id)
        row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        session.commit()
    assert [p.id for p in repo.list_all()] == [second.id, first.id]


def test_get_by_id_and_missing(repo, song_ids):
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    loaded = repo.get_by_id(playlist.id)
    assert loaded.name == "P"
    assert loaded.song_count == 1
    assert repo.get_by_id(9999) is None


def test_to_entity_defaults_empty_description():
    row = PlaylistRow(name="P", description=None)
    row.id = 7
    entity = _to_entity(row)
    assert entity.id == 7
    assert entity.description == ""
    assert entity.song_count == 0
