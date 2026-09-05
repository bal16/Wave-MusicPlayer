"""Repository tests: SqlSongRepository against an isolated SQLite file.

GUI-free by design (see docs/architecture.md).
"""

import pytest
from sqlmodel import SQLModel, create_engine

from domain.entities import SongDraft
from infrastructure.models import Song as SongRow  # noqa: F401 — register tables
from infrastructure.song_repository import SqlSongRepository


@pytest.fixture()
def repo(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/repo.db")
    SQLModel.metadata.create_all(engine)
    return SqlSongRepository(engine)


def _draft(path, **kw):
    base = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "file_path": path,
        "duration": 200.5,
    }
    base.update(kw)
    return SongDraft(**base)


def test_add_all_inserts_and_skips_duplicates(repo):
    assert repo.add_all([_draft("/music/a.mp3"), _draft("/music/b.flac")]) == 2
    # Same paths again -> 0 new (dedup by absolute file_path).
    assert repo.add_all([_draft("/music/a.mp3"), _draft("/music/b.flac")]) == 0
    assert len(repo.list_all()) == 2


def test_add_all_normalizes_relative_paths(repo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert repo.add_all([_draft("rel/song.mp3")]) == 1
    songs = repo.list_all()
    assert songs[0].file_path.startswith(str(tmp_path))


def test_list_all_search_and_favorites(repo):
    repo.add_all(
        [
            _draft("/m/one.mp3", title="Morning"),
            _draft("/m/two.mp3", title="Evening"),
        ]
    )
    assert [s.title for s in repo.list_all(query="morn")] == ["Morning"]
    first = repo.list_all()[0]
    repo.toggle_favorite(first.id)
    assert [s.title for s in repo.list_all(favorites_only=True)] == [first.title]


def test_get_by_id_missing_returns_none(repo):
    assert repo.get_by_id(9999) is None
    assert repo.toggle_favorite(9999) is None
