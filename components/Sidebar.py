from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk
from customtkinter import filedialog
from loguru import logger

from config import COLOR_ACCENT, FONT_SANS_SERIF
from utils.icons import get_folder, get_logo, get_music, get_playlist

if TYPE_CHECKING:
    from view import View


class Sidebar(ctk.CTkFrame):
    master: View

    def __init__(self, master: View, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        # Callback bound by the View (never touch the controller directly).
        self.on_add_folder: Callable[[str], None] | None = None
        self.on_navigate: Callable[[str], None] | None = None
        self.logo = ctk.CTkLabel(self, text="", image=get_logo(), text_color=COLOR_ACCENT)
        self.logo.pack(pady=40, padx=20, anchor="w")

        self.get_button("Add", command=self.open_add_music_window, image=get_folder())
        self.get_button("Music", command=lambda: self._emit_navigate("music"), image=get_music())
        self.get_button(
            "Playlist",
            command=lambda: self._emit_navigate("playlists"),
            image=get_playlist(),
        )

    def get_button(self, menu_name: str, command=lambda: None, image=None) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            self,
            text=menu_name,
            image=image,
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

    def _emit_navigate(self, target: str) -> None:
        if self.on_navigate is not None:
            self.on_navigate(target)
