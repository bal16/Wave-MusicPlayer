"""LibraryService tests with fake repo + tagger (no DB, no TinyTag, no Tk)."""

import os

import pytest

from domain.entities import Song, SongDraft
from domain.interfaces import EventBus, SongRepository
from services.library_service import LibraryService


class FakeRepo(SongRepository):
    def __init__(self):
        self.drafts = []
        self.songs = []

    def add_all(self, drafts):
        self.drafts.extend(drafts)
        return len(drafts)

    def list_all(self, query="", favorites_only=False):
        return list(self.songs)

    def get_by_id(self, song_id):
        return None

    def toggle_favorite(self, song_id):
        return True


class FakeTagger:
    def __init__(self, supported=(".mp3", ".flac")):
        self.supported = supported
        self.calls = []

    def read(self, path):
        self.calls.append(path)
        if os.path.splitext(path)[1].lower() not in self.supported:
            return None
        return SongDraft(title=os.path.basename(path), file_path=path)


@pytest.fixture()
def folder(tmp_path):
    (tmp_path / "sub").mkdir()
    for name in ["a.mp3", "b.flac", "c.ogg", "note.txt"]:
        (tmp_path / "sub" / name).write_bytes(b"x")
    return str(tmp_path)


def test_scan_folder_parses_supported_only(folder):
    repo, tagger = FakeRepo(), FakeTagger()
    service = LibraryService(repo, tagger=tagger)
    added = service.scan_folder(folder)
    assert added == 2
    assert sorted(d.file_path for d in repo.drafts) == sorted(
        p for p in tagger.calls if p.endswith((".mp3", ".flac"))
    )


def test_scan_folder_cancelled_or_missing_returns_zero():
    service = LibraryService(FakeRepo(), tagger=FakeTagger())
    assert service.scan_folder("") == 0
    assert service.scan_folder(None) == 0
    assert service.scan_folder("/does/not/exist") == 0


def test_scan_folder_publishes_event_only_when_added(folder):
    bus = EventBus()
    seen = []
    bus.subscribe("library_changed", lambda **kw: seen.append(kw))
    service = LibraryService(FakeRepo(), tagger=FakeTagger(), event_bus=bus)
    assert service.scan_folder(folder) == 2
    assert seen == [{"added": 2}]


def test_list_songs_delegates_to_repo():
    repo = FakeRepo()
    repo.songs = [
        Song(id=1, title="A", file_path="/a.mp3"),
        Song(id=2, title="B", file_path="/b.mp3"),
    ]
    service = LibraryService(repo, tagger=FakeTagger())
    assert [s.title for s in service.list_songs()] == ["A", "B"]
