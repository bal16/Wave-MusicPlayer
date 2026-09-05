"""Legacy config — compat re-export over views.theme.

New code must import from views.theme directly. These aliases stay so
Sidebar / MainContent / PlayerBar keep working untouched in Phase 0.

Note: icon loading is still eager here (legacy behavior). The cached
loader lives in utils.icons; lazy icon binding lands with the views
refactor in a later phase.
"""

from __future__ import annotations

from utils.icons import get_logo, get_logo_box, get_pause_button, get_play_button
from views.theme import theme

# Colors (canonical values live in views.theme.Colors)
COLOR_BG = theme.colors.surface
COLOR_ACCENT = theme.colors.accent
COLOR_TEXT = theme.colors.text_primary

# Fonts
FONT_SANS_SERIF = theme.fonts.sans

# Icons (eager for Phase 0 compat; cached under the hood)
ICON_LOGO_BOX = get_logo_box()
ICON_LOGO = get_logo()
ICON_PLAY_BUTTON = get_play_button()
ICON_PAUSE_BUTTON = get_pause_button()

__all__ = [
    "COLOR_ACCENT",
    "COLOR_BG",
    "COLOR_TEXT",
    "FONT_SANS_SERIF",
    "ICON_LOGO",
    "ICON_LOGO_BOX",
    "ICON_PAUSE_BUTTON",
    "ICON_PLAY_BUTTON",
    "theme",
]
