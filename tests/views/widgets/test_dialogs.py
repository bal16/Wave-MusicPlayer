"""Unit tests for views/widgets/dialogs.py (Tk faked)."""

from __future__ import annotations

import customtkinter as ctk

from tests.support import fake_tk
from tests.support.doubles import make_playlist
from views.widgets import dialogs


class AutoParent(fake_tk.FakeWidget):
    """Fake parent whose wait_window clicks a requested button."""

    def __init__(self, button_text=None):
        super().__init__()
        self.button_text = button_text
        self.top = None
        self.closed = False

    def wait_window(self, window=None):
        self.top = window
        if self.button_text is not None:
            button = fake_tk.widget_by_text(window, self.button_text)
            if button is not None:
                button.invoke()
                self.closed = True


# -- ask_text --


def test_ask_text_returns_stripped_value():
    ctk.CTkInputDialog.next_value = "  Chill Mix  "
    assert dialogs.ask_text("Title", "Prompt") == "Chill Mix"


def test_ask_text_returns_none_on_cancel():
    ctk.CTkInputDialog.next_value = None
    assert dialogs.ask_text("Title", "Prompt") is None


def test_ask_text_returns_none_on_blank():
    ctk.CTkInputDialog.next_value = "   "
    assert dialogs.ask_text("Title", "Prompt") is None


def test_ask_text_prefills_initial_value():
    ctk.CTkInputDialog.next_value = "New"
    dialogs.ask_text("Title", "Prompt", initial="Old")
    entry = ctk.CTkInputDialog.instances[-1]._entry
    assert entry.kwargs["inserted"] == (0, "Old")


# -- choose_playlist --


def test_choose_playlist_returns_picked_id():
    playlists = [make_playlist(3, name="Mix", song_count=2)]
    parent = AutoParent("Mix (2)")
    assert dialogs.choose_playlist(parent, playlists, "Song") == 3
    assert parent.top.kwargs["title"] == "Add to playlist"
    assert parent.top.kwargs["geometry"] == "320x400"
    assert parent.top.kwargs["grab_set"] is True


def test_choose_playlist_returns_new():
    parent = AutoParent("+ New playlist…")
    assert dialogs.choose_playlist(parent, [make_playlist(1)], "Song") == "new"


def test_choose_playlist_returns_none_on_cancel():
    parent = AutoParent("Cancel")
    assert dialogs.choose_playlist(parent, [make_playlist(1)], "Song") is None


def test_choose_playlist_returns_none_when_window_closed():
    parent = AutoParent(button_text=None)
    assert dialogs.choose_playlist(parent, [make_playlist(1)], "Song") is None


# -- confirm --


def test_confirm_true_on_delete():
    parent = AutoParent("Delete")
    assert dialogs.confirm(parent, "Delete playlist", "Sure?") is True
    assert parent.top.kwargs["title"] == "Delete playlist"
    assert parent.top.kwargs["geometry"] == "300x150"


def test_confirm_false_on_cancel():
    parent = AutoParent("Cancel")
    assert dialogs.confirm(parent, "Delete playlist", "Sure?") is False
