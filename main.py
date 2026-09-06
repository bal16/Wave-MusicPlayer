import os
import sys

from loguru import logger

from app.container import build_container
from controllers.main_controller import MainController
from infrastructure.db import init_db
from view import View


def main():
    # stderr honors LOGURU_LEVEL (dev=DEBUG, start=INFO); the file log
    # always keeps DEBUG for post-mortem diagnosis.
    logger.remove()
    logger.add(sys.stderr, level=os.getenv("LOGURU_LEVEL", "INFO"))
    logger.add("logs/app_history.log", rotation="1 MB", retention="10 days", level="DEBUG")

    logger.info("App Starting...")

    try:
        # DB setup lives in main(), not inside the View (splash stays visual only).
        init_db()

        view = View()
        container = build_container(view=None)
        controller = MainController(
            view=view,
            library=container.library,
            player=container.player,
            playlists=container.playlists,
        )
        container.controller = controller

        view.set_controller(controller)
        controller.bind()
        # Initial list load once the mainloop is running.
        view.after(100, controller.refresh_library_view)
        controller.run()

    except Exception:
        logger.exception("App crashed")
        raise


if __name__ == "__main__":
    main()
