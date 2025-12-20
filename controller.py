from __future__ import annotations
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from model import CounterModel
    from view import View


class Controller:
    def __init__(self, model: CounterModel, view: View):
        self.model = model
        self.view = view
        logger.debug("Controller initialized with Model and View")

    def add(self):
        new_number = self.model.add()
        self.view.update_label(str(new_number))
        logger.debug(f"add_handler called, new number: {new_number}")

    def reset(self):
        """Handle resetting Number"""
        new_number = self.model.reset()
        self.view.update_label(str(new_number))
        logger.debug(f"reset_handler called, new number: {new_number}")
