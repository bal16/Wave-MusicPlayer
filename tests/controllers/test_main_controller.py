"""Unit tests for controllers/main_controller.py (view + services faked)."""

from __future__ import annotations

from controllers.main_controller import (
    TICK_MS,
    VIEW_LIBRARY,
    VIEW_PLAYLIST_DETAIL,
    VIEW_PLAYLISTS,
    MainController,
)
from services.player_service import PlayerService
from tests.support.doubles import (
    FakeBackend,
    FakeLibrary,
    FakePlayer,
    FakePlaylists,
    FakeView,
    make_song,
)


def build_controller(*, songs=None, library=None, player=None, playlists=None, view=None):
    view = view or FakeView()
    library = library
    if library is None:
        library = FakeLibrary(songs if songs is not None else [make_song(1), make_song(2)])
    player = player or FakePlayer()
    playlists = playlists or FakePlaylists()
    return MainController(view=view, library=library, player=player, playlists=playlists), view


def real_player(songs=None):
    backend = FakeBackend({s.file_path: 200.0 for s in (songs or [])})
    return PlayerService(backend), backend


# -- lifecycle --


def test_run_enters_mainloop():
    controller, view = build_controller()
    controller.run()
    assert view.mainloop_called is True


def test_shutdown_withdraws_shuts_down_and_destroys():
    class ShutdownPlayer(FakePlayer):
        def __init__(self):
            super().__init__()
            self.shutdowns = 0

        def shutdown(self):
            self.shutdowns += 1

    view, player = FakeView(), ShutdownPlayer()
    controller = MainController(
        view=view, library=FakeLibrary(), player=player, playlists=FakePlaylists()
    )
    controller.shutdown()
    assert view.withdrawn == 1
    assert player.shutdowns == 1
    assert view.destroyed == 1


def test_shutdown_destroys_view_when_player_shutdown_fails():
    class BoomPlayer(FakePlayer):
        def shutdown(self):
            raise RuntimeError("audio gone")

    view = FakeView()
    controller = MainController(
        view=view, library=FakeLibrary(), player=BoomPlayer(), playlists=FakePlaylists()
    )
    controller.shutdown()
    assert view.destroyed == 1


def test_shutdown_swallows_view_errors():
    class BoomView(FakeView):
        def withdraw(self):
            raise RuntimeError("already gone")

        def destroy(self):
            raise RuntimeError("destroy failed")

    view = BoomView()
    controller = MainController(
        view=view, library=FakeLibrary(), player=FakePlayer(), playlists=FakePlaylists()
    )
    controller.shutdown()  # must not raise


def test_bind_subscribes_to_library():
    library = FakeLibrary()
    controller, _ = build_controller(library=library)
    controller.bind()
    assert len(library.subscribers) == 1


# -- refresh routing --


def test_refresh_library_view_pushes_songs():
    library = FakeLibrary([make_song(1), make_song(2)])
    controller, view = build_controller(library=library)
    controller.refresh_library_view()
    assert [s.id for s in view.shown[0]] == [1, 2]


def test_refresh_current_view_playlists():
    controller, view = build_controller()
    controller.current_view = VIEW_PLAYLISTS
    controller.refresh_current_view()
    assert view.playlists_shown == [[]]


def test_refresh_current_view_playlist_detail():
    playlists = FakePlaylists()
    playlist = playlists.create_playlist("Mix")
    controller, view = build_controller(playlists=playlists)
    controller.current_view = VIEW_PLAYLIST_DETAIL
    controller.current_playlist_id = playlist.id
    controller.refresh_current_view()
    assert view.playlist_songs_shown[0][0] == playlist


def test_refresh_current_view_playlist_detail_missing_falls_back():
    controller, view = build_controller()
    controller.current_view = VIEW_PLAYLIST_DETAIL
    controller.current_playlist_id = 999
    controller.refresh_current_view()
    assert controller.current_view == VIEW_PLAYLISTS
    assert view.playlists_shown != []


def test_library_changed_event_marshals_through_after():
    library = FakeLibrary()
    controller, view = build_controller(library=library)
    controller.bind()
    library.subscribers[0](added=2)
    assert view.shown == []
    assert [(ms, f.__name__) for ms, f, _ in view.scheduled] == [(0, "refresh_current_view")]
    view.run_scheduled()
    assert view.shown == [[]]


def test_playlist_changed_event_marshals_through_after():
    controller, view = build_controller()
    controller._on_playlist_changed()
    assert [(ms, f.__name__) for ms, f, _ in view.scheduled] == [(0, "refresh_current_view")]


