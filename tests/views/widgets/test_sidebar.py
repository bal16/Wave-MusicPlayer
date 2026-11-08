"""Unit tests for views/widgets/sidebar.py (Tk + filedialog faked)."""

from __future__ import annotations

from tests.support import fake_tk
from views.widgets import sidebar as module
from views.widgets.sidebar import Sidebar


def make_sidebar():
    return Sidebar(fake_tk.FakeWidget())


def test_initial_buttons():
    sidebar = make_sidebar()
    assert fake_tk.widget_by_text(sidebar, "Add") is not None
    assert fake_tk.widget_by_text(sidebar, "Music") is not None
    assert fake_tk.widget_by_text(sidebar, "Playlist") is not None
    assert sidebar.logo is not None


def test_get_button_packs_and_returns_button():
    sidebar = make_sidebar()
    button = sidebar.get_button("Extra", image="icon")
    assert isinstance(button, fake_tk.FakeCTkButton)
    assert button.kwargs["pack"] == {"fill": "x", "padx": 20, "pady": 10}


def test_music_and_playlist_buttons_navigate():
    sidebar = make_sidebar()
    seen = []
    sidebar.on_navigate = seen.append
    fake_tk.widget_by_text(sidebar, "Music").invoke()
    fake_tk.widget_by_text(sidebar, "Playlist").invoke()
    assert seen == ["music", "playlists"]


def test_add_folder_cancelled_does_nothing():
    sidebar = make_sidebar()
    seen = []
    sidebar.on_add_folder = seen.append
    module.filedialog.askdirectory_result = ""
    sidebar.open_add_music_window()
    assert module.filedialog.askdirectory_calls == 1
    assert seen == []


def test_add_folder_hands_path_to_callback():
    sidebar = make_sidebar()
    seen = []
    sidebar.on_add_folder = seen.append
    module.filedialog.askdirectory_result = "/music"
    sidebar.open_add_music_window()
    assert seen == ["/music"]


def test_add_folder_without_callback_is_safe():
    sidebar = make_sidebar()
    module.filedialog.askdirectory_result = "/music"
    sidebar.open_add_music_window()


def test_navigate_without_callback_is_safe():
    make_sidebar()._emit_navigate("music")
