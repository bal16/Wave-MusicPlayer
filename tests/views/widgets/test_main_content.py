"""Unit tests for views/widgets/main_content.py (Tk faked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from tests.support import fake_tk
from tests.support.doubles import make_song
from views.widgets.main_content import (
    CHUNK_SIZE,
    CHUNK_THRESHOLD,
    MAX_VISIBLE_ROWS,
    MainContent,
)


def make_content():
    return MainContent(fake_tk.FakeWidget())


def test_constants_are_sane():
    assert MAX_VISIBLE_ROWS == 300
    assert CHUNK_THRESHOLD == 80
    assert CHUNK_SIZE == 40


def test_set_header_changes_label():
    content = make_content()
    content.set_header("Playlist X")
    assert content.lbl_header.text == "Playlist X"


def test_set_songs_empty_shows_empty_state():
    content = make_content()
    content.set_songs([])
    assert content._rows == []
    assert content._row_by_id == {}
    assert content.lbl_empty.kwargs["text"].startswith("No songs yet")
    assert content.lbl_empty.winfo_ismapped() is True
    assert content.lbl_overflow.winfo_ismapped() is False


def test_set_songs_renders_rows_and_hides_empty_state():
    content = make_content()
    content.set_songs([make_song(1), make_song(2)])
    assert len(content._rows) == 2
    assert set(content._row_by_id) == {1, 2}
    assert content.lbl_empty.winfo_ismapped() is False


def test_set_songs_passes_allow_remove_and_playing_highlight():
    content = make_content()
    content.set_songs([make_song(1)], allow_remove=True, playing_id=1)
    row = content._rows[0]
    assert row.btn_list.text == "×"
    assert row._highlighted is True


def test_set_songs_replaces_previous_rows():
    content = make_content()
    content.set_songs([make_song(1), make_song(2)])
    old_rows = list(content._rows)
    content.set_songs([make_song(3)])
    assert [row.song_id for row in content._rows] == [3]
    assert all(row._destroyed for row in old_rows)


def test_set_songs_truncates_to_max_visible_rows():
    content = make_content()
    content.set_songs([make_song(i) for i in range(1, MAX_VISIBLE_ROWS + 6)])
    assert len(content._rows) == MAX_VISIBLE_ROWS
    assert "5 more" in content.lbl_overflow.kwargs["text"]
    assert content.lbl_overflow.winfo_ismapped() is True


def test_set_playing_highlights_and_unhighlights():
    content = make_content()
    content.set_songs([make_song(1), make_song(2)])

    assert content.set_playing(1) is True
    assert content._row_by_id[1]._highlighted is True

    assert content.set_playing(1) is True  # same id short-circuit
    assert content.set_playing(None) is True
    assert content._row_by_id[1]._highlighted is False

    assert content.set_playing(2) is True
    assert content._row_by_id[2]._highlighted is True
    assert content.set_playing(999) is False


def test_update_song_fast_path_and_misses():
    content = make_content()
    content.set_songs([make_song(1)])
    assert content.update_song(make_song(None)) is False
    assert content.update_song(make_song(999)) is False
    assert content.update_song(make_song(1, title="Changed")) is True
    assert content._row_by_id[1].lbl_title.text == "Changed"


def test_create_song_row_registers_without_id():
    content = make_content()
    row = content.create_song_row(1, make_song(None))
    assert row in content._rows
    assert content._row_by_id == {}


def test_chunked_render_stops_on_tcl_error(monkeypatch):
    content = make_content()
    monkeypatch.setattr(
        content, "create_song_row", lambda *a, **k: (_ for _ in ()).throw(fake_tk.FakeTclError())
    )
    content._render_chunked([make_song(1), make_song(2)])  # must not raise


def test_finish_overflow_hides_note_when_under_limit():
    content = make_content()
    content._finish_overflow(MAX_VISIBLE_ROWS)
    assert content.lbl_overflow.winfo_ismapped() is False


def test_emitters_only_fire_with_id_and_callback():
    content = make_content()
    content.on_select = MagicMock()
    content.on_favorite = MagicMock()
    content.on_add_to_playlist = MagicMock()
    content.on_remove_from_playlist = MagicMock()

    content._emit_select(None)
    content._emit_favorite(None)
    content._emit_add_to_playlist(None)
    content._emit_remove(None)
    for callback in (
        content.on_select,
        content.on_favorite,
        content.on_add_to_playlist,
        content.on_remove_from_playlist,
    ):
        callback.assert_not_called()

    content._emit_select(7)
    content._emit_favorite(8)
    content._emit_add_to_playlist(9)
    content._emit_remove(10)
    content.on_select.assert_called_once_with(7)
    content.on_favorite.assert_called_once_with(8)
    content.on_add_to_playlist.assert_called_once_with(9)
    content.on_remove_from_playlist.assert_called_once_with(10)


def test_emitters_are_noops_without_callbacks():
    content = make_content()
    content._emit_select(1)
    content._emit_favorite(1)
    content._emit_add_to_playlist(1)
    content._emit_remove(1)
