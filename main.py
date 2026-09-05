from loguru import logger

from controller import MainController
from models.database import engine
from view import View


def main():
    logger.add("logs/app_history.log", rotation="1 MB", retention="10 days", level="DEBUG")

    logger.info("App Starting...")

    try:
        db_engine = engine
        view = View()
        controller = MainController(model=db_engine, view=view)

        view.set_controller(controller)

    except Exception as e:
        logger.critical(f"App Crash! Error: {e}")
        raise e


if __name__ == "__main__":
    main()
