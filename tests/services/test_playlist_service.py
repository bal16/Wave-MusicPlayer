"""Unit tests for services/playlist_service.py."""

from __future__ import annotations

from domain.entities import Playlist, Song
from domain.interfaces import EventBus
from services.playlist_service import PlaylistService


class FakePlaylistRepo:
    def __init__(self) -> None:
        self.created: list[Playlist] = []
        self.renamed: list[tuple] = []
        self.deleted: list[int] = []
        self.added: list[tuple] = []
        self.removed: list[tuple] = []
        self.rename_result = True
        self.delete_result = True
        self.add_result = True
        self.remove_result = True

    def create(self, name, description=""):
        playlist = Playlist(id=len(self.created) + 1, name=name, description=description)
        self.created.append(playlist)
        return playlist

    def rename(self, playlist_id, name):
        self.renamed.append((playlist_id, name))
        return Playlist(id=playlist_id, name=name) if self.rename_result else None

    def delete(self, playlist_id):
        self.deleted.append(playlist_id)
        return self.delete_result

    def list_all(self):
        return list(self.created)

    def get_by_id(self, playlist_id):
        return next((p for p in self.created if p.id == playlist_id), None)

    def add_song(self, playlist_id, song_id):
        self.added.append((playlist_id, song_id))
        return self.add_result

    def remove_song(self, playlist_id, song_id):
        self.removed.append((playlist_id, song_id))
        return self.remove_result

    def songs_in_playlist(self, playlist_id):
        return [Song(id=1, title="A", file_path="/a.mp3")]


def test_subscribe_without_bus_is_noop():
    PlaylistService(FakePlaylistRepo(), event_bus=None).subscribe(lambda **kw: None)


def test_subscribe_registers_with_bus():
    bus = EventBus()
    service = PlaylistService(FakePlaylistRepo(), event_bus=bus)
    seen = []
    service.subscribe(lambda **kw: seen.append(True))
    bus.publish("playlist_changed")
    assert seen == [True]


def test_create_publishes():
    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    service = PlaylistService(FakePlaylistRepo(), event_bus=bus)
    playlist = service.create_playlist("Mix", "desc")
    assert playlist.name == "Mix"
    assert playlist.description == "desc"
    assert seen == [True]


def test_rename_publishes_only_on_success():
    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    repo = FakePlaylistRepo()
    service = PlaylistService(repo, event_bus=bus)

    assert service.rename_playlist(1, "New").name == "New"
    assert seen == [True]

    repo.rename_result = False
    assert service.rename_playlist(9, "X") is None
    assert seen == [True]


def test_delete_publishes_only_on_success():
    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    repo = FakePlaylistRepo()
    service = PlaylistService(repo, event_bus=bus)

    assert service.delete_playlist(1) is True
    assert seen == [True]

    repo.delete_result = False
    assert service.delete_playlist(9) is False
    assert seen == [True]


def test_add_song_publishes_only_on_success():
    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    repo = FakePlaylistRepo()
    service = PlaylistService(repo, event_bus=bus)

    assert service.add_song(1, 2) is True
    assert seen == [True]

    repo.add_result = False
    assert service.add_song(1, 3) is False
    assert seen == [True]


def test_remove_song_publishes_only_on_success():
    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    repo = FakePlaylistRepo()
    service = PlaylistService(repo, event_bus=bus)

    assert service.remove_song(1, 2) is True
    assert seen == [True]

    repo.remove_result = False
    assert service.remove_song(1, 3) is False
    assert seen == [True]


def test_queries_delegate_to_repo():
    repo = FakePlaylistRepo()
    service = PlaylistService(repo)
    created = service.create_playlist("Mix")
    assert service.list_playlists() == [created]
    assert service.get_playlist(created.id) == created
    assert service.get_playlist(999) is None
    assert [s.title for s in service.songs_in_playlist(1)] == ["A"]
