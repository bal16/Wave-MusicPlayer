"""Legacy controller path — thin compat shim over the new controller.

Phase 0 keeps Sidebar calling master.controller.add_music_from_folder(),
so this wrapper preserves that method name and the old
MainController(model=engine, view=view) signature while delegating all
logic to LibraryService. No mainloop() in __init__ — call run().
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
    ):
        if library is not None and view is not None:
            super().__init__(view=view, library=library)
            return
        # Legacy construction: build the default backend graph around the engine.
        container = build_container(view=None, engine=model)
        super().__init__(view=view, library=container.library)
        logger.debug("Legacy MainController shim delegating to LibraryService")

    def run(self) -> None:
        logger.info("Application main loop has started")
        self.view.mainloop()

    def add_music_from_folder(self, folder_path: str) -> int:
        """Legacy entry point used by Sidebar. Returns new-song count."""
        return self.handle_add_folder(folder_path)
