"""Central design system — single owner of colors, fonts, spacing, and style helpers.

Why this file exists: hex codes and font tuples were scattered across
view.py / Sidebar / MainContent / PlayerBar / config.py, which made
restyling risky. All new UI code must import from here; legacy modules
are migrated gradually (config.py re-exports these values for compat).

Style guide (short version):
- Dark Spotify-like theme: app bg #121212, sidebar #181818, player #0f0f0f.
- Accent: #2ccae6 (logo, active states). Muted text: grey.
- Body font: Arial; headers bold 20, row titles bold 14.
- Transparent buttons with hover #333333; no heavy shadows or gradients.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Colors:
    """Semantic color tokens (raw hex lives only here)."""

    bg_app: str = "#121212"
    bg_sidebar: str = "#181818"
    bg_player: str = "#0f0f0f"
    surface: str = "#1e1e1e"
    accent: str = "#2ccae6"
    text_primary: str = "white"
    text_muted: str = "grey"
    hover: str = "#333333"
    progress_track: str = "#333333"
    progress_fill: str = "white"


@dataclass(frozen=True, slots=True)
class Fonts:
    """Font family + scale."""

    sans: str = "Arial"
    header: tuple = ("Arial", 20, "bold")
    row_title: tuple = ("Arial", 14, "bold")
    body: tuple = ("Arial", 14)
    menu: tuple = ("Arial", 16)
    small_muted: tuple = ("Arial", 12)


@dataclass(frozen=True, slots=True)
class Spacing:
    """Padding / geometry tokens."""

    pad_s: int = 5
    pad_m: int = 10
    pad_l: int = 20
    pad_xl: int = 40
    sidebar_width: int = 200
    player_height: int = 90
    window_geometry: str = "1000x600"
    startup_geometry: str = "1100x650"


@dataclass(frozen=True, slots=True)
class Theme:
    colors: Colors = Colors()
    fonts: Fonts = Fonts()
    spacing: Spacing = Spacing()


theme = Theme()


def format_duration(seconds: float) -> str:
    """Format seconds as m:ss for views (DB keeps float seconds)."""
    total = max(0, int(seconds or 0))
    return f"{total // 60}:{total % 60:02d}"


def apply_dark_mode() -> None:
    """Apply the global CustomTkinter dark theme. Call once at startup."""
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
