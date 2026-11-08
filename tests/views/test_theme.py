"""Unit tests for views/theme.py."""

from __future__ import annotations

import pytest

from tests.support import fake_tk
from views.theme import Fonts, Theme, apply_dark_mode, format_duration, theme, truncate_text


def test_theme_tokens():
    assert theme.colors.accent == "#2ccae6"
    assert theme.colors.bg_app == "#121212"
    assert theme.fonts.sans == "Arial"
    assert theme.fonts.header == ("Arial", 20, "bold")
    assert theme.spacing.window_geometry == "1000x600"


def test_theme_defaults_are_immutable_dataclasses():
    from dataclasses import FrozenInstanceError

    assert Theme() == Theme()
    assert Fonts().body == ("Arial", 14)
    with pytest.raises(FrozenInstanceError):
        theme.colors.accent = "red"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0:00"),
        (0.9, "0:00"),
        (59.9, "0:59"),
        (60, "1:00"),
        (225.9, "3:45"),
        (3599, "59:59"),
        (-5, "0:00"),
        (None, "0:00"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


@pytest.mark.parametrize(
    ("text", "max_chars", "expected"),
    [
        ("Fortnight", 24, "Fortnight"),
        ("x" * 24, 24, "x" * 24),
        ("x" * 25, 24, "x" * 23 + "…"),
        ("", 24, ""),
        (None, 24, ""),
        ("abcdef", 1, "…"),
        ("abcdef", 0, "…"),
    ],
)
def test_truncate_text(text, max_chars, expected):
    assert truncate_text(text, max_chars) == expected


def test_apply_dark_mode_uses_customtkinter():
    apply_dark_mode()
    assert fake_tk.appearance_modes == ["Dark"]
    assert fake_tk.color_themes == ["dark-blue"]
