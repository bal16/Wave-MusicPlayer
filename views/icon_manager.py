import os
import sys

import customtkinter as ctk
from PIL import Image


def resource_path(relative: str) -> str:
    """Resolve asset path both in source runs and PyInstaller bundles."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)


class IconManager:
    def __init__(self, icon_path: str | None = None):
        self.path = icon_path or resource_path(os.path.join("assets", "icons"))

    def load(self, name, size=(20, 20), with_dark=False):
        """
        helper for searching and loading icons from the assets/icons folder \n
        :param name: name of the icon file without _light or _dark suffix and file extension \n
        :param size: size of the icon as a tuple (width, height)
        :param with_dark: has dark variant? default: `false`
        :type name: str
        :type size: tuple[int, int]
        :type with_dark: bool
        :
        """
        if with_dark:
            return ctk.CTkImage(
                light_image=Image.open(os.path.join(self.path, f"{name}_light.png")),
                dark_image=Image.open(os.path.join(self.path, f"{name}_dark.png")),
                size=size,
            )

        return ctk.CTkImage(
            light_image=Image.open(os.path.join(self.path, f"{name}.png")),
            dark_image=Image.open(os.path.join(self.path, f"{name}.png")),
            size=size,
        )


icons = IconManager()
