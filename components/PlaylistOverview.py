from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from views.theme import theme

if TYPE_CHECKING:
    from domain.entities import Playlist


class PlaylistOverview(ctk.CTkFrame):
    """List of playlists: name, song count, open/rename/delete actions."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Callbacks bound by the View (never import the controller here).
        self.on_select: Callable[[int], None] | None = None
        self.on_create: Callable[[], None] | None = None
        self.on_rename: Callable[[int], None] | None = None
        self.on_delete: Callable[[int], None] | None = None

        self.lbl_header = ctk.CTkLabel(self, text="Playlists", font=theme.fonts.header)
        self.lbl_header.pack(pady=30, padx=40, anchor="w")

        self.btn_new = ctk.CTkButton(
            self,
            text="+ New Playlist",
            width=160,
            fg_color="transparent",
            border_width=1,
            command=self._emit_create,
        )
        self.btn_new.pack(padx=40, anchor="w", pady=(0, 10))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20)

        self.lbl_empty = ctk.CTkLabel(
            self.scroll_frame,
            text="No playlists yet — create one to start",
            text_color=theme.colors.text_muted,
        )
        self.lbl_empty.pack(fill="x", pady=20)

        self._rows: list[ctk.CTkFrame] = []

    def set_playlists(self, playlists: list[Playlist]) -> None:
        """Replace the rendered rows in place (no frame recreate)."""
        for row in self._rows:
            row.destroy()
        self._rows = []

        if playlists:
            self.lbl_empty.pack_forget()
        else:
            self.lbl_empty.pack(fill="x", pady=20)

        for playlist in playlists:
            self._rows.append(self.create_playlist_row(playlist))

    def create_playlist_row(self, playlist: Playlist) -> ctk.CTkFrame:
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=50)
        row.pack(fill="x", pady=5)

        btn_name = ctk.CTkButton(
            row,
            text=playlist.name,
            font=theme.fonts.row_title,
            fg_color="transparent",
            anchor="w",
            command=lambda pid=playlist.id: self._emit_select(pid),
        )
        btn_name.pack(side="left", padx=10, expand=True, fill="x")
        ctk.CTkLabel(
            row,
            text=f"{playlist.song_count} songs",
            text_color=theme.colors.text_muted,
        ).pack(side="left")

        ctk.CTkButton(
            row,
            text="Rename",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=lambda pid=playlist.id: self._emit_rename(pid),
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            row,
            text="✕",
            width=30,
            fg_color="transparent",
            text_color=theme.colors.text_muted,
            command=lambda pid=playlist.id: self._emit_delete(pid),
        ).pack(side="right")

        return row

    def _emit_select(self, playlist_id: int | None) -> None:
        if playlist_id is not None and self.on_select is not None:
            self.on_select(playlist_id)

    def _emit_create(self) -> None:
        if self.on_create is not None:
            self.on_create()

    def _emit_rename(self, playlist_id: int | None) -> None:
        if playlist_id is not None and self.on_rename is not None:
            self.on_rename(playlist_id)

    def _emit_delete(self, playlist_id: int | None) -> None:
        if playlist_id is not None and self.on_delete is not None:
            self.on_delete(playlist_id)
