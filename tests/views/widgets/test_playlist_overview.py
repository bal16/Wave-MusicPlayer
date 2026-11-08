"""Unit tests for views/widgets/playlist_overview.py (Tk faked)."""

from __future__ import annotations

from tests.support import fake_tk
from tests.support.doubles import make_playlist
from views.widgets.playlist_overview import PlaylistOverview


def make_overview():
    return PlaylistOverview(fake_tk.FakeWidget())


def test_initial_state():
    overview = make_overview()
    assert overview.lbl_header.text == "Playlists"
    assert overview.btn_new.text == "+ New Playlist"
    assert overview._rows == []
    assert overview.lbl_empty.winfo_ismapped() is True


def test_set_playlists_renders_rows():
    overview = make_overview()
    overview.set_playlists([make_playlist(1, name="A", song_count=2), make_playlist(2, name="B")])
    assert len(overview._rows) == 2
    assert overview.lbl_empty.winfo_ismapped() is False


def test_set_playlists_empty_shows_empty_state():
    overview = make_overview()
    overview.set_playlists([make_playlist(1)])
    overview.set_playlists([])
    assert overview._rows == []
    assert overview.lbl_empty.winfo_ismapped() is True


def test_set_playlists_replaces_old_rows():
    overview = make_overview()
    overview.set_playlists([make_playlist(1)])
    old = overview._rows[0]
    overview.set_playlists([make_playlist(2)])
    assert old._destroyed is True
    assert len(overview._rows) == 1


def test_playlist_row_buttons_emit_callbacks():
    selected, renamed, deleted = [], [], []
    overview = make_overview()
    overview.on_select = selected.append
    overview.on_rename = renamed.append
    overview.on_delete = deleted.append
    playlist = make_playlist(5, name="Mix", song_count=3)
    overview.set_playlists([playlist])

    fake_tk.widget_by_text(overview._rows[0], "Mix").invoke()
    fake_tk.widget_by_text(overview._rows[0], "Rename").invoke()
    fake_tk.widget_by_text(overview._rows[0], "✕").invoke()

    assert selected == [5]
    assert renamed == [5]
    assert deleted == [5]
    assert fake_tk.widget_by_text(overview._rows[0], "3 songs") is not None


def test_new_button_emits_create():
    overview = make_overview()
    called = []
    overview.on_create = lambda: called.append(True)
    overview.btn_new.invoke()
    assert called == [True]


def test_emit_helpers_ignore_none_and_missing_callbacks():
    overview = make_overview()
    overview._emit_select(None)
    overview._emit_rename(None)
    overview._emit_delete(None)
    overview._emit_create()  # no callback bound
