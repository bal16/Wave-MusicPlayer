"""Small modal dialogs for playlist flows (Tk-based, blocking).

Kept in one module so views stay free of dialog construction details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from views.theme import theme

if TYPE_CHECKING:
    from domain.entities import Playlist


def ask_text(title: str, prompt: str, initial: str = "") -> str | None:
    """Single-line text input. Returns None when cancelled or blank."""
    dialog = ctk.CTkInputDialog(text=prompt, title=title)
    if initial:
        dialog._entry.insert(0, initial)
    value = dialog.get_input()
    if value is None:
        return None
    return value.strip() or None


def choose_playlist(parent, playlists: list[Playlist], song_title: str) -> int | str | None:
    """Modal chooser: playlist id, "new" for a fresh playlist, None if cancelled."""
    result: dict = {"value": None}

    top = ctk.CTkToplevel(parent)
    top.title("Add to playlist")
    top.geometry("320x400")
    top.transient(parent)
    top.grab_set()

    ctk.CTkLabel(top, text=f"Add '{song_title}' to…", font=theme.fonts.body).pack(
        pady=15, padx=20
    )

    scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=10, pady=5)

    def pick(value) -> None:
        result["value"] = value
        top.destroy()

    for playlist in playlists:
        ctk.CTkButton(
            scroll,
            text=f"{playlist.name} ({playlist.song_count})",
            fg_color="transparent",
            anchor="w",
            command=lambda pid=playlist.id: pick(pid),
        ).pack(fill="x", pady=3)

    ctk.CTkButton(
        scroll, text="+ New playlist…", border_width=1, command=lambda: pick("new")
    ).pack(fill="x", pady=10)
    ctk.CTkButton(scroll, text="Cancel", fg_color="transparent", command=top.destroy).pack(
        fill="x", pady=3
    )

    parent.wait_window(top)
    return result["value"]


def confirm(parent, title: str, message: str) -> bool:
    """Yes/no confirmation. Returns True only on explicit Yes."""
    result = {"value": False}
    top = ctk.CTkToplevel(parent)
    top.title(title)
    top.geometry("300x150")
    top.transient(parent)
    top.grab_set()

    ctk.CTkLabel(top, text=message, font=theme.fonts.body).pack(pady=20, padx=20)

    row = ctk.CTkFrame(top, fg_color="transparent")
    row.pack(pady=10)

    def decide(value: bool) -> None:
        result["value"] = value
        top.destroy()

    ctk.CTkButton(row, text="Delete", width=100, command=lambda: decide(True)).pack(
        side="left", padx=5
    )
    ctk.CTkButton(
        row, text="Cancel", width=100, fg_color="transparent", command=lambda: decide(False)
    ).pack(side="left", padx=5)

    parent.wait_window(top)
    return result["value"]
