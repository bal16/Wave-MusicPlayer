"""Unit tests for views/widgets/player_bar.py (Tk faked)."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest

from tests.support import fake_tk
from tests.support.doubles import make_song
from views.widgets import player_bar as module
from views.widgets.player_bar import PlayerBar


@pytest.fixture()
def bar():
    return PlayerBar(fake_tk.FakeWidget())


def _png_bytes(color=(10, 20, 30), size=(32, 32)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_initial_state(bar):
    assert bar._total == 0.0
    assert bar._dragging is False
    assert bar._cover_cache == {}
    assert bar.lbl_song_title.text == "Song Title"
    assert bar.lbl_art.image is not None  # bundled fallback


def test_set_track_updates_labels_and_resets_progress(bar):
    song = make_song(1, title="A" * 40, artist="B" * 40, duration=225.9)
    bar.set_track(song)
    assert bar.lbl_song_title.text == "A" * 23 + "…"
    assert bar.lbl_song_artist.text == "B" * 23 + "…"
    assert bar._total == 225.9
    assert bar.lbl_total_time.text == "3:45"
    assert bar.slider.get() == 0.0


def test_set_progress_updates_labels_and_slider(bar):
    bar.set_progress(30, 120)
    assert bar.lbl_current_time.text == "0:30"
    assert bar.lbl_total_time.text == "2:00"
    assert bar.slider.get() == 0.25


def test_set_progress_clamps_fraction(bar):
    bar.set_progress(999, 100)
    assert bar.slider.get() == 1.0
    bar.set_progress(-5, 100)
    assert bar.slider.get() == 0.0


def test_set_progress_skips_slider_while_dragging(bar):
    bar._dragging = True
    bar.set_progress(30, 120)
    assert bar.slider.get() == 0.0
    assert bar.lbl_current_time.text == "0:30"


def test_set_progress_ignores_zero_total_for_slider(bar):
    bar.set_progress(30, 0)
    assert bar.slider.get() == 0.0


def test_set_playing_swaps_icon(bar, monkeypatch):
    monkeypatch.setattr(module, "get_pause_button", lambda: "pause")
    monkeypatch.setattr(module, "get_play_button", lambda: "play")
    bar.set_playing(True)
    assert bar.btn_play.image == "pause"
    bar.set_playing(False)
    assert bar.btn_play.image == "play"


def test_set_muted_swaps_icon(bar, monkeypatch):
    monkeypatch.setattr(module, "get_muted", lambda: "muted")
    monkeypatch.setattr(module, "get_notmuted", lambda: "sound")
    bar.set_muted(True)
    assert bar.btn_volume.image == "muted"
    bar.set_muted(False)
    assert bar.btn_volume.image == "sound"


def test_set_favorite_swaps_icon(bar, monkeypatch):
    monkeypatch.setattr(module, "get_heart_filled", lambda size: f"filled:{size}")
    monkeypatch.setattr(module, "get_heart_outline", lambda size: f"outline:{size}")
    bar.set_favorite(True)
    assert bar.like_button.image == "filled:22"
    bar.set_favorite(False)
    assert bar.like_button.image == "outline:22"


def test_set_cover_uses_bundled_asset_by_default(bar):
    assert bar.lbl_art.image is not None
    assert bar.lbl_art.text == ""


def test_set_cover_decodes_and_caches(bar, monkeypatch):
    decode = MagicMock(return_value="thumb")
    monkeypatch.setattr(PlayerBar, "_decode_cover", staticmethod(decode))
    bar.set_cover(1, b"bytes")
    bar.set_cover(1, b"bytes")
    assert decode.call_count == 1
    assert bar._cover_cache[1] == "thumb"
    assert bar.lbl_art.image == "thumb"


def test_set_cover_falls_back_when_decode_fails(bar, monkeypatch):
    monkeypatch.setattr(PlayerBar, "_decode_cover", staticmethod(lambda data: None))
    monkeypatch.setattr(module, "get_now_playing", lambda: "fallback")
    bar.set_cover(1, b"garbage")
    assert bar.lbl_art.image == "fallback"
    assert 1 not in bar._cover_cache


def test_set_cover_ignores_data_without_song_id(bar):
    bar.set_cover(None, b"bytes")
    assert bar._cover_cache == {}


def test_set_cover_text_placeholder_when_asset_fails(bar, monkeypatch):
    def boom():
        raise RuntimeError("missing asset")

    monkeypatch.setattr(module, "get_now_playing", boom)
    bar.set_cover(None, None)
    assert bar.lbl_art.image is None
    assert bar.lbl_art.text == "[IMG]"


def test_decode_cover_valid_and_garbage():
    assert PlayerBar._decode_cover(_png_bytes()) is not None
    assert PlayerBar._decode_cover(b"not-an-image") is None


def test_slider_press_and_release_commits_seek(bar):
    seen = []
    bar.on_seek = seen.append
    bar._total = 200.0
    bar.slider.set(0.5)
    bar._on_slider_press(None)
    assert bar._dragging is True
    bar._on_slider_release(None)
    assert bar._dragging is False
    assert seen == [100.0]


def test_slider_release_without_total_does_not_commit(bar):
    seen = []
    bar.on_seek = seen.append
    bar._total = 0.0
    bar.slider.set(0.5)
    bar._on_slider_release(None)
    assert seen == []


def test_slider_release_without_callback_is_safe(bar):
    bar._total = 100.0
    bar._on_slider_release(None)


def test_slider_move_updates_time_only_while_dragging(bar):
    bar._total = 120.0
    bar.slider.set(0.5)
    bar._on_slider_move(0.5)
    assert bar.lbl_current_time.text == "0:00"  # not dragging yet
    bar._dragging = True
    bar._on_slider_move(0.5)
    assert bar.lbl_current_time.text == "1:00"


def test_volume_move_emits(bar):
    seen = []
    bar.on_volume = seen.append
    bar._on_volume_move(0.25)
    assert seen == [0.25]


def test_emitters_call_bound_callbacks(bar):
    calls = []
    bar.on_play = lambda: calls.append("play")
    bar.on_next = lambda: calls.append("next")
    bar.on_prev = lambda: calls.append("prev")
    bar.on_mute = lambda: calls.append("mute")
    bar.on_favorite = lambda: calls.append("favorite")

    bar._emit_play()
    bar._emit_next()
    bar._emit_prev()
    bar._emit_mute()
    bar._emit_favorite()
    assert calls == ["play", "next", "prev", "mute", "favorite"]


def test_emitters_without_callbacks_are_safe(bar):
    bar._emit_play()
    bar._emit_next()
    bar._emit_prev()
    bar._emit_mute()
    bar._emit_favorite()
