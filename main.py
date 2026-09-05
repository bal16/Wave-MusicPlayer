from loguru import logger

from app.container import build_container
from controller import MainController
from infrastructure.db import init_db
from view import View


def main():
    logger.add("logs/app_history.log", rotation="1 MB", retention="10 days", level="DEBUG")

    logger.info("App Starting...")

    try:
        # DB setup lives in main(), not inside the View (splash stays visual only).
        init_db()

        view = View()
        container = build_container(view=None)
        controller = MainController(view=view, library=container.library)
        container.controller = controller

        view.set_controller(controller)
        controller.bind()
        # Initial list load once the mainloop is running.
        view.after(100, controller.refresh_library_view)
        controller.run()

    except Exception as e:
        logger.critical(f"App Crash! Error: {e}")
        raise e


if __name__ == "__main__":
    main()