# -- scan --


class StubThread:
    instances: list[StubThread] = []

    def __init__(self, target=None, args=(), daemon=None):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        StubThread.instances.append(self)

    def start(self):
        self.started = True


def test_add_folder_ignores_second_scan():
    controller, view = build_controller()
    controller._scanning = True
    controller.handle_add_folder("/music")
    assert view.scan_started == 0


def test_add_folder_empty_path_is_noop():
    controller, view = build_controller()
    controller.handle_add_folder("")
    assert view.scan_started == 0
    assert controller._scanning is False


def test_add_folder_starts_background_thread(monkeypatch):
    StubThread.instances.clear()
    monkeypatch.setattr("controllers.main_controller.threading.Thread", StubThread)
    controller, view = build_controller()
    controller.handle_add_folder("/music")
    assert view.scan_started == 1
    assert controller._scanning is True
    assert len(StubThread.instances) == 1
    assert StubThread.instances[0].started is True
    assert StubThread.instances[0].daemon is True


def test_scan_in_background_reports_progress_and_finishes():
    controller, view = build_controller()
    controller._scan_in_background("/music")
    view.run_scheduled()
    assert view.scan_finished == 1
    assert controller._scanning is False


def test_scan_in_background_surfaces_failure():
    class BoomLibrary(FakeLibrary):
        def scan_folder(self, path, progress=None):
            raise RuntimeError("disk gone")

    controller, view = build_controller(library=BoomLibrary())
    controller._scan_in_background("/music")
    view.run_scheduled()
    assert view.scan_failures == ["disk gone"]
    assert view.scan_finished == 1


def test_scan_background_swallows_dead_view_errors():
    class DeadView(FakeView):
        def after(self, ms, func, *args):
            raise RuntimeError("window gone")

    controller, view = build_controller(view=DeadView())
    controller._scan_in_background("/music")  # must not raise
    controller._report_scan_progress(1, 2)  # must not raise


def test_scan_failure_with_dead_view_does_not_raise():
    class BoomLibrary(FakeLibrary):
        def scan_folder(self, path, progress=None):
            raise RuntimeError("disk gone")

    class DeadView(FakeView):
        def after(self, ms, func, *args):
            raise RuntimeError("window gone")

    controller, view = build_controller(library=BoomLibrary(), view=DeadView())
    controller._scan_in_background("/music")  # must not raise
    assert controller._scanning is False


def test_report_scan_progress_marshals():
    controller, view = build_controller()
    controller._report_scan_progress(1, 3)
    view.run_scheduled()
    assert view.scan_progress == [(1, 3)]


# -- library handlers --


def test_list_songs_and_toggle_favorite_delegate():
    library = FakeLibrary([make_song(1)])
    controller, _ = build_controller(library=library)
    assert controller.handle_list_songs(query="x", favorites_only=True) == library.songs
    assert controller.handle_toggle_favorite(1) is True
    assert library.favorites == [1]


def test_select_song_queues_full_library_at_clicked_index():
    songs = [make_song(1), make_song(2), make_song(3)]
    player, backend = real_player(songs)
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(2)
    assert backend.loaded == "/music/2.mp3"
    assert [s.id for s in view.tracks] == [2]


def test_select_song_missing_id_defaults_to_first():
    songs = [make_song(1), make_song(2)]
    player, backend = real_player(songs)
    controller, _ = build_controller(songs=songs, player=player)
    controller.handle_select_song(999)
    assert backend.loaded == "/music/1.mp3"


def test_select_song_empty_library_keeps_ticker_idle():
    player, backend = real_player([])
    controller, view = build_controller(songs=[], player=player)
    controller.handle_select_song(1)
    assert view.tracks == []
    assert view.scheduled == [(TICK_MS, controller._tick, ())]


def test_current_songs_uses_playlist_in_detail_view():
    class PlaylistWithSongs(FakePlaylists):
        def songs_in_playlist(self, playlist_id):
            return [make_song(7)]

    playlists = PlaylistWithSongs()
    controller, _ = build_controller(playlists=playlists)
    controller.current_view = VIEW_PLAYLIST_DETAIL
    controller.current_playlist_id = 3
    assert [s.id for s in controller._current_songs()] == [7]


def test_current_songs_uses_library_otherwise():
    controller, _ = build_controller(songs=[make_song(1)])
    assert [s.id for s in controller._current_songs()] == [1]


