import customtkinter as ctk

from config import COLOR_BG, FONT_SANS_SERIF, ICON_PLAY_BUTTON


class PlayerBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(1, weight=1)  # Tengah melar

        # Frame Album Art & Title (Kiri)
        self.album_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.album_frame.grid(row=0, column=0)

        # Album Art (Kiri)
        self.lbl_art = ctk.CTkLabel(
            self.album_frame, text="[IMG]", width=100, height=100, fg_color="#333"
        )
        self.lbl_art.grid(row=0, column=0, padx=20, pady=10)

        # frame Judul & Artist
        self.detail_frame = ctk.CTkFrame(self.album_frame, fg_color="transparent")
        self.detail_frame.grid(row=0, column=1, pady=20)

        self.lbl_song_title = ctk.CTkLabel(
            self.detail_frame, text="Song Title", font=(FONT_SANS_SERIF, 14)
        )
        self.lbl_song_title.pack(pady=0, anchor="w")
        self.lbl_song_artist = ctk.CTkLabel(
            self.detail_frame, text="Artist Name", text_color="grey"
        )
        self.lbl_song_artist.pack(pady=0, anchor="w")

        # Button Like & Dislike
        self.like_button = ctk.CTkButton(
            self.album_frame,
            text="♡",
            width=30,
            fg_color="transparent",
            text_color="grey",
            border_width=0,
        )
        self.like_button.grid(row=0, column=2, padx=10)

        # Controls (Tengah)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1)

        # Slider Progress Frame
        self.progress_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.progress_frame.pack(pady=5)

        self.lbl_current_time = ctk.CTkLabel(self.progress_frame, text="0:00")
        self.lbl_current_time.grid(row=0, column=0, pady=5, padx=5)

        # Slider Progress
        self.slider = ctk.CTkSlider(
            self.progress_frame, width=400, progress_color="white", button_color="white"
        )
        self.slider.grid(row=0, column=1, pady=5)

        self.lbl_total_time = ctk.CTkLabel(self.progress_frame, text="3:45")
        self.lbl_total_time.grid(row=0, column=2, pady=5, padx=5)

        # Buttons (Prev, Play, Next)
        # Use a dedicated row frame to avoid mixing pack/grid
        self.buttons_row = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.buttons_row.pack(pady=5)

        self.btn_prev = ctk.CTkButton(
            self.buttons_row, text="<<", width=40, fg_color="transparent", border_width=1
        )
        self.btn_prev.pack(side="left", padx=5)
        self.btn_play = ctk.CTkButton(
            self.buttons_row,
            text="",
            width=40,
            fg_color="transparent",
            border_width=0,
            image=ICON_PLAY_BUTTON,
            hover_color=COLOR_BG,
        )
        self.btn_play.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(
            self.buttons_row, text=">>", width=40, fg_color="transparent", border_width=1
        )
        self.btn_next.pack(side="left", padx=5)

        # Frame Volume Slider (Kanan)
        self.volume_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.volume_frame.grid(row=0, column=2)

        # loop button
        self.btn_loop = ctk.CTkButton(
            self.volume_frame, text="🔁", width=40, fg_color="transparent", border_width=0
        )
        self.btn_loop.grid(row=0, column=0, pady=20, padx=0)

        # volume button
        self.btn_volume = ctk.CTkButton(
            self.volume_frame, text="🔊", width=40, fg_color="transparent", border_width=0
        )
        self.btn_volume.grid(row=0, column=1, pady=20, padx=0)

        self.volume_slider = ctk.CTkSlider(
            self.volume_frame, width=100, progress_color="white", button_color="white"
        )
        self.volume_slider.grid(row=0, column=2, pady=20, padx=0)

        self.btn_volume = ctk.CTkButton(
            self.volume_frame, text="🔊", width=40, fg_color="transparent", border_width=0
        )
        self.btn_volume.grid(row=0, column=3, pady=20, padx=0)
