from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from components.scroll_helper import enable_wheel_scroll, register_scrollable_frame
from utils.icons import get_heart_filled, get_heart_outline
from views.theme import format_duration, theme

if TYPE_CHECKING:
    from domain.entities import Song

# Upper bound for one render pass. Full virtualization stays backlog;
# the overflow label tells the user the list is truncated, not empty.
MAX_VISIBLE_ROWS = 300

HEART_ON = "♥"
HEART_OFF = "♡"


def favorite_icon(is_favorite: bool):
    """Heart asset for love/like/favorite state (icon, never emoji/font)."""
    return get_heart_filled() if is_favorite else get_heart_outline()


# Grid columns shared by the sticky header and every row so they align:
# 0:# | 1:info (title stacked over artist) | 2:playlist action | 3:favorite | 4:duration
_FIXED_COLS = {0: 34, 2: 40, 3: 40, 4: 56}
_WEIGHTED_COLS = {1: 1}


def _configure_columns(frame) -> None:
    for col, minsize in _FIXED_COLS.items():
        frame.grid_columnconfigure(col, weight=0, minsize=minsize)
    for col, weight in _WEIGHTED_COLS.items():
        frame.grid_columnconfigure(col, weight=weight)


class _Tooltip:
    """Tiny hover tooltip (no dependency, Tk-only)."""

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        self._after: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress-1>", self._hide, add="+")
        widget.bind("<Button-4>", self._hide, add="+")
        widget.bind("<Button-5>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after = self.widget.after(500, self._show)

    def _cancel(self) -> None:
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except tk.TclError:
                pass
            self._after = None

    def _show(self) -> None:
        self._after = None
        if self.tip is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(
                self.tip,
                text=self.text,
                bg=theme.colors.surface,
                fg=theme.colors.text_primary,
                font=(theme.fonts.sans, 11),
                padx=8,
                pady=4,
            ).pack()
        except tk.TclError:
            self.tip = None

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


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
        self.lbl_header = ctk.CTkLabel(self, text="All Music", font=theme.fonts.header)
        self.lbl_header.pack(pady=30, padx=40, anchor="w")

        # Sticky column headings (outside the scroll area so they never scroll away).
        headings = ctk.CTkFrame(self, fg_color="transparent", height=30)
        headings.pack(fill="x", padx=20, pady=(0, 10))
        _configure_columns(headings)
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

        self._rows: list[ctk.CTkFrame] = []
        self._row_by_id: dict[int, dict] = {}
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
            old["frame"].configure(fg_color="transparent")
            old["lbl_num"].configure(text_color=theme.colors.text_muted)
        self._playing_id = song_id
        if song_id is None:
            return True
        refs = self._row_by_id.get(song_id)
        if refs is None:
            return False
        refs["frame"].configure(fg_color=theme.colors.surface)
        refs["lbl_num"].configure(text_color=theme.colors.accent)
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
        display = format_song_row(song)
        refs["lbl_title"].configure(text=display["title"])
        refs["lbl_artist"].configure(text=display["artist"])
        refs["lbl_duration"].configure(text=display["duration"])
        refs["btn_fav"].configure(image=favorite_icon(song.is_favorite))
        return True

    def create_song_row(self, idx: int, song: Song) -> ctk.CTkFrame:
        display = format_song_row(song)
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        _configure_columns(row)

        lbl_num = ctk.CTkLabel(row, text=str(idx), text_color=theme.colors.text_muted)
        lbl_num.grid(row=0, column=0, sticky="w", padx=10)

        # Title stacked over artist (Spotify-style): artist sits right
        # under the title instead of a far-away column.
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=10)
        lbl_title = ctk.CTkLabel(info, text=display["title"], font=theme.fonts.row_title)
        lbl_title.pack(anchor="w")
        lbl_artist = ctk.CTkLabel(info, text=display["artist"], text_color=theme.colors.text_muted)
        lbl_artist.pack(anchor="w")

        lbl_duration = ctk.CTkLabel(row, text=display["duration"])
        lbl_duration.grid(row=0, column=4, sticky="e", padx=20)

        # Favorite toggle for this song.
        btn_fav = ctk.CTkButton(
            row,
            text="",
            image=favorite_icon(song.is_favorite),
            width=36,
            fg_color="transparent",
            hover_color=theme.colors.hover,
            text_color=theme.colors.text_muted,
            command=lambda song_id=song.id: self._emit_favorite(song_id),
        )
        btn_fav.grid(row=0, column=3)
        _Tooltip(btn_fav, "Toggle favorite")
        enable_wheel_scroll(btn_fav, self.scroll_frame)

        # Playlist action: add ("+") or remove ("×") depending on the view.
        if self._allow_remove:
            btn_list = ctk.CTkButton(
                row,
                text="×",
                width=36,
                fg_color="transparent",
                hover_color=theme.colors.hover,
                text_color=theme.colors.text_muted,
                command=lambda song_id=song.id: self._emit_remove(song_id),
            )
            _Tooltip(btn_list, "Remove from playlist")
        else:
            btn_list = ctk.CTkButton(
                row,
                text="+",
                width=36,
                fg_color="transparent",
                hover_color=theme.colors.hover,
                text_color=theme.colors.text_muted,
                command=lambda song_id=song.id: self._emit_add_to_playlist(song_id),
            )
            _Tooltip(btn_list, "Add to playlist")
        btn_list.grid(row=0, column=2)
        enable_wheel_scroll(btn_list, self.scroll_frame)

        self._rows.append(row)
        if song.id is not None:
            self._row_by_id[song.id] = {
                "frame": row,
                "lbl_num": lbl_num,
                "lbl_title": lbl_title,
                "lbl_artist": lbl_artist,
                "lbl_duration": lbl_duration,
                "btn_fav": btn_fav,
            }
            # Restore the now-playing highlight after a rebuild.
            if song.id == self._playing_id:
                row.configure(fg_color=theme.colors.surface)
                lbl_num.configure(text_color=theme.colors.accent)
            self._bind_row_interaction(
                song.id, [row, info, lbl_num, lbl_title, lbl_artist, lbl_duration]
            )
        return row

    def _bind_row_interaction(self, song_id: int, widgets) -> None:
        """Click-to-play on the whole row, hover feedback, wheel scroll.

        Clicking any label behaves like clicking the row itself (Tk does
        not propagate <Button-1> from a child Label to its parent Frame).
        Every widget also gets an explicit Button-4/5 binding so a wheel
        notch over any nested child scrolls exactly once (it stops the
        global CTkScrollableFrame handler via "break").
        """
        refs = self._row_by_id.get(song_id)

        def _hover(on: bool) -> None:
            if refs is None:
                return
            if song_id == self._playing_id:
                return  # now-playing highlight wins over hover
            refs["frame"].configure(fg_color=theme.colors.hover if on else "transparent")

        for widget in widgets:
            widget.bind("<Button-1>", lambda _e, sid=song_id: self._emit_select(sid), add="+")
            widget.bind("<Enter>", lambda _e: _hover(True), add="+")
            widget.bind("<Leave>", lambda _e: _hover(False), add="+")
            enable_wheel_scroll(widget, self.scroll_frame)

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
