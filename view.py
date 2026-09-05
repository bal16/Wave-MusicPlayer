from __future__ import annotations

import time
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

from components.dialogs import ask_text, choose_playlist, confirm
from components.MainContent import MainContent
from components.PlayerBar import PlayerBar
from components.PlaylistOverview import PlaylistOverview
from components.Sidebar import Sidebar
from components.SplashScreen import SplashScreen

if TYPE_CHECKING:
    from controller import MainController as Controller

    from domain.entities import Playlist, Song


class View(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.controller: Controller | None = None  # Placeholder

        self.withdraw()

        self.splash = SplashScreen(self)

        self.loading_step = 0
        self.run_loading()

        self.title("Wave Music Player")
        self.geometry("1100x650")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("View initialized")

    def set_controller(self, controller: Controller):
        """Accept object controller from outside, then bind view callbacks.

        Binding happens here (not in setup_ui) because the controller
        only exists after the View is fully constructed.
        """
        self.controller = controller
        self.sidebar.on_add_folder = self._on_add_folder
        self.sidebar.on_navigate = self._on_navigate
        self.main_area.on_select = self._on_select_song
        self.main_area.on_favorite = self._on_favorite_song
        self.main_area.on_add_to_playlist = self._on_add_song_to_playlist
        self.main_area.on_remove_from_playlist = self._on_remove_song_from_playlist
        self.playlist_view.on_select = controller.handle_select_playlist
        self.playlist_view.on_create = self._on_create_playlist
        self.playlist_view.on_rename = self._on_rename_playlist
        self.playlist_view.on_delete = self._on_delete_playlist
        self.player_bar.on_play = controller.handle_play_pause
        self.player_bar.on_next = controller.handle_next
        self.player_bar.on_prev = controller.handle_prev
        self.player_bar.on_volume = controller.handle_volume
        self.player_bar.on_mute = controller.handle_mute
        self.player_bar.on_favorite = controller.handle_toggle_current_favorite
        self.player_bar.on_seek = self._on_seek_commit
        # Hold the progress ticker off for the whole slider drag.
        self.player_bar.slider.bind("<ButtonPress-1>", self._on_seek_start, add="+")
        self.player_bar.slider.bind("<ButtonRelease-1>", self._on_seek_end, add="+")
        logger.debug("Controller set and callbacks bound")

    def run_loading(self):
        # Visual splash only. DB setup lives in main(), not here.
        self.update_splash_progress(0.1)
        self.update()

        time.sleep(0.5)
        self.update_splash_progress(0.5)

        time.sleep(0.5)
        self.update_splash_progress(1.0)

        self.finish_loading()

    def finish_loading(self):
        if hasattr(self, "splash"):
            self.splash.destroy()

        self.center_main_window()
        self.deiconify()  # Show

        self.setup_ui()

    def update_splash_progress(self, val):
        if hasattr(self, "splash") and self.splash.winfo_exists():
            self.splash.progress.set(val)
            self.splash.update_idletasks()

    def center_main_window(self):
        w, h = 1000, 600
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (ws / 2) - (w / 2), (hs / 2) - (h / 2)
        self.geometry(f"{w}x{h}+{int(x)}+{int(y)}")

    def setup_ui(self):
        # Grid Configuration (Root)
        # Row 0: Main Content (Expandable), Row 1: Player Bar (Fixed)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Col 0: Sidebar (Fixed), Col 1: Content (Expandable)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # --- A. SIDEBAR ---
        self.sidebar = Sidebar(self, width=200, corner_radius=0, fg_color="#181818")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # --- B. MAIN CONTENT (songs + playlists share this cell) ---
        self.main_area = MainContent(self, fg_color="#121212", corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.playlist_view = PlaylistOverview(self, fg_color="#121212", corner_radius=0)
        self.playlist_view.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.playlist_view.grid_remove()  # library list is the default view

        # --- C. BOTTOM PLAYER BAR ---
        self.player_bar = PlayerBar(self, height=90, corner_radius=0, fg_color="#0f0f0f")
        self.player_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    ## METHOD FOR DESTROY self.main_area WHEN REFRESH IS NEEDED
    def refresh_song_list(self):
        """Deprecated: prefer show_songs() in-place updates.

        Kept for one phase so external callers keep working.
        """
        logger.warning("refresh_song_list() is deprecated, use show_songs()")
        if self.controller is not None:
            self.controller.refresh_library_view()
        else:
            self.playlist_view.grid_remove()
            self.main_area.destroy()
            self.main_area = MainContent(self, fg_color="#121212", corner_radius=0)
            self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
            logger.debug("MainContent refreshed")

    def show_songs(self, songs: list[Song]) -> None:
        """Render songs in place (no frame recreate)."""
        self.playlist_view.grid_remove()
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_area.set_header("All Musics")
        self.main_area.set_songs(songs)

    def show_playlists(self, playlists: list[Playlist]) -> None:
        """Render the playlist overview in the main cell."""
        self.main_area.grid_remove()
        self.playlist_view.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.playlist_view.set_playlists(playlists)

    def show_playlist_songs(self, playlist: Playlist, songs: list[Song]) -> None:
        """Render one playlist's songs with remove affordances."""
        self.playlist_view.grid_remove()
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_area.set_header(playlist.name)
        self.main_area.set_songs(songs, allow_remove=True)

    def show_track(self, song: Song) -> None:
        """Display the current track in the player bar."""
        self.player_bar.set_track(song)
        self.player_bar.set_playing(True)

    def set_progress(self, seconds: float, total: float) -> None:
        self.player_bar.set_progress(seconds, total)

    def set_playing(self, playing: bool) -> None:
        self.player_bar.set_playing(playing)

    def set_muted(self, muted: bool) -> None:
        self.player_bar.set_muted(muted)

    # -- Callbacks bound to the controller in set_controller() --

    def _on_close(self) -> None:
        if self.controller is not None:
            self.controller.shutdown()
        else:
            self.destroy()

    def _on_add_folder(self, folder_path: str) -> None:
        if self.controller is None:
            return
        # List refresh arrives via the library_changed event when new
        # songs are added; nothing to do here when the count is zero.
        self.controller.handle_add_folder(folder_path)

    def _on_select_song(self, song_id: int) -> None:
        if self.controller is not None:
            self.controller.handle_select_song(song_id)

    def _on_favorite_song(self, song_id: int) -> None:
        if self.controller is not None:
            self.controller.handle_toggle_favorite(song_id)
            self.controller.refresh_current_view()

    def _on_navigate(self, target: str) -> None:
        if self.controller is None:
            return
        if target == "playlists":
            self.controller.handle_show_playlists()
        else:
            self.controller.handle_show_music()

    def _on_create_playlist(self) -> None:
        if self.controller is None:
            return
        name = ask_text("New playlist", "Playlist name:")
        if name is not None:
            try:
                self.controller.handle_create_playlist(name)
            except ValueError as e:
                logger.warning(f"Playlist not created: {e}")

    def _on_rename_playlist(self, playlist_id: int) -> None:
        if self.controller is None:
            return
        current = self.controller.handle_get_playlist(playlist_id)
        name = ask_text(
            "Rename playlist", "New name:", initial=current.name if current else ""
        )
        if name is not None:
            try:
                self.controller.handle_rename_playlist(playlist_id, name)
            except ValueError as e:
                logger.warning(f"Playlist not renamed: {e}")

    def _on_delete_playlist(self, playlist_id: int) -> None:
        if self.controller is None:
            return
        current = self.controller.handle_get_playlist(playlist_id)
        label = current.name if current else "this playlist"
        if confirm(self, "Delete playlist", f"Delete '{label}'? Songs stay in your library."):
            self.controller.handle_delete_playlist(playlist_id)

    def _on_add_song_to_playlist(self, song_id: int) -> None:
        if self.controller is None:
            return
        song = self.controller.handle_get_song(song_id)
        playlists = self.controller.handle_list_playlists()
        if not playlists:
            name = ask_text("New playlist", "Name for the new playlist:")
            if name is None:
                return
            try:
                created = self.controller.handle_create_playlist(name)
            except ValueError as e:
                logger.warning(f"Playlist not created: {e}")
                return
            self.controller.handle_add_to_playlist(created.id, song_id)
            return
        choice = choose_playlist(
            self, playlists, song.title if song else f"song {song_id}"
        )
        if choice is None:
            return
        if choice == "new":
            name = ask_text("New playlist", "Name for the new playlist:")
            if name is None:
                return
            try:
                created = self.controller.handle_create_playlist(name)
            except ValueError as e:
                logger.warning(f"Playlist not created: {e}")
                return
            self.controller.handle_add_to_playlist(created.id, song_id)
        else:
            self.controller.handle_add_to_playlist(choice, song_id)

    def _on_remove_song_from_playlist(self, song_id: int) -> None:
        if self.controller is not None:
            current = self.controller.handle_get_current_playlist()
            if current is not None and current.id is not None:
                self.controller.handle_remove_from_playlist(current.id, song_id)

    def _on_seek_start(self, _event=None) -> None:
        if self.controller is not None:
            self.controller.seeking = True

    def _on_seek_end(self, _event=None) -> None:
        if self.controller is not None:
            self.controller.seeking = False

    def _on_seek_commit(self, seconds: float) -> None:
        if self.controller is not None:
            self.controller.seeking = True
            try:
                self.controller.handle_seek(seconds)
            finally:
                self.controller.seeking = False

    # METHOD FOR DESTROY self.main_area WHEN CHANGE VIEW (Music / Playlist / MusicPlaylist)
    def change_main_content(self, new_content: ctk.CTkFrame):
        """Change the main content area to a new frame"""
        self.main_area.destroy()
        self.main_area = new_content
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        logger.debug("MainContent changed")
