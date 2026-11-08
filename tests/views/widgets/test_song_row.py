"""Unit tests for views/widgets/song_row.py (Tk faked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from tests.support import fake_tk
from tests.support.doubles import make_song
from views.theme import theme
from views.widgets import song_row as module
from views.widgets.song_row import SongRow, configure_columns, favorite_icon, format_song_row


def make_row(song=None, **kwargs):
    scroll = kwargs.pop("scroll_frame", fake_tk.FakeScrollableFrame())
    master = kwargs.pop("master", scroll)
    return SongRow(master, 1, song or make_song(1), scroll_frame=scroll, **kwargs)


def test_configure_columns_applies_shared_spec():
    frame = fake_tk.FakeWidget()
    configure_columns(frame)
    assert frame.kwargs["column:0"] == {"weight": 0, "minsize": 34}
    assert frame.kwargs["column:1"] == {"weight": 1}
    assert frame.kwargs["column:4"] == {"weight": 0, "minsize": 56}


def test_format_song_row_mapping():
    row = format_song_row(make_song(1))
    assert row == {
        "title": "Title 1",
        "artist": "Artist",
        "duration": "3:20",
        "favorite_mark": "♡",
    }
    assert format_song_row(make_song(2, is_favorite=True))["favorite_mark"] == "♥"


def test_favorite_icon_switches_asset(monkeypatch):
    monkeypatch.setattr(module, "get_heart_filled", lambda: "filled")
    monkeypatch.setattr(module, "get_heart_outline", lambda: "outline")
    assert favorite_icon(True) == "filled"
    assert favorite_icon(False) == "outline"


def test_row_renders_labels_and_add_button():
    song = make_song(1, title="Hello", artist="World", duration=225.9)
    row = make_row(song)
    assert row.song_id == 1
    assert row.lbl_num.text == "1"
    assert row.lbl_title.text == "Hello"
    assert row.lbl_artist.text == "World"
    assert row.lbl_duration.text == "3:45"
    assert row.btn_list.text == "+"
    assert row.kwargs["pack"] == {"fill": "x", "pady": 2}


def test_row_uses_remove_button_in_playlist_view():
    row = make_row(allow_remove=True)
    assert row.btn_list.text == "×"


def test_row_binds_wheel_scroll_on_every_child():
    row = make_row()
    assert "<Button-4>" in row.bindings
    assert "<Button-4>" in row.lbl_title.bindings
    assert "<Button-4>" in row.btn_fav.bindings


def test_favorite_button_emits_song_id():
    seen = []
    row = make_row(on_favorite=seen.append)
    row.btn_fav.invoke()
    assert seen == [1]


def test_add_and_remove_buttons_emit_callbacks():
    added, removed = [], []
    add_row = make_row(on_add=added.append)
    remove_row = make_row(allow_remove=True, on_remove=removed.append)
    add_row.btn_list.invoke()
    remove_row.btn_list.invoke()
    assert added == [1]
    assert removed == [1]


def test_clicking_row_emits_select():
    seen = []
    row = make_row(on_select=seen.append)
    row.emit("<Button-1>")
    assert seen == [1]


def test_emit_ignores_missing_song_id_and_missing_callback():
    callback = MagicMock()
    row = SongRow(
        fake_tk.FakeScrollableFrame(),
        1,
        make_song(None),
        scroll_frame=fake_tk.FakeScrollableFrame(),
        on_select=callback,
    )
    row.emit("<Button-1>")
    callback.assert_not_called()
    row2 = make_row()
    row2.emit("<Button-1>")  # no callback bound


def test_hover_feedback_when_not_highlighted():
    row = make_row()
    row.emit("<Enter>")
    assert row.kwargs["fg_color"] == theme.colors.hover
    row.emit("<Leave>")
    assert row.kwargs["fg_color"] == "transparent"


def test_hover_is_ignored_while_highlighted():
    row = make_row()
    row.set_highlight(True)
    row.emit("<Enter>")
    assert row.kwargs["fg_color"] == theme.colors.surface


def test_set_highlight_updates_colors():
    row = make_row()
    row.set_highlight(True)
    assert row._highlighted is True
    assert row.kwargs["fg_color"] == theme.colors.surface
    assert row.lbl_num.kwargs["text_color"] == theme.colors.accent

    row.set_highlight(False)
    assert row._highlighted is False
    assert row.kwargs["fg_color"] == "transparent"
    assert row.lbl_num.kwargs["text_color"] == theme.colors.text_muted


def test_refresh_updates_labels_and_icon(monkeypatch):
    monkeypatch.setattr(module, "favorite_icon", lambda value: f"heart:{value}")
    row = make_row()
    row.refresh(make_song(1, title="New", artist="Singer", duration=61, is_favorite=True))
    assert row.lbl_title.text == "New"
    assert row.lbl_artist.text == "Singer"
    assert row.lbl_duration.text == "1:01"
    assert row.btn_fav.image == "heart:True"


def test_wheel_scroll_calls_canvas_once():
    scroll = fake_tk.FakeScrollableFrame()
    scroll._parent_canvas.set_view(0.0, 0.5)
    row = make_row(scroll_frame=scroll)
    row.emit("<Button-4>")
    row.emit("<Button-5>")
    assert scroll._parent_canvas.scroll_calls == [(-1, "units"), (1, "units")]


def test_wheel_scroll_noop_when_list_fits():
    scroll = fake_tk.FakeScrollableFrame()  # default view is (0.0, 1.0)
    row = make_row(scroll_frame=scroll)
    row.emit("<Button-4>")
    assert scroll._parent_canvas.scroll_calls == []
