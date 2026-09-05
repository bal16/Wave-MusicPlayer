"""Thin MainController — holds services + view, never the Engine.

No mainloop() in __init__ so the controller stays testable; call run()
to enter the Tk loop. Player callbacks arrive on audio threads and are
always marshalled to the UI thread via view.after().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from services.library_service import LibraryService
from services.player_service import (
    STATE_CHANGED_EVENT,
    TRACK_CHANGED_EVENT,
    PlayerService,
)

if TYPE_CHECKING:
    pass

TICK_MS = 1000


class MainController:
    def __init__(self, view: Any, library: LibraryService, player: PlayerService):
        self.view = view
        self.library = library
        self.player = player
        # True while the user drags the seek slider (ticker holds off).
        self.seeking = False
        self._ticker_running = False
        player.subscribe(TRACK_CHANGED_EVENT, self._on_track_changed)
        player.subscribe(STATE_CHANGED_EVENT, self._on_player_state)
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

    def _on_library_changed(self, **_kwargs) -> None:
        # The scan may run on a worker thread in later phases, so always
        # marshal the UI update through after() instead of touching
        # widgets directly.
        self.view.after(0, self.refresh_library_view)

    # -- Library handlers --

    def handle_add_folder(self, folder_path: str) -> int:
        """Entry point for Sidebar.on_add_folder. Returns new-song count."""
        return self.library.scan_folder(folder_path)

    def handle_list_songs(self, query: str = "", favorites_only: bool = False):
        return self.library.list_songs(query=query, favorites_only=favorites_only)

    def handle_toggle_favorite(self, song_id: int) -> bool | None:
        return self.library.toggle_favorite(song_id)

    # -- Playback handlers (Fase 2, F3 Play) --

    def handle_select_song(self, song_id: int) -> None:
        """Queue the full library in shown order, start at the clicked song."""
        songs = self.library.list_songs()
        index = next((i for i, s in enumerate(songs) if s.id == song_id), 0)
        song = self.player.play_queue(songs, index)
        if song is not None:
            self.view.show_track(song)
        self._ensure_ticker()

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