# -- playback handlers --


def test_play_pause_updates_view():
    songs = [make_song(1)]
    player, _ = real_player(songs)
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    controller.handle_play_pause()
    assert view.playing_states == [False]


def test_next_and_prev_update_view():
    songs = [make_song(1), make_song(2)]
    player, _ = real_player(songs)
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    view.tracks.clear()
    controller.handle_next()
    controller.handle_prev()
    assert [s.id for s in view.tracks] == [2, 1]


def test_next_and_prev_without_song_do_not_touch_view():
    class EmptyPlayer(FakePlayer):
        def next(self):
            return None

        def prev(self):
            return None

    controller, view = build_controller(player=EmptyPlayer())
    controller.handle_next()
    controller.handle_prev()
    assert view.tracks == []


def test_seek_updates_progress():
    songs = [make_song(1)]
    player, backend = real_player(songs)
    backend.durations["/music/1.mp3"] = 200.0
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    controller.handle_seek(50)
    assert view.progress[-1] == (50.0, 200.0)


def test_volume_and_mute_delegate():
    controller, view = build_controller()
    controller.handle_volume(0.25)
    controller.handle_mute()
    assert view.muted_states == [True]


def test_toggle_current_favorite_updates_row():
    class PlayingPlayer(FakePlayer):
        def __init__(self, current):
            super().__init__()
            self.current = current

    updated = make_song(1, is_favorite=True)
    library = FakeLibrary([updated])
    controller, view = build_controller(library=library, player=PlayingPlayer(make_song(1)))
    controller.handle_toggle_current_favorite()
    assert library.favorites == [1]
    assert view.refreshed_rows == [updated]


def test_toggle_current_favorite_no_current_is_noop():
    controller, view = build_controller()
    controller.handle_toggle_current_favorite()
    assert view.refreshed_rows == []


def test_toggle_current_favorite_missing_song_is_noop():
    class PlayingPlayer(FakePlayer):
        def __init__(self):
            super().__init__()
            self.current = make_song(None)

    controller, view = build_controller(player=PlayingPlayer())
    controller.handle_toggle_current_favorite()
    assert view.refreshed_rows == []


def test_toggle_current_favorite_song_deleted_is_noop():
    class PlayingPlayer(FakePlayer):
        def __init__(self):
            super().__init__()
            self.current = make_song(999)

    view = FakeView()
    controller = MainController(
        view=view, library=FakeLibrary([]), player=PlayingPlayer(), playlists=FakePlaylists()
    )
    controller.handle_toggle_current_favorite()
    assert view.refreshed_rows == []


# -- navigation / playlists --


def test_navigate_music_and_playlists():
    controller, view = build_controller()
    controller.handle_show_playlists()
    assert controller.current_view == VIEW_PLAYLISTS
    assert view.playlists_shown != []

    controller.handle_show_music()
    assert controller.current_view == VIEW_LIBRARY
    assert [s.id for s in view.shown[-1]] == [1, 2]


def test_select_playlist_shows_detail():
    playlists = FakePlaylists()
    playlist = playlists.create_playlist("Mix")
    controller, view = build_controller(playlists=playlists)
    controller.handle_select_playlist(playlist.id)
    assert controller.current_view == VIEW_PLAYLIST_DETAIL
    assert controller.current_playlist_id == playlist.id
    assert view.playlist_songs_shown[0][0] == playlist


def test_select_missing_playlist_falls_back_to_overview():
    controller, view = build_controller()
    controller.handle_select_playlist(999)
    assert controller.current_view == VIEW_PLAYLISTS
    assert view.playlists_shown != []


def test_create_rename_delete_playlist_delegate():
    playlists = FakePlaylists()
    controller, _ = build_controller(playlists=playlists)
    created = controller.handle_create_playlist("Mix", "desc")
    assert created.name == "Mix"
    assert controller.handle_rename_playlist(created.id, "New").name == "New"
    assert controller.handle_delete_playlist(created.id) is True


def test_delete_current_playlist_returns_to_overview():
    playlists = FakePlaylists()
    controller, view = build_controller(playlists=playlists)
    created = controller.handle_create_playlist("Temp")
    controller.handle_select_playlist(created.id)
    assert controller.handle_delete_playlist(created.id) is True
    assert controller.current_view == VIEW_PLAYLISTS


