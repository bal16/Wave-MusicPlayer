"""Thin MainController — holds services + view, never the Engine.

No mainloop() in __init__ so the controller stays testable; call run()
to enter the Tk loop. Player callbacks arrive on audio threads and are
always marshalled to the UI thread via view.after().
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from loguru import logger

from services.library_service import LibraryService
from services.player_service import (
    STATE_CHANGED_EVENT,
    TRACK_CHANGED_EVENT,
    PlayerService,
)
from services.playlist_service import PlaylistService

if TYPE_CHECKING:
    pass

TICK_MS = 1000

# Controller navigation state (mirrors the main-area view).
VIEW_LIBRARY = "library"
VIEW_PLAYLISTS = "playlists"
VIEW_PLAYLIST_DETAIL = "playlist"


class MainController:
    def __init__(
        self,
        view: Any,
        library: LibraryService,
        player: PlayerService,
        playlists: PlaylistService,
    ):
        self.view = view
        self.library = library
        self.player = player
        self.playlists = playlists
        self.current_view = VIEW_LIBRARY
        self.current_playlist_id: int | None = None
        # True while the user drags the seek slider (ticker holds off).
        self.seeking = False
        self._ticker_running = False
        self._scanning = False
        player.subscribe(TRACK_CHANGED_EVENT, self._on_track_changed)
        player.subscribe(STATE_CHANGED_EVENT, self._on_player_state)
        playlists.subscribe(self._on_playlist_changed)
        logger.debug("MainController initialized (thin, no mainloop side-effect)")

    def run(self) -> None:
        logger.info("Application main loop has started")
        self.view.mainloop()

    def shutdown(self) -> None:
        """Stop playback, release audio, then destroy the window.

        Bound to WM_DELETE_WINDOW so no device is left open for
        interpreter-teardown __del__ (which deadlocks).
        """
        self._ticker_running = False
        try:
            self.player.shutdown()
        except Exception as e:
            logger.error(f"Error during player shutdown: {e}")
        finally:
            self.view.destroy()

    def bind(self) -> None:
        """Subscribe to backend events. Call once after set_controller()."""
        self.library.subscribe(self._on_library_changed)

    def refresh_library_view(self) -> None:
        """Re-query songs and push them to the view (UI thread only)."""
        songs = self.library.list_songs()
        self.view.show_songs(songs)

    def refresh_current_view(self) -> None:
        """Re-render whichever main-area view is active (UI thread only)."""
        if self.current_view == VIEW_PLAYLISTS:
            self.view.show_playlists(self.playlists.list_playlists())
        elif self.current_view == VIEW_PLAYLIST_DETAIL:
            self._show_playlist_detail(self.current_playlist_id)
        else:
            self.refresh_library_view()

    def _on_playlist_changed(self, **_kwargs) -> None:
        self.view.after(0, self.refresh_current_view)

    def _on_library_changed(self, **_kwargs) -> None:
        # The scan may run on a worker thread in later phases, so always
        # marshal the UI update through after() instead of touching
        # widgets directly.
        self.view.after(0, self.refresh_current_view)

    # -- Library handlers --

    def handle_add_folder(self, folder_path: str) -> None:
        """Entry point for Sidebar.on_add_folder. Scans on a worker thread.

        A second scan while one runs is ignored. Completion arrives via
        the library_changed event; failures are logged and shown.
        """
        if self._scanning:
            logger.warning("Scan already running — ignoring new folder")
            return
        if not folder_path:
            return
        self._scanning = True
        self.view.show_scan_started()
        thread = threading.Thread(target=self._scan_in_background, args=(folder_path,), daemon=True)
        thread.start()

    def _scan_in_background(self, folder_path: str) -> None:
        try:
            self.library.scan_folder(folder_path, progress=self._report_scan_progress)
        except Exception as e:
            logger.error(f"Background scan failed: {e}")
            self.view.after(0, self.view.show_scan_failed, str(e))
        finally:
            self._scanning = False
            # Scheduled after the refresh (publish happens before this),
            # so the dialog closes on completion even with zero new songs.
            self.view.after(0, self.view.show_scan_finished)

    def _report_scan_progress(self, done: int, total: int) -> None:
        # Runs on the worker thread — marshal to the UI thread.
        self.view.after(0, self.view.show_scan_progress, done, total)

    def handle_list_songs(self, query: str = "", favorites_only: bool = False):
        return self.library.list_songs(query=query, favorites_only=favorites_only)

    def handle_toggle_favorite(self, song_id: int) -> bool | None:
        return self.library.toggle_favorite(song_id)

    # -- Playback handlers (Fase 2, F3 Play) --

    def handle_select_song(self, song_id: int) -> None:
        """Queue the current view's songs, start at the clicked song."""
        songs = self._current_songs()
        index = next((i for i, s in enumerate(songs) if s.id == song_id), 0)
        song = self.player.play_queue(songs, index)
        if song is not None:
            self.view.show_track(song)
        self._ensure_ticker()

    def _current_songs(self) -> list:
        """Songs backing queue/next/prev for the active view."""
        if self.current_view == VIEW_PLAYLIST_DETAIL and self.current_playlist_id is not None:
            return self.playlists.songs_in_playlist(self.current_playlist_id)
        return self.library.list_songs()

    def handle_play_pause(self) -> None:
        playing = self.player.play_pause()
        self.view.set_playing(playing)
        self._ensure_ticker()

    def handle_next(self) -> None:
        song = self.player.next()
        if song is not None:
            self.view.show_track(song)
        self._ensure_ticker()

    def handle_prev(self) -> None:
        song = self.player.prev()
        if song is not None:
            self.view.show_track(song)
        self._ensure_ticker()

    def handle_seek(self, seconds: float) -> None:
        pos = self.player.seek(seconds)
        self.view.set_progress(pos, self.player.get_duration())

    def handle_volume(self, level: float) -> None:
        self.player.set_volume(level)

    def handle_mute(self) -> None:
        muted = self.player.toggle_mute()
        self.view.set_muted(muted)

    def handle_toggle_current_favorite(self) -> None:
        song = self.player.current
        if song is None or song.id is None:
            return
        self.library.toggle_favorite(song.id)
        self.refresh_library_view()
        updated = self.library.get_song(song.id)
        if updated is not None:
            self.view.show_track(updated)

    # -- Playlist handlers (Fase 3, F4 Playlist) --

    def handle_show_music(self) -> None:
        self.current_view = VIEW_LIBRARY
        self.current_playlist_id = None
        self.refresh_library_view()

    def handle_show_playlists(self) -> None:
        self.current_view = VIEW_PLAYLISTS
        self.current_playlist_id = None
        self.view.show_playlists(self.playlists.list_playlists())

    def handle_select_playlist(self, playlist_id: int) -> None:
        self.current_view = VIEW_PLAYLIST_DETAIL
        self.current_playlist_id = playlist_id
        self._show_playlist_detail(playlist_id)

    def _show_playlist_detail(self, playlist_id: int | None) -> None:
        playlist = self.playlists.get_playlist(playlist_id) if playlist_id is not None else None
        if playlist is None:
            self.handle_show_playlists()
            return
        songs = self.playlists.songs_in_playlist(playlist_id)
        self.view.show_playlist_songs(playlist, songs)

    def handle_create_playlist(self, name: str, description: str = ""):
        return self.playlists.create_playlist(name, description)

    def handle_rename_playlist(self, playlist_id: int, name: str):
        return self.playlists.rename_playlist(playlist_id, name)

    def handle_delete_playlist(self, playlist_id: int) -> bool:
        deleted = self.playlists.delete_playlist(playlist_id)
        if deleted and self.current_playlist_id == playlist_id:
            self.handle_show_playlists()
        return deleted

    def handle_add_to_playlist(self, playlist_id: int, song_id: int) -> bool:
        return self.playlists.add_song(playlist_id, song_id)

    def handle_remove_from_playlist(self, playlist_id: int, song_id: int) -> bool:
        removed = self.playlists.remove_song(playlist_id, song_id)
        if removed:
            self.refresh_current_view()
        return removed

    def handle_list_playlists(self) -> list:
        return self.playlists.list_playlists()

    def handle_get_playlist(self, playlist_id: int):
        return self.playlists.get_playlist(playlist_id)

    def handle_get_current_playlist(self):
        """Playlist backing the detail view, or None."""
        if self.current_playlist_id is None:
            return None
        return self.playlists.get_playlist(self.current_playlist_id)

    def handle_get_song(self, song_id: int):
        return self.library.get_song(song_id)

    def handle_get_cover(self, song_id: int) -> bytes | None:
        return self.library.get_cover(song_id)

    # -- Player events (audio threads) --

    def _on_track_changed(self, song=None, **_kwargs) -> None:
        self.view.after(0, self._show_track_safe, song)

    def _show_track_safe(self, song) -> None:
        if song is not None:
            self.view.show_track(song)

    def _on_player_state(self, playing: bool = False, **_kwargs) -> None:
        self.view.after(0, self.view.set_playing, playing)

    # -- Progress ticker (after loop, never a UI thread) --

    def _ensure_ticker(self) -> None:
        if self._ticker_running:
            return
        self._ticker_running = True
        self.view.after(TICK_MS, self._tick)

    def _tick(self) -> None:
        if self.player.current is None or not self.player.is_playing:
            self._ticker_running = False
            return
        if not self.seeking:
            self.view.set_progress(self.player.get_pos(), self.player.get_duration())
        self.view.after(TICK_MS, self._tick)
