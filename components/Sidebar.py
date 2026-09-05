from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import customtkinter as ctk
from customtkinter import filedialog
from loguru import logger

from config import COLOR_ACCENT, FONT_SANS_SERIF, ICON_LOGO

if TYPE_CHECKING:
    from view import View


class Sidebar(ctk.CTkFrame):
    master: View

    def __init__(self, master: View, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        # Callback bound by the View (never touch the controller directly).
        self.on_add_folder: Callable[[str], None] | None = None
        self.logo = ctk.CTkLabel(self, text="", image=ICON_LOGO, text_color=COLOR_ACCENT)
        self.logo.pack(pady=40, padx=20, anchor="w")

        i = 0
        MENUS = ["➕ Add", "🎵 Music", "📚 Playlist"]
        for menu in MENUS:
            if i == 0:
                self.get_button(menu, command=self.open_add_music_window)
            else:
                self.get_button(menu)
            i += 1

    def get_button(self, menu_name: str, command=lambda: None) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            self,
            text=menu_name,
            fg_color="transparent",
            anchor="w",
            font=(FONT_SANS_SERIF, 16),
            hover_color="#333333",
            command=command,
        )
        btn.pack(fill="x", padx=20, pady=10)

    def open_add_music_window(self):
        """Ask for a folder, then hand it to the bound callback."""
        dir = filedialog.askdirectory()
        logger.debug(f"Selected directory: {dir}")

        if not dir:
            logger.debug("Add folder cancelled — nothing to do")
            return
        if self.on_add_folder is not None:
            self.on_add_folder(dir)
