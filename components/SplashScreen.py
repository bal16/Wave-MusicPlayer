import customtkinter as ctk

from utils.icons import get_logo_box
from views.theme import theme


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.overrideredirect(True)

        width = 500
        height = 300
        self.config(background=theme.colors.surface)
        self.attributes("-topmost", True)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

        self.logo_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=0)
        self.logo_frame.pack(expand=True, fill="both")

        self.lbl_icon = ctk.CTkLabel(self.logo_frame, text="", image=get_logo_box())
        self.lbl_icon.pack(pady=(80, 10))

        self.progress = ctk.CTkProgressBar(
            self.logo_frame, width=200, height=4, progress_color=theme.colors.accent
        )
        self.progress.pack(pady=30)
        self.progress.set(0)
