"""Cached icon loader.

Wraps utils.icon_manager.IconManager with lru_cache so repeated loads
of the same (name, size) reuse the CTkImage instead of reopening files.
"""

from __future__ import annotations

from functools import lru_cache

from utils.icon_manager import IconManager

_manager = IconManager()


@lru_cache(maxsize=64)
def load_icon(name: str, width: int = 20, height: int = 20, with_dark: bool = False):
    """Load an icon from assets/icons, cached by (name, size)."""
    return _manager.load(name, (width, height), with_dark=with_dark)


def get_logo():
    return load_icon("logo", 128, 25)


def get_logo_box():
    return load_icon("logo_box", 176, 130)


def get_play_button():
    return load_icon("play", 32, 32)


def get_pause_button():
    return load_icon("pause", 32, 32)


def get_next_button():
    return load_icon("next", 32, 32)


def get_prev_button():
    return load_icon("prev", 32, 32)


def get_now_playing(size: int = 60):
    return load_icon("now_playing", size, size)


def get_muted():
    return load_icon("muted", 20, 20)


def get_notmuted():
    return load_icon("notmuted", 20, 20)


def get_repeat():
    return load_icon("repeat", 20, 20)


def get_heart_outline(size: int = 20):
    return load_icon("heart_outline", size, size)


def get_heart_filled(size: int = 20):
    return load_icon("heart_filled", size, size)


def get_folder():
    return load_icon("folder", 20, 20)


def get_music():
    return load_icon("music", 20, 20)


def get_playlist():
    return load_icon("playlist", 20, 20)
