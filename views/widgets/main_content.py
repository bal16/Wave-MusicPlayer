from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from views.theme import theme
from views.widgets.scroll_helper import register_scrollable_frame
from views.widgets.song_row import SongRow, configure_columns

if TYPE_CHECKING:
    from domain.entities import Song

# Upper bound for one render pass. Full virtualization stays backlog;
# the overflow label tells the user the list is truncated, not empty.
MAX_VISIBLE_ROWS = 300

# Lists bigger than this render in slices via after() so boot (and any
# full rebuild) never freezes the window on ~2000 widgets at once.
# The empty-state label doubles as the "Loading… i/N" readout meanwhile.
CHUNK_THRESHOLD = 80
CHUNK_SIZE = 40


class MainContent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Callbacks bound by the View (never import the controller here).
        self.on_select: Callable[[int], None] | None = None
        self.on_favorite: Callable[[int], None] | None = None
        self.on_add_to_playlist: Callable[[int], None] | None = None
        self.on_remove_from_playlist: Callable[[int], None] | None = None

        # Header text
        self.lbl_header = ctk.CTkLabel(self, text="All Music", font=theme.fonts.header)
        self.lbl_header.pack(pady=30, padx=40, anchor="w")

        # Sticky column headings (outside the scroll area so they never scroll away).
        headings = ctk.CTkFrame(self, fg_color="transparent", height=30)
        headings.pack(fill="x", padx=20, pady=(0, 10))
        configure_columns(headings)
        ctk.CTkLabel(headings, text="#", text_color=theme.colors.text_muted).grid(
            row=0, column=0, sticky="w", padx=10
        )
        ctk.CTkLabel(headings, text="Title", font=theme.fonts.row_title).grid(
            row=0, column=1, sticky="w", padx=10
        )
        ctk.CTkLabel(headings, text="Duration").grid(row=0, column=4, sticky="e", padx=20)

        # Scrollable Song List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20)
        # Keyboard navigation registry (wheel events arrive natively as
        # Button-4/5; each row widget also gets an explicit wheel binding
        # in _bind_row_interaction so scrolling is deterministic).
        register_scrollable_frame(self.scroll_frame)

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

        self._rows: list[SongRow] = []
        self._row_by_id: dict[int, SongRow] = {}
        self._allow_remove = False
        self._playing_id: int | None = None

    def set_header(self, title: str) -> None:
        """Change the header (e.g. playlist name) without recreating."""
        self.lbl_header.configure(text=title)

    def set_songs(
        self, songs: list[Song], *, allow_remove: bool = False, playing_id: int | None = None
    ) -> None:
        """Replace the rendered rows in place (no frame recreate).

        allow_remove swaps the row "+" (add to playlist) for "×"
        (remove from the shown playlist). playing_id re-applies the
        now-playing highlight after the rebuild.
        """
        self._allow_remove = allow_remove
        self._playing_id = playing_id
        self._clear_rows()
        visible = songs[:MAX_VISIBLE_ROWS]

        if not visible:
            self.lbl_empty.configure(text="No songs yet — Add a folder to start")
            self.lbl_empty.pack(fill="x", pady=20)
            self.lbl_overflow.pack_forget()
            return

        self.lbl_empty.pack_forget()
        if len(visible) > CHUNK_THRESHOLD:
            self._render_chunked(visible, len(songs))
        else:
            for idx, song in enumerate(visible, start=1):
                self.create_song_row(idx, song)
            self._finish_overflow(len(songs))

    def _render_chunked(self, visible: list[Song], total: int | None = None) -> None:
        """Render big lists in slices so the window stays responsive.

        Progress is shown in place ("Loading… i/N"); each slice yields
        to the event loop via after(). A TclError means the window was
        closed mid-load — just stop.

        ``total`` is the untruncated song count so the overflow note
        reports the real remainder; it defaults to ``len(visible)``.
        """
        total = len(visible) if total is None else total
        self.lbl_empty.configure(text=f"Loading… 0/{len(visible)}")
        self.lbl_empty.pack(fill="x", pady=20)
        state = {"done": 0}

        def _batch() -> None:
            try:
                end = min(state["done"] + CHUNK_SIZE, len(visible))
                for j in range(state["done"], end):
                    self.create_song_row(j + 1, visible[j])
                state["done"] = end
                if end < len(visible):
                    self.lbl_empty.configure(text=f"Loading… {end}/{len(visible)}")
                    self.after(1, _batch)
                else:
                    self.lbl_empty.pack_forget()
                    self._finish_overflow(total)
            except tk.TclError:
                pass

        self.after(1, _batch)

    def _finish_overflow(self, total: int) -> None:
        if total > MAX_VISIBLE_ROWS:
            self.lbl_overflow.configure(
                text=f"…and {total - MAX_VISIBLE_ROWS} more (showing first {MAX_VISIBLE_ROWS})"
            )
            self.lbl_overflow.pack(fill="x", pady=10)
        else:
            self.lbl_overflow.pack_forget()

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.destroy()
        self._rows = []
        self._row_by_id = {}
        self.lbl_overflow.pack_forget()

    def set_playing(self, song_id: int | None) -> bool:
        """Highlight the now-playing row (accent number + surface bg).

        Returns True when the song is currently rendered, False when the
        caller should fall back to a full refresh.
        """
        if song_id == self._playing_id and song_id is not None:
            return True
        old = self._row_by_id.get(self._playing_id) if self._playing_id is not None else None
        if old is not None:
            old.set_highlight(False)
        self._playing_id = song_id
        if song_id is None:
            return True
        refs = self._row_by_id.get(song_id)
        if refs is None:
            return False
        refs.set_highlight(True)
        return True

    def update_song(self, song: Song) -> bool:
        """Update one rendered row in place (no destroy/recreate).

        Returns True on fast-path hit, False when the caller should
        fall back to a full refresh (song not currently rendered).
        """
        if song.id is None:
            return False
        refs = self._row_by_id.get(song.id)
        if refs is None:
            return False
        refs.refresh(song)
        return True

    def create_song_row(self, idx: int, song: Song) -> SongRow:
        """Build one SongRow, register it, restore highlight if playing."""
        row = SongRow(
            self.scroll_frame,
            idx,
            song,
            allow_remove=self._allow_remove,
            scroll_frame=self.scroll_frame,
            highlighted=song.id is not None and song.id == self._playing_id,
            on_select=self._emit_select,
            on_favorite=self._emit_favorite,
            on_add=self._emit_add_to_playlist,
            on_remove=self._emit_remove,
        )
        self._rows.append(row)
        if song.id is not None:
            self._row_by_id[song.id] = row
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
