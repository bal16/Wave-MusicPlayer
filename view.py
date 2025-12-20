from __future__ import annotations
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

from components.SplashScreen import SplashScreen
from components.Sidebar import Sidebar
from components.MainContent import MainContent
from components.PlayerBar import PlayerBar


if TYPE_CHECKING:
    from controller import Controller


class View(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.controller: Controller | None = None  # Placeholder

        self.withdraw()
        
        self.splash = SplashScreen(self)
        
        self.loading_step = 0
        self.run_loading()

        self.title("Wave Music Player")
        self.geometry("1100x650")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")
        
        logger.debug("View initialized")

    def set_controller(self, controller: Controller):
        """Accept object controller from outside"""
        self.controller = controller
        logger.debug("Controller set")

    def run_loading(self):
        """
        Simulasi memuat database/aset. 
        In a real app, this could be replaced with threading logic.
        """
        self.loading_step += 0.05 # Increment loading progress
        
        # Update progress bar in splash screen
        if hasattr(self, 'splash') and self.splash.winfo_exists():
            self.splash.progress.set(self.loading_step)

        if self.loading_step < 1.0:
            # Call this function again after 100ms (to keep animation smooth)
            self.after(100, self.run_loading)
        else:
            # LOADING SELESAI
            self.finish_loading()

    def finish_loading(self):
        if hasattr(self, 'splash'):
            self.splash.destroy()
        
        self.center_main_window()
        self.deiconify() # Show
        
        self.setup_ui()

    def center_main_window(self):
        w, h = 1000, 600
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (ws/2) - (w/2), (hs/2) - (h/2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')

    def setup_ui(self):
        # Grid Configuration (Root)
        # Row 0: Main Content (Expandable), Row 1: Player Bar (Fixed)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=0) 
        
        # Col 0: Sidebar (Fixed), Col 1: Content (Expandable)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # --- A. SIDEBAR ---
        self.sidebar = Sidebar(self, width=200, corner_radius=0, fg_color="#181818")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        

        # --- B. MAIN CONTENT ---
        self.main_area = MainContent(self, fg_color="#121212", corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        

        # --- C. BOTTOM PLAYER BAR ---
        self.player_bar = PlayerBar(self, height=90, corner_radius=0, fg_color="#0f0f0f")
        self.player_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
