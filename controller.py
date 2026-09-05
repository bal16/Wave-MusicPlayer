"""Legacy controller path — thin compat shim over the new controller.

Views talk to the controller through callbacks bound in View.set_controller()
(Sidebar.on_add_folder, MainContent.on_select/on_favorite). This wrapper
preserves the old MainController(model=engine, view=view) signature while
delegating all logic to LibraryService. No mainloop() in __init__ — call run().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from app.container import build_container
from controllers.main_controller import MainController as ThinController

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from view import View


class MainController(ThinController):
    def __init__(
        self,
        model: Engine | None = None,
        view: View | None = None,
        library: Any | None = None,
        player: Any | None = None,
        playlists: Any | None = None,
    ):
        if (
            library is not None
            and player is not None
            and playlists is not None
            and view is not None
        ):
            super().__init__(view=view, library=library, player=player, playlists=playlists)
            return
        # Legacy construction: build the default backend graph around the engine.
        container = build_container(view=None, engine=model)
        super().__init__(
            view=view,
            library=container.library,
            player=container.player,
            playlists=container.playlists,
        )
        logger.debug("Legacy MainController shim delegating to LibraryService")

    def run(self) -> None:
        logger.info("Application main loop has started")
        self.view.mainloop()

    def add_music_from_folder(self, folder_path: str) -> None:
        """Legacy entry point (kept for compat). Scan runs in background;
        completion arrives via the library_changed event."""
        self.handle_add_folder(folder_path)
