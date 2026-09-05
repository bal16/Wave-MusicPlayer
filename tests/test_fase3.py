"""Fase 3 (F4 Playlist) tests: repository, service, controller routing.

GUI-free — widgets are never instantiated (dialogs excluded, covered by
manual smoke). Repository tests run against an isolated tmp SQLite file.
"""

import pytest
from sqlmodel import SQLModel, create_engine

from controllers.main_controller import MainController
from domain.entities import Playlist, Song
from infrastructure.models import (  # noqa: F401 — register tables
    Playlist as PlaylistRow,
)
from infrastructure.models import Song as SongRow
from infrastructure.playlist_repository import SqlPlaylistRepository
from services.player_service import PlayerService
from services.playlist_service import PlaylistService


def _song(title, path):
    return Song(
        id=None,
        title=title,
        artist="Artist",
        album="Album",
        file_path=path,
        duration=200.0,
    )


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/pl.db")
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture()
def song_ids(engine):
    """Two persisted songs; returns their ids."""
    from sqlmodel import Session

    with Session(engine) as session:
        session.add(SongRow(title="A", file_path="/m/a.mp3", duration=200.0))
        session.add(SongRow(title="B", file_path="/m/b.mp3", duration=180.0))
        session.commit()
        rows = session.exec(__import__("sqlmodel").select(SongRow)).all()
        return [r.id for r in rows]


# -- Repository --


def test_create_and_list_with_counts(engine, song_ids):
    repo = SqlPlaylistRepository(engine)
    playlist = repo.create("Chill", "Evening")
    assert playlist.id is not None
    assert playlist.song_count == 0

    assert repo.add_song(playlist.id, song_ids[0]) is True
    assert repo.add_song(playlist.id, song_ids[0]) is True  # idempotent
    (listed,) = repo.list_all()
    assert (listed.name, listed.song_count) == ("Chill", 1)


def test_create_blank_name_rejected(engine):
    repo = SqlPlaylistRepository(engine)
    with pytest.raises(ValueError):
        repo.create("   ")


def test_rename_and_missing(engine):
    repo = SqlPlaylistRepository(engine)
    playlist = repo.create("Old")
    assert repo.rename(playlist.id, "New").name == "New"
    assert repo.rename(9999, "X") is None
    with pytest.raises(ValueError):
        repo.rename(playlist.id, "  ")


def test_add_song_missing_ids(engine, song_ids):
    repo = SqlPlaylistRepository(engine)
    playlist = repo.create("P")
    assert repo.add_song(9999, song_ids[0]) is False
    assert repo.add_song(playlist.id, 9999) is False


def test_remove_and_delete_keep_songs(engine, song_ids):
    from sqlmodel import Session, select

    repo = SqlPlaylistRepository(engine)
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    assert repo.remove_song(playlist.id, song_ids[0]) is True
    assert repo.remove_song(playlist.id, song_ids[0]) is False
    assert repo.songs_in_playlist(playlist.id) == []

    repo.add_song(playlist.id, song_ids[1])
    assert repo.delete(playlist.id) is True
    assert repo.delete(playlist.id) is False
    # Links gone, songs remain.
    assert repo.songs_in_playlist(playlist.id) == []
    with Session(engine) as session:
        assert len(session.exec(select(SongRow)).all()) == 2


def test_songs_ordered_by_added_at_desc(engine, song_ids):
    repo = SqlPlaylistRepository(engine)
    playlist = repo.create("P")
    repo.add_song(playlist.id, song_ids[0])
    repo.add_song(playlist.id, song_ids[1])
    titles = [s.title for s in repo.songs_in_playlist(playlist.id)]
    assert titles == ["B", "A"]


# -- Service --


class FakePlaylistRepo:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.added = []
        self.removed = []

    def create(self, name, description=""):
        clean = name.strip()
        if not clean:
            raise ValueError("blank")
        playlist = Playlist(id=len(self.created) + 1, name=clean)
        self.created.append(playlist)
        return playlist

    def rename(self, pid, name):
        return Playlist(id=pid, name=name.strip())

    def delete(self, pid):
        self.deleted.append(pid)
        return True

    def list_all(self):
        return list(self.created)

    def get_by_id(self, pid):
        return Playlist(id=pid, name="P")

    def add_song(self, pid, sid):
        self.added.append((pid, sid))
        return True

    def remove_song(self, pid, sid):
        self.removed.append((pid, sid))
        return True

    def songs_in_playlist(self, pid):
        return []


