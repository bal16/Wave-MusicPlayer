from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from views.theme import format_duration, theme

if TYPE_CHECKING:
    from domain.entities import Song

# Upper bound for one render pass. Full virtualization stays backlog;
# the overflow label tells the user the list is truncated, not empty.
MAX_VISIBLE_ROWS = 300

HEART_ON = "♥"
HEART_OFF = "♡"


def format_song_row(song: Song) -> dict:
    """Pure mapping from Song to row display values (Tk-free, unit-tested)."""
    return {
        "title": song.title,
        "artist": song.artist,
        "duration": format_duration(song.duration),
        "favorite_mark": HEART_ON if song.is_favorite else HEART_OFF,
    }


class MainContent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Callbacks bound by the View (never import the controller here).
        self.on_select: Callable[[int], None] | None = None
        self.on_favorite: Callable[[int], None] | None = None
        self.on_add_to_playlist: Callable[[int], None] | None = None
        self.on_remove_from_playlist: Callable[[int], None] | None = None

        # Header text
        self.lbl_header = ctk.CTkLabel(self, text="All Musics", font=theme.fonts.header)
        self.lbl_header.pack(pady=30, padx=40, anchor="w")

        # Scrollable Song List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20)

        # row headings
        headings = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=30)
        headings.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(headings, text="#", width=30, text_color=theme.colors.text_muted).pack(
            side="left", padx=10
        )
        ctk.CTkLabel(headings, text="Title", font=theme.fonts.row_title).pack(side="left", padx=10)
        ctk.CTkLabel(headings, text="Duration", width=50).pack(side="right", padx=20)

        # Empty state (visible until the first set_songs with data).
        self.lbl_empty = ctk.CTkLabel(
            self.scroll_frame,
            text="No songs yet — Add a folder to start",
            text_color=theme.colors.text_muted,
        )
        self.lbl_empty.pack(fill="x", pady=20)

        # Overflow note for truncated renders.
        self.lbl_overflow = ctk.CTkLabel(
            self.scroll_frame, text="", text_color=theme.colors.text_muted
        )

        self._rows: list[ctk.CTkFrame] = []
        self._allow_remove = False

    def set_header(self, title: str) -> None:
        """Change the header (e.g. playlist name) without recreating."""
        self.lbl_header.configure(text=title)

    def set_songs(self, songs: list[Song], *, allow_remove: bool = False) -> None:
        """Replace the rendered rows in place (no frame recreate).

        allow_remove swaps the row "+" (add to playlist) for "×"
        (remove from the shown playlist).
        """
        self._allow_remove = allow_remove
        self._clear_rows()
        visible = songs[:MAX_VISIBLE_ROWS]

        if visible:
            self.lbl_empty.pack_forget()
        else:
            self.lbl_empty.pack(fill="x", pady=20)

        for idx, song in enumerate(visible, start=1):
            self.create_song_row(idx, song)

        if len(songs) > MAX_VISIBLE_ROWS:
            self.lbl_overflow.configure(
                text=f"…and {len(songs) - MAX_VISIBLE_ROWS} more (showing first {MAX_VISIBLE_ROWS})"
            )
            self.lbl_overflow.pack(fill="x", pady=10)
        else:
            self.lbl_overflow.pack_forget()

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.destroy()
        self._rows = []
        self.lbl_overflow.pack_forget()

    def create_song_row(self, idx: int, song: Song) -> ctk.CTkFrame:
        display = format_song_row(song)
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=50)
        row.pack(fill="x", pady=5)

        ctk.CTkLabel(row, text=str(idx), width=30, text_color=theme.colors.text_muted).pack(
            side="left", padx=10
        )
        ctk.CTkLabel(row, text=display["title"], font=theme.fonts.row_title).pack(
            side="left", padx=10
        )
        ctk.CTkLabel(row, text=display["artist"], text_color=theme.colors.text_muted).pack(
            side="left"
        )
        ctk.CTkLabel(row, text=display["duration"], width=50).pack(side="right", padx=20)

        # Favorite toggle for this song.
        btn_fav = ctk.CTkButton(
            row,
            text=display["favorite_mark"],
            width=30,
            fg_color="transparent",
            text_color=theme.colors.text_muted,
            command=lambda song_id=song.id: self._emit_favorite(song_id),
        )
        btn_fav.pack(side="right")

        # Playlist action: add ("+") or remove ("×") depending on the view.
        if self._allow_remove:
            btn_list = ctk.CTkButton(
                row,
                text="×",
                width=30,
                fg_color="transparent",
                text_color=theme.colors.text_muted,
                command=lambda song_id=song.id: self._emit_remove(song_id),
            )
        else:
            btn_list = ctk.CTkButton(
                row,
                text="+",
                width=30,
                fg_color="transparent",
                text_color=theme.colors.text_muted,
                command=lambda song_id=song.id: self._emit_add_to_playlist(song_id),
            )
        btn_list.pack(side="right")

        # Row click selects the song (stub for Fase 2 playback).
        row.bind("<Button-1>", lambda _e, song_id=song.id: self._emit_select(song_id))

        self._rows.append(row)
        return row

    def _emit_select(self, song_id: int | None) -> None:
        if song_id is not None and self.on_select is not None:
            self.on_select(song_id)

    def _emit_favorite(self, song_id: int | None) -> None:
        if song_id is not None and self.on_favorite is not None:
            self.on_favorite(song_id)

    def _emit_add_to_playlist(self, song_id: int | None) -> None:
        if song_id is not None and self.on_add_to_playlist is not None:
            self.on_add_to_playlist(song_id)

    def _emit_remove(self, song_id: int | None) -> None:
        if song_id is not None and self.on_remove_from_playlist is not None:
            self.on_remove_from_playlist(song_id)
