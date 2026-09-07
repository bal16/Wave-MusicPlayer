"""SongRow — one song row (<SongRow /> in React terms).

Owns everything about a single row: grid columns shared with the list
header, title/artist/duration labels, playlist + favorite buttons,
hover feedback, click-to-play, explicit wheel bindings, tooltips, and
the now-playing highlight. MainContent only manages the collection
(header, registry, chunked render, overflow).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from views.icons import get_heart_filled, get_heart_outline
from views.theme import format_duration, theme
from views.widgets.scroll_helper import enable_wheel_scroll
from views.widgets.tooltip import Tooltip

if TYPE_CHECKING:
    from domain.entities import Song

HEART_ON = "♥"
HEART_OFF = "♡"

# Grid columns shared by the sticky header and every row so they align:
# 0:# | 1:info (title stacked over artist) | 2:playlist action | 3:favorite | 4:duration
_FIXED_COLS = {0: 34, 2: 40, 3: 40, 4: 56}
_WEIGHTED_COLS = {1: 1}


def configure_columns(frame) -> None:
    """Apply the shared song-list column spec to a header or row frame."""
    for col, minsize in _FIXED_COLS.items():
        frame.grid_columnconfigure(col, weight=0, minsize=minsize)
    for col, weight in _WEIGHTED_COLS.items():
        frame.grid_columnconfigure(col, weight=weight)


def format_song_row(song: Song) -> dict:
    """Pure mapping from Song to row display values (Tk-free, unit-tested)."""
    return {
        "title": song.title,
        "artist": song.artist,
        "duration": format_duration(song.duration),
        "favorite_mark": HEART_ON if song.is_favorite else HEART_OFF,
    }


def favorite_icon(is_favorite: bool):
    """Heart asset for love/like/favorite state (icon, never emoji/font)."""
    return get_heart_filled() if is_favorite else get_heart_outline()


class SongRow(ctk.CTkFrame):
    """One rendered song. Never imports the controller — only callbacks."""

    def __init__(
        self,
        master,
        idx: int,
        song: Song,
        *,
        allow_remove: bool = False,
        scroll_frame=None,
        highlighted: bool = False,
        on_select: Callable[[int | None], None] | None = None,
        on_favorite: Callable[[int | None], None] | None = None,
        on_add: Callable[[int | None], None] | None = None,
        on_remove: Callable[[int | None], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.song_id = song.id
        self._highlighted = False
        self._on_select = on_select
        self._on_favorite = on_favorite
        self._on_add = on_add
        self._on_remove = on_remove
        self._scroll_frame = scroll_frame if scroll_frame is not None else master
        self.pack(fill="x", pady=2)
        configure_columns(self)

        display = format_song_row(song)

        self.lbl_num = ctk.CTkLabel(self, text=str(idx), text_color=theme.colors.text_muted)
        self.lbl_num.grid(row=0, column=0, sticky="w", padx=10)

        # Title stacked over artist (Spotify-style): artist sits right
        # under the title instead of a far-away column.
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=10)
        self.lbl_title = ctk.CTkLabel(info, text=display["title"], font=theme.fonts.row_title)
        self.lbl_title.pack(anchor="w")
        self.lbl_artist = ctk.CTkLabel(
            info, text=display["artist"], text_color=theme.colors.text_muted
        )
        self.lbl_artist.pack(anchor="w")

        self.lbl_duration = ctk.CTkLabel(self, text=display["duration"])
        self.lbl_duration.grid(row=0, column=4, sticky="e", padx=20)

        # Favorite toggle for this song.
        self.btn_fav = ctk.CTkButton(
            self,
            text="",
            image=favorite_icon(song.is_favorite),
            width=36,
            fg_color="transparent",
            hover_color=theme.colors.hover,
            text_color=theme.colors.text_muted,
            command=lambda: self._emit(self._on_favorite),
        )
        self.btn_fav.grid(row=0, column=3)
        Tooltip(self.btn_fav, "Toggle favorite")
        enable_wheel_scroll(self.btn_fav, self._scroll_frame)

        # Playlist action: add ("+") or remove ("×") depending on the view.
        if allow_remove:
            self.btn_list = ctk.CTkButton(
                self,
                text="×",
                width=36,
                fg_color="transparent",
                hover_color=theme.colors.hover,
                text_color=theme.colors.text_muted,
                command=lambda: self._emit(self._on_remove),
            )
            Tooltip(self.btn_list, "Remove from playlist")
        else:
            self.btn_list = ctk.CTkButton(
                self,
                text="+",
                width=36,
                fg_color="transparent",
                hover_color=theme.colors.hover,
                text_color=theme.colors.text_muted,
                command=lambda: self._emit(self._on_add),
            )
            Tooltip(self.btn_list, "Add to playlist")
        self.btn_list.grid(row=0, column=2)
        enable_wheel_scroll(self.btn_list, self._scroll_frame)

        self._bind_interaction([self, info, self.lbl_num, self.lbl_title, self.lbl_artist])
        if highlighted:
            self.set_highlight(True)

    def refresh(self, song: Song) -> None:
        """Refresh labels + favorite icon in place (no destroy/recreate)."""
        display = format_song_row(song)
        self.lbl_title.configure(text=display["title"])
        self.lbl_artist.configure(text=display["artist"])
        self.lbl_duration.configure(text=display["duration"])
        self.btn_fav.configure(image=favorite_icon(song.is_favorite))

    def set_highlight(self, on: bool) -> None:
        """Now-playing look (accent number + surface bg); wins over hover."""
        self._highlighted = on
        self.configure(fg_color=theme.colors.surface if on else "transparent")
        self.lbl_num.configure(text_color=theme.colors.accent if on else theme.colors.text_muted)

    def _emit(self, callback: Callable[[int | None], None] | None) -> None:
        if self.song_id is not None and callback is not None:
            callback(self.song_id)

    def _bind_interaction(self, widgets) -> None:
        """Click-to-play on the whole row, hover feedback, wheel scroll.

        Clicking any label behaves like clicking the row itself (Tk does
        not propagate <Button-1> from a child Label to its parent Frame).
        Every widget also gets an explicit Button-4/5 binding so a wheel
        notch over any nested child scrolls exactly once (it stops the
        global CTkScrollableFrame handler via "break").
        """

        def _hover(on: bool) -> None:
            if self._highlighted:
                return  # now-playing highlight wins over hover
            self.configure(fg_color=theme.colors.hover if on else "transparent")

        for widget in widgets:
            widget.bind("<Button-1>", lambda _e: self._emit(self._on_select), add="+")
            widget.bind("<Enter>", lambda _e: _hover(True), add="+")
            widget.bind("<Leave>", lambda _e: _hover(False), add="+")
            enable_wheel_scroll(widget, self._scroll_frame)
