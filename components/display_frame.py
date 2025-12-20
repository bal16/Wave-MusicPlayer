import customtkinter as ctk
from loguru import logger


class DisplayFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.label_title = ctk.CTkLabel(
            self, text="Current Counter", font=("Arial", 12)
        )
        self.label_title.pack(pady=(10, 0))

        self.label_value = ctk.CTkLabel(self, text="0", font=("Arial", 40, "bold"))
        self.label_value.pack(pady=10)

    def set_value(self, value):
        """A special method for changing label text from outside"""
        logger.debug(f"DisplayFrame: Setting label value to {value}")
        self.label_value.configure(text=str(value))
