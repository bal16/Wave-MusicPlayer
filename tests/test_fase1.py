"""Fase 1 (F2 List) tests: row mapping, controller refresh, event wiring.

GUI-free by design — no widget is instantiated (no display needed).
"""

from components.MainContent import MAX_VISIBLE_ROWS, format_song_row
from controllers.main_controller import MainController
from domain.entities import Song
from domain.interfaces import EventBus
from services.library_service import LibraryService


def _song(song_id, **kw):
    base = {
        "id": song_id,
        "title": f"Title {song_id}",
        "artist": "Artist",
        "album": "Album",
        "file_path": f"/music/{song_id}.mp3",
        "duration": 225.9,
    }
    base.update(kw)
    return Song(**base)


class FakeLibrary:
    """Minimal stand-in for LibraryService (records calls, replays songs)."""

    def __init__(self, songs=None):
        self.songs = songs or []
        self.subscribers = []
        self.scanned = []

    def subscribe(self, listener):
        self.subscribers.append(listener)

    def add_all(self, drafts):
        self.songs.extend(drafts)
        return len(drafts)

    def list_songs(self, query="", favorites_only=False):
        return list(self.songs)

    def scan_folder(self, path):
        self.scanned.append(path)
        return 0

    def get_song(self, song_id):
        return next((s for s in self.songs if s.id == song_id), None)

    def toggle_favorite(self, song_id):
        return True


class FakePlayer:
    """Minimal stand-in for PlayerService (playback not under test here)."""

    def __init__(self):
        self.subscribers = []

    def subscribe(self, event, listener):
        self.subscribers.append(listener)

    def play_queue(self, songs, index=0):
        return None


class FakePlaylists:
    """Minimal stand-in for PlaylistService (not under test here)."""

    def subscribe(self, listener):
        pass


class FakeView:
    """Records show_songs payloads and after() scheduling (no Tk)."""

    def __init__(self):
        self.shown = []
        self.scheduled = []

    def show_songs(self, songs):
        self.shown.append(list(songs))

    def after(self, ms, func, *args):
        self.scheduled.append((ms, func, args))
        return "after-id"


def test_format_song_row_mapping():
    row = format_song_row(_song(1))
    assert row == {
        "title": "Title 1",
        "artist": "Artist",
        "duration": "3:45",
        "favorite_mark": "♡",
    }
    assert format_song_row(_song(2, is_favorite=True))["favorite_mark"] == "♥"


def test_refresh_pushes_songs_to_view():
    view, library = FakeView(), FakeLibrary(songs=[_song(1), _song(2)])
    controller = MainController(
        view=view, library=library, player=FakePlayer(), playlists=FakePlaylists()
    )
    controller.refresh_library_view()
    assert [s.id for s in view.shown[0]] == [1, 2]


def test_library_changed_event_marshals_through_after():
    view, library = FakeView(), FakeLibrary()
    controller = MainController(
        view=view, library=library, player=FakePlayer(), playlists=FakePlaylists()
    )
    controller.bind()
    assert len(library.subscribers) == 1

    # Simulate the service publishing from any thread: the controller
    # must schedule (not directly call) the UI refresh.
    library.subscribers[0](added=2)
    assert len(view.shown) == 0
    assert [(ms, f.__name__) for ms, f, _ in view.scheduled] == [(0, "refresh_current_view")]

    # Running the scheduled callback performs the actual refresh.
    _, func, args = view.scheduled[0]
    func(*args)
    assert view.shown == [[]]


def test_select_stub_handles_missing_song():
    view, library = FakeView(), FakeLibrary()
    controller = MainController(
        view=view, library=library, player=FakePlayer(), playlists=FakePlaylists()
    )
    controller.handle_select_song(9999)  # must not raise
    controller.handle_select_song(1)  # empty library, still fine


def test_service_subscribe_without_bus_is_noop():
    class NullTagger:
        def read(self, path):
            return None

    service = LibraryService(FakeLibrary(), tagger=NullTagger(), event_bus=None)
    service.subscribe(lambda **kw: None)  # must not raise


def test_service_subscribe_receives_scan_events(tmp_path):
    from services.library_service import LibraryService as RealService

    class Tagger:
        def read(self, path):
            from domain.entities import SongDraft

            return SongDraft(title="t", file_path=path)

    (tmp_path / "a.mp3").write_bytes(b"x")
    seen = []
    bus = EventBus()
    service = RealService(FakeLibrary(), tagger=Tagger(), event_bus=bus)
    service.subscribe(lambda **kw: seen.append(kw))
    assert service.scan_folder(str(tmp_path)) == 1
    assert seen == [{"added": 1}]


def test_max_visible_rows_cap_is_sane():
    assert MAX_VISIBLE_ROWS >= 100
