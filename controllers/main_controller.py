"""Thin MainController — Phase 0.

Holds services + view, never the Engine. No mainloop() in __init__
so the controller stays testable; call run() to enter the Tk loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from services.library_service import LibraryService

if TYPE_CHECKING:
    pass


class MainController:
    def __init__(self, view: Any, library: LibraryService):
        self.view = view
        self.library = library
        logger.debug("MainController initialized (thin, no mainloop side-effect)")

    def run(self) -> None:
        logger.info("Application main loop has started")
        self.view.mainloop()

    # -- Handlers wired to view callbacks (Phase 1/2 will bind them) --

    def handle_add_folder(self, folder_path: str) -> int:
        """Entry point for Sidebar.on_add_folder. Returns new-song count."""
        return self.library.scan_folder(folder_path)

    def handle_list_songs(self, query: str = "", favorites_only: bool = False):
        return self.library.list_songs(query=query, favorites_only=favorites_only)

    def handle_toggle_favorite(self, song_id: int) -> bool | None:
        return self.library.toggle_favorite(song_id)
