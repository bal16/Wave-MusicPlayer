"""Unit tests for views/widgets/splash_screen.py (Tk faked)."""

from __future__ import annotations

from tests.support import fake_tk
from views.theme import theme
from views.widgets.splash_screen import SplashScreen


def test_splash_screen_builds_centered_window():
    parent = fake_tk.FakeWidget()
    splash = SplashScreen(parent)

    assert splash.kwargs["overrideredirect"] is True
    assert splash.kwargs["attributes"] == (("-topmost", True), {})
    assert splash.kwargs["geometry"] == "500x300+710+390"
    assert splash.kwargs["background"] == theme.colors.surface
    assert splash.lbl_icon.image is not None
    assert splash.progress.get() == 0
