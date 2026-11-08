"""Unit tests for services/library_service.py."""

from __future__ import annotations

import os

import pytest

from domain.entities import Song, SongDraft
from domain.interfaces import EventBus, SongRepository
from services.library_service import LibraryService


class FakeRepo(SongRepository):
    def __init__(self):
        self.drafts = []
        self.songs = []
        self.favorite_result = True

    def add_all(self, drafts):
        self.drafts.extend(drafts)
        return len(drafts)

    def list_all(self, query="", favorites_only=False):
        return list(self.songs)

    def get_by_id(self, song_id):
        return next((s for s in self.songs if s.id == song_id), None)

    def toggle_favorite(self, song_id):
        return self.favorite_result


class FakeTagger:
    def __init__(self, supported=(".mp3", ".flac")):
        self.supported = supported
        self.calls = []
        self.cover = b"img"

    def read(self, path):
        self.calls.append(path)
        if os.path.splitext(path)[1].lower() not in self.supported:
            return None
        return SongDraft(title=os.path.basename(path), file_path=path)

    def read_cover(self, path):
        return self.cover


class PlainTagger:
    def read(self, path):
        return SongDraft(title="t", file_path=path)


@pytest.fixture()
def folder(tmp_path):
    (tmp_path / "sub").mkdir()
    for name in ["a.mp3", "b.flac", "c.ogg", "note.txt"]:
        (tmp_path / "sub" / name).write_bytes(b"x")
    return str(tmp_path)


def test_subscribe_without_bus_is_noop():
    LibraryService(FakeRepo(), tagger=PlainTagger(), event_bus=None).subscribe(lambda **kw: None)


def test_subscribe_registers_with_bus():
    bus = EventBus()
    service = LibraryService(FakeRepo(), tagger=PlainTagger(), event_bus=bus)
    seen = []
    service.subscribe(lambda **kw: seen.append(kw))
    bus.publish("library_changed", added=1)
    assert seen == [{"added": 1}]


def test_scan_folder_parses_supported_only(folder):
    repo, tagger = FakeRepo(), FakeTagger()
    added = LibraryService(repo, tagger=tagger).scan_folder(folder)
    assert added == 2
    assert sorted(d.file_path for d in repo.drafts) == sorted(
        p for p in tagger.calls if p.endswith((".mp3", ".flac"))
    )


@pytest.mark.parametrize("path", ["", None, "/does/not/exist"])
def test_scan_folder_cancelled_or_missing_returns_zero(path):
    assert LibraryService(FakeRepo(), tagger=FakeTagger()).scan_folder(path) == 0


def test_scan_folder_reports_determinate_progress(tmp_path):
    for name in ["a.mp3", "b.flac", "c.ogg"]:
        (tmp_path / name).write_bytes(b"x")
    seen = []
    service = LibraryService(FakeRepo(), tagger=FakeTagger())
    assert service.scan_folder(str(tmp_path), progress=lambda d, t: seen.append((d, t))) == 2
    assert [d for d, _ in seen] == [1, 2, 3]
    assert {t for _, t in seen} == {3}


def test_scan_folder_publishes_event_only_when_added(folder):
    bus = EventBus()
    seen = []
    bus.subscribe("library_changed", lambda **kw: seen.append(kw))
    service = LibraryService(FakeRepo(), tagger=FakeTagger(), event_bus=bus)
    assert service.scan_folder(folder) == 2
    assert seen == [{"added": 2}]


def test_scan_folder_empty_folder_publishes_nothing(tmp_path):
    bus = EventBus()
    seen = []
    bus.subscribe("library_changed", lambda **kw: seen.append(kw))
    service = LibraryService(FakeRepo(), tagger=FakeTagger(), event_bus=bus)
    assert service.scan_folder(str(tmp_path)) == 0
    assert seen == []


def test_list_songs_delegates_to_repo():
    repo = FakeRepo()
    repo.songs = [
        Song(id=1, title="A", file_path="/a.mp3"),
        Song(id=2, title="B", file_path="/b.mp3"),
    ]
    service = LibraryService(repo, tagger=FakeTagger())
    assert [s.title for s in service.list_songs()] == ["A", "B"]


def test_get_song_delegates_to_repo():
    repo = FakeRepo()
    repo.songs = [Song(id=1, title="A", file_path="/a.mp3")]
    service = LibraryService(repo, tagger=FakeTagger())
    assert service.get_song(1).title == "A"
    assert service.get_song(2) is None


def test_get_cover_delegates_to_tagger():
    repo = FakeRepo()
    repo.songs = [Song(id=1, title="A", file_path="/a.flac")]
    tagger = FakeTagger()
    service = LibraryService(repo, tagger=tagger)
    assert service.get_cover(1) == b"img"
    assert service.get_cover(2) is None


def test_get_cover_returns_none_when_tagger_has_no_cover_support():
    repo = FakeRepo()
    repo.songs = [Song(id=1, title="A", file_path="/a.flac")]
    service = LibraryService(repo, tagger=PlainTagger())
    assert service.get_cover(1) is None


def test_toggle_favorite_delegates_to_repo():
    repo = FakeRepo()
    repo.favorite_result = False
    service = LibraryService(repo, tagger=FakeTagger())
    assert service.toggle_favorite(1) is False
