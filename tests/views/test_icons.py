"""Unit tests for views/icons.py (delegation + lru_cache)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import views.icons as icons


@pytest.fixture()
def loader(monkeypatch):
    mock = MagicMock(side_effect=lambda name, *args, **kwargs: f"{name}:{args}")
    monkeypatch.setattr(icons, "load_icon", mock)
    return mock


def test_getters_delegate_with_expected_sizes(loader):
    assert icons.get_logo().startswith("logo:")
    assert icons.get_logo_box().startswith("logo_box:")
    assert icons.get_play_button().startswith("play:")
    assert icons.get_pause_button().startswith("pause:")
    assert icons.get_next_button().startswith("next:")
    assert icons.get_prev_button().startswith("prev:")
    assert icons.get_muted().startswith("muted:")
    assert icons.get_notmuted().startswith("notmuted:")
    assert icons.get_repeat().startswith("repeat:")
    assert icons.get_folder().startswith("folder:")
    assert icons.get_music().startswith("music:")
    assert icons.get_playlist().startswith("playlist:")

    assert icons.get_now_playing() == "now_playing:(60, 60)"
    assert icons.get_now_playing(12) == "now_playing:(12, 12)"
    assert icons.get_heart_outline() == "heart_outline:(20, 20)"
    assert icons.get_heart_filled(22) == "heart_filled:(22, 22)"


def test_load_icon_is_cached(monkeypatch):
    icons.load_icon.cache_clear()
    manager_load = MagicMock(return_value="image")
    monkeypatch.setattr(icons._manager, "load", manager_load)

    first = icons.load_icon("play", 32, 32)
    second = icons.load_icon("play", 32, 32)

    assert first == second == "image"
    assert manager_load.call_count == 1
    assert icons.load_icon.cache_info().hits >= 1


def test_load_icon_passes_with_dark_flag(monkeypatch):
    icons.load_icon.cache_clear()
    manager_load = MagicMock(return_value="image")
    monkeypatch.setattr(icons._manager, "load", manager_load)

    icons.load_icon("logo", 1, 2, with_dark=True)

    manager_load.assert_called_once_with("logo", (1, 2), with_dark=True)
