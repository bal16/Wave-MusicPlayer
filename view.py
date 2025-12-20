from __future__ import annotations
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

# from interface.controller import IController

# from components import ActionFrame, DisplayFrame
from components.display_frame import DisplayFrame
from components.action_frame import ActionFrame

if TYPE_CHECKING:
    from controller import Controller


class View(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MVC APP")
        self.geometry("400x200")

        self.controller: Controller | None = None  # Placeholder

        self.display_frame = DisplayFrame(master=self)
        self.display_frame.pack(pady=20, fill="x", padx=20)

        self.action_frame = ActionFrame(
            master=self,
            on_add_callback=self.on_add_click,
            on_reset_callback=self.on_reset_click,
        )
        self.action_frame.pack(pady=20)

        logger.debug("View initialized")

    def set_controller(self, controller: Controller):
        """Accept object controller from outside"""
        self.controller = controller
        logger.debug("Controller set")

    def on_add_click(self):
        """Report to controller if the button is clicked"""
        if self.controller:
            self.controller.add()
            logger.debug("Add button clicked")

    def on_reset_click(self):
        if self.controller:
            self.controller.reset()
            logger.debug("Reset button clicked")

    def update_label(self, text: str):
        """Passive function to be called by the controller"""
        # Update the DisplayFrame label instead of a non-existent self.label
        self.display_frame.set_value(text)
        logger.debug(f"Label updated to: {text}")
