from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

from utils.icons import (
    get_heart_filled,
    get_heart_outline,
    get_muted,
    get_next_button,
    get_notmuted,
    get_now_playing,
    get_pause_button,
    get_play_button,
    get_prev_button,
    get_repeat,
)
from views.theme import format_duration, theme, truncate_text

if TYPE_CHECKING:
    from domain.entities import Song


class PlayerBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Callbacks bound by the View (never import the controller here).
        self.on_play: Callable[[], None] | None = None
        self.on_next: Callable[[], None] | None = None
        self.on_prev: Callable[[], None] | None = None
        self.on_seek: Callable[[float], None] | None = None
        self.on_volume: Callable[[float], None] | None = None
        self.on_mute: Callable[[], None] | None = None
        self.on_favorite: Callable[[], None] | None = None

        # Total duration of the current track (for slider mapping).
        self._total = 0.0
        self._dragging = False
        # Decoded covers by song id (thumbnail CTkImages).
        self._cover_cache: dict[int, ctk.CTkImage] = {}

        # Top-level grid: fixed sides, fluid center.
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Left: album art + title
        self.album_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.album_frame.grid(row=0, column=0, padx=(10, 0), sticky="ns")

        # Album Art (placeholder until cover support lands post-MVP).
        # 60px keeps the bar at the 90px theme height.
        self.lbl_art = ctk.CTkLabel(
            self.album_frame,
            text="[IMG]",
            width=60,
            height=60,
            fg_color=theme.colors.hover,
        )
        self.lbl_art.grid(row=0, column=0, padx=10, pady=10)

        # Title & artist frame (fixed width so track changes never shift
        # the layout; long text is truncated with an ellipsis in set_track).
        self.detail_frame = ctk.CTkFrame(self.album_frame, fg_color="transparent")
        self.detail_frame.grid(row=0, column=1, pady=20)

        self.lbl_song_title = ctk.CTkLabel(
            self.detail_frame, text="Song Title", font=theme.fonts.body, width=200, anchor="w"
        )
        self.lbl_song_title.pack(pady=0, anchor="w")
        self.lbl_song_artist = ctk.CTkLabel(
            self.detail_frame,
            text="Artist Name",
            text_color=theme.colors.text_muted,
            width=200,
            anchor="w",
        )
        self.lbl_song_artist.pack(pady=0, anchor="w")

        # Favorite button for the current track (40px to match transport keys).
        self.like_button = ctk.CTkButton(
            self.album_frame,
            text="",
            image=get_heart_outline(22),
            width=40,
            fg_color="transparent",
            hover_color=theme.colors.surface,
            text_color=theme.colors.text_muted,
            border_width=0,
            command=self._emit_favorite,
        )
        self.like_button.grid(row=0, column=2, padx=10)

        # Center: controls (stretches with the window)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, sticky="nsew")

        # Slider progress frame: fixed time labels, fluid slider.
        # Tight stack below (gap 4 to the transport keys); the top pad
        # balances the leftover bar height so the block stays centered.
        self.progress_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(10, 2), padx=10)
        self.progress_frame.grid_columnconfigure(0, weight=0)
        self.progress_frame.grid_columnconfigure(1, weight=1)
        self.progress_frame.grid_columnconfigure(2, weight=0)

        self.lbl_current_time = ctk.CTkLabel(
            self.progress_frame, text="0:00", width=44, anchor="center"
        )
        self.lbl_current_time.grid(row=0, column=0, pady=2, padx=5)

        # Progress slider (0.0 - 1.0 fraction of the track, fluid width)
        self.slider = ctk.CTkSlider(
            self.progress_frame,
            from_=0,
            to=1,
            progress_color=theme.colors.progress_fill,
            button_color=theme.colors.progress_fill,
            command=self._on_slider_move,
        )
        self.slider.set(0)
        self.slider.grid(row=0, column=1, pady=2, sticky="ew")
        self.slider.bind("<ButtonPress-1>", self._on_slider_press)
        self.slider.bind("<ButtonRelease-1>", self._on_slider_release)

        self.lbl_total_time = ctk.CTkLabel(
            self.progress_frame, text="0:00", width=44, anchor="center"
        )
        self.lbl_total_time.grid(row=0, column=2, pady=2, padx=5)

        # Buttons (Prev, Play, Next)
        # Use a dedicated row frame to avoid mixing pack/grid
        self.buttons_row = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.buttons_row.pack(pady=2)

        self.btn_prev = ctk.CTkButton(
            self.buttons_row,
            text="",
            image=get_prev_button(),
            width=40,
            fg_color="transparent",
            border_width=0,
            hover_color=theme.colors.surface,
            command=self._emit_prev,
        )
        self.btn_prev.pack(side="left", padx=5)
        self.btn_play = ctk.CTkButton(
            self.buttons_row,
            text="",
            width=40,
            fg_color="transparent",
            border_width=0,
            image=get_play_button(),
            hover_color=theme.colors.surface,
            command=self._emit_play,
        )
        self.btn_play.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(
            self.buttons_row,
            text="",
            image=get_next_button(),
            width=40,
            fg_color="transparent",
            border_width=0,
            hover_color=theme.colors.surface,
            command=self._emit_next,
        )
        self.btn_next.pack(side="left", padx=5)

        # Right: volume frame
        self.volume_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.volume_frame.grid(row=0, column=2, padx=(0, 20), sticky="ns")

        # Loop button (non-functional until repeat is decided post-MVP).
        self.btn_loop = ctk.CTkButton(
            self.volume_frame,
            text="",
            image=get_repeat(),
            width=40,
            fg_color="transparent",
            border_width=0,
            state="disabled",
        )
        self.btn_loop.grid(row=0, column=0, pady=20, padx=0)

        # Mute toggle button
        self.btn_volume = ctk.CTkButton(
            self.volume_frame,
            text="",
            image=get_notmuted(),
            width=40,
            fg_color="transparent",
            border_width=0,
            command=self._emit_mute,
        )
        self.btn_volume.grid(row=0, column=1, pady=20, padx=0)

        self.volume_slider = ctk.CTkSlider(
            self.volume_frame,
            width=100,
            from_=0,
            to=1,
            progress_color=theme.colors.progress_fill,
            button_color=theme.colors.progress_fill,
            command=self._on_volume_move,
        )
        self.volume_slider.set(1)
        self.volume_slider.grid(row=0, column=2, pady=20, padx=0)

        # Initial art: bundled fallback until the first track plays.
        self.set_cover(None, None)

    # -- Display API called by the View --

    def set_track(self, song: Song) -> None:
        """Show track metadata and reset progress."""
        self.lbl_song_title.configure(text=truncate_text(song.title))
        self.lbl_song_artist.configure(text=truncate_text(song.artist))
        self._total = float(song.duration or 0.0)
        self.lbl_total_time.configure(text=format_duration(self._total))
        self.set_favorite(song.is_favorite)
        self.set_progress(0.0, self._total)

    def set_progress(self, seconds: float, total: float) -> None:
        """Update time labels and slider (skipped while dragging)."""
        self._total = total
        self.lbl_current_time.configure(text=format_duration(seconds))
        self.lbl_total_time.configure(text=format_duration(total))
        if not self._dragging and total > 0:
            self.slider.set(max(0.0, min(1.0, seconds / total)))

    def set_playing(self, playing: bool) -> None:
        """Swap the play/pause icon."""
        self.btn_play.configure(image=get_pause_button() if playing else get_play_button())

    def set_muted(self, muted: bool) -> None:
        self.btn_volume.configure(image=get_muted() if muted else get_notmuted())

    def set_favorite(self, is_favorite: bool) -> None:
        icon = get_heart_filled(22) if is_favorite else get_heart_outline(22)
        self.like_button.configure(image=icon)

    def set_cover(self, song_id: int | None, data: bytes | None) -> None:
        """Show embedded cover art, bundled fallback, or text placeholder.

        Embedded bytes are thumbnailed and cached per song id; without
        bytes the bundled now_playing asset is used. Plain text remains
        only if the asset itself fails to load.
        """
        if data is not None and song_id is not None:
            image = self._cover_cache.get(song_id)
            if image is None:
                image = self._decode_cover(data)
                if image is not None:
                    self._cover_cache[song_id] = image
            if image is not None:
                self.lbl_art.configure(image=image, text="")
                return
        try:
            self.lbl_art.configure(image=get_now_playing(), text="")
        except Exception:
            self.lbl_art.configure(image=None, text="[IMG]")

    @staticmethod
    def _decode_cover(data: bytes) -> ctk.CTkImage | None:
        import io

        from PIL import Image

        try:
            picture = Image.open(io.BytesIO(data)).convert("RGB")
            picture.thumbnail((120, 120))
            return ctk.CTkImage(light_image=picture, dark_image=picture, size=(60, 60))
        except Exception:
            logger.debug("Cover bytes could not be decoded — using fallback art")
            return None

    # -- Slider interaction --

    def _on_slider_press(self, _event) -> None:
        self._dragging = True

    def _on_slider_release(self, _event) -> None:
        self._dragging = False
        if self.on_seek is not None and self._total > 0:
            self.on_seek(self.slider.get() * self._total)

    def _on_slider_move(self, _value: float) -> None:
        # Live feedback while dragging; the commit happens on release.
        if self._dragging:
            self.lbl_current_time.configure(text=format_duration(self.slider.get() * self._total))

    def _on_volume_move(self, value: float) -> None:
        if self.on_volume is not None:
            self.on_volume(value)

    # -- Emitters --

    def _emit_play(self) -> None:
        if self.on_play is not None:
            self.on_play()

    def _emit_next(self) -> None:
        if self.on_next is not None:
            self.on_next()

    def _emit_prev(self) -> None:
        if self.on_prev is not None:
            self.on_prev()

    def _emit_mute(self) -> None:
        if self.on_mute is not None:
            self.on_mute()

    def _emit_favorite(self) -> None:
        if self.on_favorite is not None:
            self.on_favorite()
