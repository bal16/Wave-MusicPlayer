"""Legacy config — compat re-export over views.theme.

New code must import from views.theme (tokens) and utils.icons (cached,
lazy icon loading) directly. These aliases stay so legacy modules keep
working during migration.
"""

from __future__ import annotations

from views.theme import theme

# Colors (canonical values live in views.theme.Colors)
COLOR_BG = theme.colors.surface
COLOR_ACCENT = theme.colors.accent
COLOR_TEXT = theme.colors.text_primary

# Fonts
FONT_SANS_SERIF = theme.fonts.sans

__all__ = [
    "COLOR_ACCENT",
    "COLOR_BG",
    "COLOR_TEXT",
    "FONT_SANS_SERIF",
    "theme",
]
