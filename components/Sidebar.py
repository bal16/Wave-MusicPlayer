import customtkinter as ctk
from config import COLOR_ACCENT, FONT_SANS_SERIF, ICON_LOGO

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.logo = ctk.CTkLabel(self, text="", image=ICON_LOGO, text_color=COLOR_ACCENT)
        self.logo.pack(pady=40, padx=20, anchor="w")
        
        MENUS = ["➕ Add", "🎵 Music", "📚 Playlist"]
        for menu in MENUS:
            btn = ctk.CTkButton(self, text=menu, 
                                fg_color="transparent", 
                                anchor="w", 
                                font=(FONT_SANS_SERIF, 16),
                                hover_color="#333333")
            btn.pack(fill="x", padx=20, pady=10)