def test_service_publishes_only_on_change():
    from domain.interfaces import EventBus

    bus = EventBus()
    seen = []
    bus.subscribe("playlist_changed", lambda **kw: seen.append(True))
    service = PlaylistService(FakePlaylistRepo(), event_bus=bus)

    service.create_playlist("Mix")
    service.add_song(1, 5)
    service.remove_song(1, 5)
    service.delete_playlist(1)
    assert len(seen) == 4

    class FailingRepo(FakePlaylistRepo):
        def delete(self, pid):
            return False

    quiet = PlaylistService(FailingRepo(), event_bus=bus)
    quiet.delete_playlist(999)
    assert len(seen) == 4  # no event on failed delete


# -- Controller routing --


class FakeLibrary:
    def __init__(self, songs=None):
        self.songs = songs or []
        self.subscribers = []

    def subscribe(self, listener):
        self.subscribers.append(listener)

    def list_songs(self, query="", favorites_only=False):
        return list(self.songs)

    def get_song(self, song_id):
        return next((s for s in self.songs if s.id == song_id), None)

    def toggle_favorite(self, song_id):
        return True


class FakeBackend:
    def __init__(self):
        self.loaded = None
        self.playing = False

    def load(self, path):
        self.loaded = path

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False

    def seek(self, seconds):
        pass

    def set_volume(self, level):
        pass

    def get_pos(self):
        return 0.0

    def get_duration(self):
        return 200.0

    def is_playing(self):
        return self.playing

    def on_end(self, callback):
        pass

    def close(self):
        pass


class FakeView:
    def __init__(self):
        self.playlists_shown = []
        self.detail_shown = []
        self.songs_shown = []
        self.tracks = []
        self.scheduled = []

    def show_playlists(self, playlists):
        self.playlists_shown.append([p.name for p in playlists])

    def show_playlist_songs(self, playlist, songs):
        self.detail_shown.append((playlist.name, [s.id for s in songs]))

    def show_songs(self, songs):
        self.songs_shown.append([s.id for s in songs])

    def show_track(self, song):
        self.tracks.append(song.id)

    def set_progress(self, s, t):
        pass

    def set_playing(self, p):
        pass

    def set_muted(self, m):
        pass

    def after(self, ms, func, *args):
        self.scheduled.append((ms, func, args))
        return "after-id"


def _controller(songs=None, playlists=None):
    songs = songs if songs is not None else [_song_with_id(1), _song_with_id(2)]
    view = FakeView()
    controller = MainController(
        view=view,
        library=FakeLibrary(songs),
        player=PlayerService(FakeBackend()),
        playlists=PlaylistService(FakePlaylistRepo()),
    )
    return controller, view


def _song_with_id(song_id, title="T"):
    return Song(
        id=song_id,
        title=title,
        artist="A",
        album="B",
        file_path=f"/m/{song_id}.mp3",
        duration=200.0,
    )


def test_navigate_music_and_playlists():
    controller, view = _controller(
        songs=[_song_with_id(1), _song_with_id(2)],
    )
    controller.handle_show_playlists()
    assert controller.current_view == "playlists"
    assert view.playlists_shown != []

    controller.handle_show_music()
    assert controller.current_view == "library"
    assert view.songs_shown[-1] == [1, 2]


def test_select_playlist_shows_detail_and_queues_it():
    repo = FakePlaylistRepo()
    songs = [_song_with_id(1), _song_with_id(2), _song_with_id(3)]
    view = FakeView()
    controller = MainController(
        view=view,
        library=FakeLibrary(songs),
        player=PlayerService(FakeBackend()),
        playlists=PlaylistService(repo),
    )
    created = controller.handle_create_playlist("Mix")
    controller.handle_select_playlist(created.id)
    assert controller.current_view == "playlist"
    assert controller.current_playlist_id == created.id
    assert view.detail_shown != []


def test_delete_current_playlist_returns_to_overview():
    controller, view = _controller()
    created = controller.handle_create_playlist("Temp")
    controller.handle_select_playlist(created.id)
    assert controller.handle_delete_playlist(created.id) is True
    assert controller.current_view == "playlists"


def test_select_song_in_playlist_view_queues_playlist_songs():
    class PlaylistSongsRepo(FakePlaylistRepo):
        def songs_in_playlist(self, pid):
            return [_song_with_id(7), _song_with_id(8)]

    view = FakeView()
    backend = FakeBackend()
    controller = MainController(
        view=view,
        library=FakeLibrary([_song_with_id(1)]),
        player=PlayerService(backend),
        playlists=PlaylistService(PlaylistSongsRepo()),
    )
    created = controller.handle_create_playlist("Mix")
    controller.handle_select_playlist(created.id)
    controller.handle_select_song(8)
    assert backend.loaded == "/m/8.mp3"
    assert view.tracks == [8]
