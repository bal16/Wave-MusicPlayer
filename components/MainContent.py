import customtkinter as ctk
from config import FONT_SANS_SERIF

class MainContent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Header text
        self.lbl_header = ctk.CTkLabel(self, text="Daftar Musik", font=(FONT_SANS_SERIF, 20, "bold"))
        self.lbl_header.pack(pady=30, padx=40, anchor="w")

        # Scrollable Song List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20)

        # row headings
        headings = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=30)
        headings.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(headings, text="#", width=30, text_color="grey").pack(side="left", padx=10)
        ctk.CTkLabel(headings, text="Title", font=(FONT_SANS_SERIF, 14, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(headings, text="Duration", width=50).pack(side="right", padx=20)
        
        # Dummy Songs (Visualisasi List Gambar 2)
        for i in range(1, 10):
            self.create_song_row(i, f"Lagu Demo {i}", "Artist Name", "03:45")

    def create_song_row(self, idx, title, artist, duration):
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=50)
        row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row, text=str(idx), width=30, text_color="grey").pack(side="left", padx=10)
        ctk.CTkLabel(row, text=title, font=(FONT_SANS_SERIF, 14, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row, text=artist, text_color="grey").pack(side="left")
        ctk.CTkLabel(row, text=duration, width=50).pack(side="right", padx=20)
        
        # Icon Hati
        ctk.CTkButton(row, text="♡", width=30, fg_color="transparent", text_color="grey").pack(side="right")
        ctk.CTkButton(row, text="D", width=30, fg_color="transparent", text_color="grey").pack(side="right")