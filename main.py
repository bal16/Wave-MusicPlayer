from loguru import logger

from model import CounterModel
from view import View
from controller import Controller


def main():
    logger.add(
        "logs/app_history.log", rotation="1 MB", retention="10 days", level="DEBUG"
    )

    logger.info("App Starting...")

    try:
        model = CounterModel()
        view = View()
        controller = Controller(model, view)

        view.set_controller(controller)
        view.mainloop()
    except Exception as e:
        logger.critical(f"App Crash! Error: {e}")
        raise e


if __name__ == "__main__":
    main()