def test_delete_other_playlist_keeps_view():
    playlists = FakePlaylists()
    controller, _ = build_controller(playlists=playlists)
    playlist = playlists.create_playlist("P")
    controller.handle_select_playlist(playlist.id)
    assert controller.handle_delete_playlist(2) is True
    assert controller.current_view == VIEW_PLAYLIST_DETAIL


def test_add_and_remove_playlist_song():
    controller, view = build_controller()
    assert controller.handle_add_to_playlist(1, 2) is True
    assert controller.handle_remove_from_playlist(1, 2) is True
    assert view.shown != []  # remove triggers a library refresh


def test_add_to_playlist_returns_false_without_refresh():
    class FailingPlaylists(FakePlaylists):
        def add_song(self, playlist_id, song_id):
            return False

        def remove_song(self, playlist_id, song_id):
            return False

    controller, view = build_controller(playlists=FailingPlaylists())
    assert controller.handle_add_to_playlist(1, 2) is False
    assert controller.handle_remove_from_playlist(1, 2) is False
    assert view.refresh_current_calls == 0


def test_query_playlists_songs_and_cover():
    playlists = FakePlaylists()
    playlist = playlists.create_playlist("Mix")
    library = FakeLibrary([make_song(1)], cover=b"img")
    controller, _ = build_controller(library=library, playlists=playlists)
    controller.current_playlist_id = playlist.id
    assert controller.handle_list_playlists() == [playlist]
    assert controller.handle_get_playlist(playlist.id) == playlist
    assert controller.handle_get_current_playlist() == playlist
    assert controller.handle_get_song(1).id == 1
    assert controller.handle_get_cover(1) == b"img"


def test_get_current_playlist_none_in_library_view():
    controller, _ = build_controller()
    assert controller.handle_get_current_playlist() is None


# -- player events --


def test_track_change_marshals_through_after():
    controller, view = build_controller()
    song = make_song(3)
    controller._on_track_changed(song)
    assert view.tracks == []
    ms, func, args = view.scheduled[0]
    assert ms == 0
    func(*args)
    assert view.tracks == [song]


def test_show_track_safe_ignores_none():
    controller, view = build_controller()
    controller._show_track_safe(None)
    assert view.tracks == []


def test_player_state_marshals_through_after():
    controller, view = build_controller()
    controller._on_player_state(playing=True)
    ms, func, args = view.scheduled[0]
    assert (ms, func, args) == (0, view.set_playing, (True,))


# -- ticker --


def test_ensure_ticker_starts_once():
    controller, view = build_controller()
    controller._ensure_ticker()
    controller._ensure_ticker()
    assert view.scheduled == [(TICK_MS, controller._tick, ())]


def test_tick_stops_when_window_is_gone():
    class DeadView(FakeView):
        def winfo_exists(self):
            return False

    controller, view = build_controller(view=DeadView())
    controller._ticker_running = True
    controller._tick()
    assert controller._ticker_running is False
    assert view.scheduled == []


def test_tick_stops_when_winfo_exists_raises():
    class BrokenView(FakeView):
        def winfo_exists(self):
            raise RuntimeError("tcl gone")

    controller, view = build_controller(view=BrokenView())
    controller._ticker_running = True
    controller._tick()
    assert controller._ticker_running is False


def test_tick_stops_without_current_song():
    controller, view = build_controller()
    controller._ticker_running = True
    controller._tick()
    assert controller._ticker_running is False
    assert view.progress == []


def test_tick_stops_while_paused():
    songs = [make_song(1)]
    player, backend = real_player(songs)
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    view.scheduled.clear()
    backend.playing = False
    controller._ticker_running = True
    controller._tick()
    assert controller._ticker_running is False
    assert view.progress == []


def test_tick_skips_progress_while_seeking_but_reschedules():
    songs = [make_song(1)]
    player, backend = real_player(songs)
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    view.scheduled.clear()
    controller.seeking = True
    controller._ticker_running = True
    controller._tick()
    assert view.progress == []
    assert view.scheduled == [(TICK_MS, controller._tick, ())]


def test_tick_pushes_progress_and_reschedules():
    songs = [make_song(1)]
    player, backend = real_player(songs)
    backend.durations["/music/1.mp3"] = 200.0
    controller, view = build_controller(songs=songs, player=player)
    controller.handle_select_song(1)
    view.scheduled.clear()
    backend.pos = 5.0
    controller._ticker_running = True
    controller._tick()
    assert view.progress[-1] == (5.0, 200.0)
    assert view.scheduled == [(TICK_MS, controller._tick, ())]
