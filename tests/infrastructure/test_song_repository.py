"""Unit tests for infrastructure/song_repository.py (isolated SQLite)."""

from __future__ import annotations

import pytest
from sqlmodel import SQLModel, create_engine

from domain.entities import SongDraft
from infrastructure.models import Song as SongRow  # noqa: F401 — register tables
from infrastructure.song_repository import SqlSongRepository, _to_entity


@pytest.fixture()
def repo(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/repo.db")
    SQLModel.metadata.create_all(engine)
    return SqlSongRepository(engine)


def _draft(path, **kwargs):
    base = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "file_path": path,
        "duration": 200.5,
    }
    base.update(kwargs)
    return SongDraft(**base)


def test_add_all_inserts_and_skips_duplicates(repo):
    assert repo.add_all([_draft("/music/a.mp3"), _draft("/music/b.flac")]) == 2
    assert repo.add_all([_draft("/music/a.mp3"), _draft("/music/b.flac")]) == 0
    assert len(repo.list_all()) == 2


def test_add_all_dedups_within_one_batch(repo):
    drafts = [_draft("/music/a.mp3", title="One"), _draft("/music/a.mp3", title="Two")]
    assert repo.add_all(drafts) == 1
    assert repo.list_all()[0].title == "Two"  # last draft wins


def test_add_all_empty_returns_zero(repo):
    assert repo.add_all([]) == 0


def test_add_all_normalizes_relative_paths(repo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert repo.add_all([_draft("rel/song.mp3")]) == 1
    assert repo.list_all()[0].file_path.startswith(str(tmp_path))


def test_add_all_defaults_duration(repo):
    assert repo.add_all([_draft("/m/x.mp3", duration=None)]) == 1
    assert repo.list_all()[0].duration == 0.0


def test_list_all_search_and_favorites(repo):
    repo.add_all(
        [
            _draft("/m/one.mp3", title="Morning", artist="Alice", album="Wake"),
            _draft("/m/two.mp3", title="Evening", artist="Bob", album="Night"),
        ]
    )
    assert [s.title for s in repo.list_all(query="morn")] == ["Morning"]
    assert [s.title for s in repo.list_all(query="alice")] == ["Morning"]
    assert [s.title for s in repo.list_all(query="night")] == ["Evening"]

    first = repo.list_all()[0]
    repo.toggle_favorite(first.id)
    assert [s.title for s in repo.list_all(favorites_only=True)] == [first.title]


def test_list_all_orders_by_added_at_desc(repo):
    repo.add_all([_draft("/m/a.mp3", title="A"), _draft("/m/b.mp3", title="B")])
    assert [s.title for s in repo.list_all()] == ["B", "A"]


def test_get_by_id(repo):
    repo.add_all([_draft("/m/a.mp3", title="A")])
    song = repo.list_all()[0]
    assert repo.get_by_id(song.id) == song
    assert repo.get_by_id(9999) is None


def test_toggle_favorite_roundtrip(repo):
    repo.add_all([_draft("/m/a.mp3")])
    song = repo.list_all()[0]
    assert repo.toggle_favorite(song.id) is True
    assert repo.get_by_id(song.id).is_favorite is True
    assert repo.toggle_favorite(song.id) is False
    assert repo.toggle_favorite(9999) is None


def test_to_entity_maps_nullable_fields():
    row = SongRow(title="T", file_path="/x.mp3", duration=None, is_favorite=None)
    row.id = 3
    entity = _to_entity(row)
    assert entity.id == 3
    assert entity.duration == 0.0
    assert entity.is_favorite is False
