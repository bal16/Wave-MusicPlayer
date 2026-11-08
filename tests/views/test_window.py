"""Unit tests for views/window.py (Tk faked, clock patched)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.support import fake_tk
from tests.support.doubles import make_playlist, make_song
from views import window as module
from views.window import View


@pytest.fixture()
def view(monkeypatch):
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    return View()


@pytest.fixture()
def controller():
    mock = MagicMock()
    mock.player.current = None
    return mock


def bound_view(view, controller):
    view.set_controller(controller)
    return view


# -- construction --


def test_view_initializes_window_and_widgets(view):
    assert view.kwargs["title"] == "Wave Music Player"
    assert view.kwargs["geometry"] == "1100x650+410+215"
    assert view.kwargs["protocol:WM_DELETE_WINDOW"] == view._on_close
    assert view.splash._destroyed is True
    assert view.sidebar is not None
    assert view.main_area is not None
    assert view.playlist_view is not None
    assert view.player_bar is not None
    assert view.playlist_view.winfo_ismapped() is False
    assert fake_tk.appearance_modes == ["Dark"]
    assert fake_tk.color_themes == ["dark-blue"]


def test_update_splash_progress_sets_value(view):
    splash = fake_tk.FakeWidget()
    splash.progress = fake_tk.FakeWidget()
    view.splash = splash
    view.update_splash_progress(0.5)
    assert splash.progress.get() == 0.5


def test_update_splash_progress_ignores_missing_or_destroyed(view):
    del view.splash
    view.update_splash_progress(0.5)

    splash = fake_tk.FakeWidget()
    splash.progress = fake_tk.FakeWidget()
    splash.destroy()
    view.splash = splash
    view.update_splash_progress(0.5)
    assert splash.progress.get() == 0


def test_center_main_window(view):
    view.center_main_window()
    assert view.kwargs["geometry"] == "1100x650+410+215"


def test_set_controller_binds_every_callback(view, controller):
    view.set_controller(controller)
    assert view.controller is controller
    assert view.sidebar.on_add_folder == view._on_add_folder
    assert view.sidebar.on_navigate == view._on_navigate
    assert view.main_area.on_select == view._on_select_song
    assert view.main_area.on_favorite == view._on_favorite_song
    assert view.main_area.on_add_to_playlist == view._on_add_song_to_playlist
    assert view.main_area.on_remove_from_playlist == view._on_remove_song_from_playlist
    assert view.playlist_view.on_select is controller.handle_select_playlist
    assert view.playlist_view.on_create == view._on_create_playlist
    assert view.playlist_view.on_rename == view._on_rename_playlist
    assert view.playlist_view.on_delete == view._on_delete_playlist
    assert view.player_bar.on_play is controller.handle_play_pause
    assert view.player_bar.on_next is controller.handle_next
    assert view.player_bar.on_prev is controller.handle_prev
    assert view.player_bar.on_volume is controller.handle_volume
    assert view.player_bar.on_mute is controller.handle_mute
    assert view.player_bar.on_favorite is controller.handle_toggle_current_favorite
    assert view.player_bar.on_seek == view._on_seek_commit
    assert len(view.player_bar.slider.bindings["<ButtonPress-1>"]) == 2
    assert len(view.player_bar.slider.bindings["<ButtonRelease-1>"]) == 2


# -- rendering --


def test_show_songs_switches_to_library_and_highlights_current(view, controller):
    controller.player.current = make_song(2)
    bound_view(view, controller)
    view.show_songs([make_song(1), make_song(2)])
    assert view.playlist_view.winfo_ismapped() is False
    assert view.main_area.winfo_ismapped() is True
    assert view.main_area.lbl_header.text == "All Music"
    assert len(view.main_area._rows) == 2
    assert view.main_area._row_by_id[2]._highlighted is True


def test_show_playlists_switches_to_overview(view, controller):
    bound_view(view, controller)
    view.show_playlists([make_playlist(1, name="Mix")])
    assert view.main_area.winfo_ismapped() is False
    assert view.playlist_view.winfo_ismapped() is True
    assert len(view.playlist_view._rows) == 1


def test_show_playlist_songs_uses_remove_affordance(view, controller):
    controller.player.current = None
    bound_view(view, controller)
    view.show_playlist_songs(make_playlist(1, name="Mix"), [make_song(1)])
    assert view.playlist_view.winfo_ismapped() is False
    assert view.main_area.lbl_header.text == "Mix"
    assert view.main_area._rows[0].btn_list.text == "×"


@pytest.mark.parametrize("current", [None, "missing"])
def test_current_song_id_handles_absent_player(view, current):
    if current is None:
        view.controller = None
    else:
        view.controller = SimpleNamespace()
    assert view._current_song_id() is None


def test_current_song_id_returns_song_id(view, controller):
    controller.player.current = make_song(7)
    view.controller = controller
    assert view._current_song_id() == 7


def test_refresh_song_row_fast_path_syncs_player_bar(view, controller):
    song = make_song(1)
    controller.player.current = song
    bound_view(view, controller)
    view.show_songs([song])
    view.player_bar.set_favorite = MagicMock()

    updated = make_song(1, is_favorite=True)
    view.refresh_song_row(updated)

    assert view.main_area._row_by_id[1].lbl_title.text == updated.title
    view.player_bar.set_favorite.assert_called_once_with(True)
    controller.refresh_current_view.assert_not_called()


def test_refresh_song_row_falls_back_when_not_rendered(view, controller):
    bound_view(view, controller)
    view.show_songs([make_song(1)])
    view.refresh_song_row(make_song(99))
    controller.refresh_current_view.assert_called_once()


def test_refresh_song_row_falls_back_on_attribute_error(view, controller):
    bound_view(view, controller)
    view.main_area.update_song = MagicMock(side_effect=AttributeError("old view"))
    view.refresh_song_row(make_song(1))
    controller.refresh_current_view.assert_called_once()


def test_show_track_updates_player_bar_and_rows(view, controller):
    song = make_song(1)
    controller.handle_get_cover.return_value = b"cover"
    bound_view(view, controller)
    view.show_songs([song])
    view.player_bar.set_track = MagicMock()
    view.player_bar.set_playing = MagicMock()
    view.player_bar.set_cover = MagicMock()
    view.main_area.set_playing = MagicMock(return_value=True)

    view.show_track(song)

    view.player_bar.set_track.assert_called_once_with(song)
    view.player_bar.set_playing.assert_called_once_with(True)
    view.main_area.set_playing.assert_called_once_with(1)
    view.player_bar.set_cover.assert_called_once_with(1, b"cover")


def test_show_track_without_cover_uses_fallback(view, controller):
    song = make_song(1)
    controller.handle_get_cover.side_effect = RuntimeError("bad cover")
    bound_view(view, controller)
    view.player_bar.set_cover = MagicMock()

    view.show_track(song)

    view.player_bar.set_cover.assert_called_once_with(1, None)


def test_show_track_without_song_id_skips_lookup(view, controller):
    song = make_song(None)
    bound_view(view, controller)
    view.player_bar.set_cover = MagicMock()

    view.show_track(song)

    controller.handle_get_cover.assert_not_called()
    view.player_bar.set_cover.assert_called_once_with(None, None)


def test_progress_playing_and_muted_delegate(view):
    view.player_bar.set_progress = MagicMock()
    view.player_bar.set_playing = MagicMock()
    view.player_bar.set_muted = MagicMock()
    view.set_progress(1, 2)
    view.set_playing(True)
    view.set_muted(False)
    view.player_bar.set_progress.assert_called_once_with(1, 2)
    view.player_bar.set_playing.assert_called_once_with(True)
    view.player_bar.set_muted.assert_called_once_with(False)


# -- scan dialog wrappers --


def test_scan_wrappers_delegate(view):
    view.scan_dialog = MagicMock()
    view.show_scan_started()
    view.show_scan_progress(1, 2)
    view.show_scan_finished()
    view.show_scan_failed("boom")
    view.scan_dialog.show_started.assert_called_once()
    view.scan_dialog.show_progress.assert_called_once_with(1, 2)
    view.scan_dialog.show_finished.assert_called_once()
    view.scan_dialog.show_failed.assert_called_once_with("boom")


# -- top-level callbacks --


def test_on_close_without_controller_destroys(view):
    view.destroy = MagicMock()
    view._on_close()
    view.destroy.assert_called_once()


def test_on_close_with_controller_shuts_down(view, controller):
    bound_view(view, controller)
    view._on_close()
    controller.shutdown.assert_called_once()


def test_on_add_folder_requires_controller(view, controller):
    view._on_add_folder("/music")
    controller.handle_add_folder.assert_not_called()

    bound_view(view, controller)
    view._on_add_folder("/music")
    controller.handle_add_folder.assert_called_once_with("/music")


def test_on_select_song_requires_controller(view, controller):
    view._on_select_song(1)
    controller.handle_select_song.assert_not_called()
    bound_view(view, controller)
    view._on_select_song(1)
    controller.handle_select_song.assert_called_once_with(1)


def test_on_favorite_song_refreshes_row(view, controller):
    updated = make_song(1)
    controller.handle_get_song.return_value = updated
    bound_view(view, controller)
    view.refresh_song_row = MagicMock()
    view._on_favorite_song(1)
    controller.handle_toggle_favorite.assert_called_once_with(1)
    view.refresh_song_row.assert_called_once_with(updated)


def test_on_favorite_song_missing_song_falls_back_to_refresh(view, controller):
    controller.handle_get_song.return_value = None
    bound_view(view, controller)
    view._on_favorite_song(1)
    controller.refresh_current_view.assert_called_once()


def test_on_favorite_song_requires_controller(view, controller):
    view._on_favorite_song(1)
    controller.handle_toggle_favorite.assert_not_called()


def test_on_navigate_routes(controller, view):
    bound_view(view, controller)
    view._on_navigate("playlists")
    controller.handle_show_playlists.assert_called_once()
    view._on_navigate("music")
    controller.handle_show_music.assert_called_once()


def test_on_navigate_requires_controller(view, controller):
    view._on_navigate("playlists")
    controller.handle_show_playlists.assert_not_called()


# -- playlist flows --


def test_create_playlist_dialog(monkeypatch, view, controller):
    bound_view(view, controller)
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: "Mix")
    view._on_create_playlist()
    controller.handle_create_playlist.assert_called_once_with("Mix")

    monkeypatch.setattr(module, "ask_text", lambda *a, **k: None)
    controller.handle_create_playlist.reset_mock()
    view._on_create_playlist()
    controller.handle_create_playlist.assert_not_called()


def test_create_playlist_swallows_validation_error(monkeypatch, view, controller):
    bound_view(view, controller)
    controller.handle_create_playlist.side_effect = ValueError("blank")
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: " ")
    view._on_create_playlist()  # must not raise


def test_create_playlist_requires_controller(monkeypatch, view, controller):
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: "Mix")
    view._on_create_playlist()
    controller.handle_create_playlist.assert_not_called()


def test_rename_playlist_dialog(monkeypatch, view, controller):
    controller.handle_get_playlist.return_value = make_playlist(3, name="Old")
    bound_view(view, controller)
    seen = {}

    def fake_ask(title, prompt, initial=""):
        seen["initial"] = initial
        return "New"

    monkeypatch.setattr(module, "ask_text", fake_ask)
    view._on_rename_playlist(3)
    assert seen["initial"] == "Old"
    controller.handle_rename_playlist.assert_called_once_with(3, "New")

    monkeypatch.setattr(module, "ask_text", lambda *a, **k: None)
    controller.handle_rename_playlist.reset_mock()
    view._on_rename_playlist(3)
    controller.handle_rename_playlist.assert_not_called()


def test_rename_missing_playlist_uses_empty_initial(monkeypatch, view, controller):
    controller.handle_get_playlist.return_value = None
    bound_view(view, controller)
    seen = {}

    def fake_ask(title, prompt, initial=""):
        seen["initial"] = initial
        return None

    monkeypatch.setattr(module, "ask_text", fake_ask)
    view._on_rename_playlist(99)
    assert seen["initial"] == ""


def test_rename_playlist_swallows_validation_error(monkeypatch, view, controller):
    controller.handle_get_playlist.return_value = make_playlist(3)
    controller.handle_rename_playlist.side_effect = ValueError("blank")
    bound_view(view, controller)
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: " ")
    view._on_rename_playlist(3)  # must not raise


def test_rename_requires_controller(monkeypatch, view, controller):
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: "New")
    view._on_rename_playlist(3)
    controller.handle_rename_playlist.assert_not_called()


def test_delete_playlist_confirmed(monkeypatch, view, controller):
    controller.handle_get_playlist.return_value = make_playlist(3, name="Mix")
    bound_view(view, controller)
    monkeypatch.setattr(module, "confirm", lambda *a, **k: True)
    view._on_delete_playlist(3)
    controller.handle_delete_playlist.assert_called_once_with(3)


def test_delete_playlist_cancelled(monkeypatch, view, controller):
    controller.handle_get_playlist.return_value = None
    bound_view(view, controller)
    seen = {}

    def fake_confirm(parent, title, message):
        seen["message"] = message
        return False

    monkeypatch.setattr(module, "confirm", fake_confirm)
    view._on_delete_playlist(3)
    controller.handle_delete_playlist.assert_not_called()
    assert "this playlist" in seen["message"]


def test_delete_requires_controller(monkeypatch, view, controller):
    monkeypatch.setattr(module, "confirm", lambda *a, **k: True)
    view._on_delete_playlist(3)
    controller.handle_delete_playlist.assert_not_called()


def test_add_song_creates_first_playlist(monkeypatch, view, controller):
    controller.handle_get_song.return_value = make_song(1, title="Song")
    controller.handle_list_playlists.return_value = []
    created = SimpleNamespace(id=5)
    controller.handle_create_playlist.return_value = created
    bound_view(view, controller)
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: "Mix")

    view._on_add_song_to_playlist(1)

    controller.handle_add_to_playlist.assert_called_once_with(5, 1)


def test_add_song_first_playlist_cancelled(monkeypatch, view, controller):
    controller.handle_list_playlists.return_value = []
    bound_view(view, controller)
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: None)
    view._on_add_song_to_playlist(1)
    controller.handle_create_playlist.assert_not_called()


def test_add_song_first_playlist_validation_error(monkeypatch, view, controller):
    controller.handle_list_playlists.return_value = []
    controller.handle_create_playlist.side_effect = ValueError("blank")
    bound_view(view, controller)
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: " ")
    view._on_add_song_to_playlist(1)
    controller.handle_add_to_playlist.assert_not_called()


def test_add_song_existing_playlist_pick(monkeypatch, view, controller):
    controller.handle_get_song.return_value = make_song(1, title="Song")
    controller.handle_list_playlists.return_value = [make_playlist(7, name="Mix")]
    bound_view(view, controller)
    seen = {}

    def fake_choose(parent, playlists, title):
        seen["title"] = title
        return 7

    monkeypatch.setattr(module, "choose_playlist", fake_choose)
    view._on_add_song_to_playlist(1)
    assert seen["title"] == "Song"
    controller.handle_add_to_playlist.assert_called_once_with(7, 1)


def test_add_song_existing_playlist_new(monkeypatch, view, controller):
    controller.handle_get_song.return_value = make_song(1, title="Song")
    controller.handle_list_playlists.return_value = [make_playlist(7)]
    created = SimpleNamespace(id=8)
    controller.handle_create_playlist.return_value = created
    bound_view(view, controller)
    monkeypatch.setattr(module, "choose_playlist", lambda *a, **k: "new")
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: "New")

    view._on_add_song_to_playlist(1)

    controller.handle_create_playlist.assert_called_once_with("New")
    controller.handle_add_to_playlist.assert_called_once_with(8, 1)


def test_add_song_new_cancelled_or_invalid(monkeypatch, view, controller):
    controller.handle_list_playlists.return_value = [make_playlist(7)]
    bound_view(view, controller)
    monkeypatch.setattr(module, "choose_playlist", lambda *a, **k: "new")

    monkeypatch.setattr(module, "ask_text", lambda *a, **k: None)
    view._on_add_song_to_playlist(1)
    controller.handle_create_playlist.assert_not_called()

    controller.handle_create_playlist.side_effect = ValueError("blank")
    monkeypatch.setattr(module, "ask_text", lambda *a, **k: " ")
    view._on_add_song_to_playlist(1)
    controller.handle_add_to_playlist.assert_not_called()


def test_add_song_dialog_cancelled(monkeypatch, view, controller):
    controller.handle_list_playlists.return_value = [make_playlist(7)]
    bound_view(view, controller)
    monkeypatch.setattr(module, "choose_playlist", lambda *a, **k: None)
    view._on_add_song_to_playlist(1)
    controller.handle_add_to_playlist.assert_not_called()


def test_add_song_missing_song_uses_placeholder_title(monkeypatch, view, controller):
    controller.handle_get_song.return_value = None
    controller.handle_list_playlists.return_value = [make_playlist(7)]
    bound_view(view, controller)
    seen = {}

    def fake_choose(parent, playlists, title):
        seen["title"] = title
        return 7

    monkeypatch.setattr(module, "choose_playlist", fake_choose)
    view._on_add_song_to_playlist(42)
    assert seen["title"] == "song 42"


def test_add_song_requires_controller(view, controller):
    view._on_add_song_to_playlist(1)
    controller.handle_add_to_playlist.assert_not_called()


def test_remove_song_from_current_playlist(view, controller):
    controller.handle_get_current_playlist.return_value = make_playlist(3)
    bound_view(view, controller)
    view._on_remove_song_from_playlist(1)
    controller.handle_remove_from_playlist.assert_called_once_with(3, 1)


def test_remove_song_without_current_playlist(view, controller):
    controller.handle_get_current_playlist.return_value = None
    bound_view(view, controller)
    view._on_remove_song_from_playlist(1)
    controller.handle_remove_from_playlist.assert_not_called()

    controller.handle_get_current_playlist.return_value = make_playlist(None)
    view._on_remove_song_from_playlist(1)
    controller.handle_remove_from_playlist.assert_not_called()


def test_remove_song_requires_controller(view, controller):
    view._on_remove_song_from_playlist(1)
    controller.handle_remove_from_playlist.assert_not_called()


# -- seek --


def test_seek_start_end_toggle_flag(view, controller):
    bound_view(view, controller)
    view._on_seek_start()
    assert controller.seeking is True
    view._on_seek_end()
    assert controller.seeking is False


def test_seek_callbacks_without_controller_are_safe(view):
    view._on_seek_start()
    view._on_seek_end()
    view._on_seek_commit(1.0)


def test_seek_commit_resets_flag(view, controller):
    bound_view(view, controller)
    view._on_seek_commit(12.0)
    controller.handle_seek.assert_called_once_with(12.0)
    assert controller.seeking is False


def test_seek_commit_resets_flag_on_error(view, controller):
    controller.handle_seek.side_effect = RuntimeError("seek failed")
    bound_view(view, controller)
    with pytest.raises(RuntimeError):
        view._on_seek_commit(12.0)
    assert controller.seeking is False
