"""Tooltip — tiny hover tooltip, Tk-only, no dependencies.

Reusable by any widget (song rows today, transport keys tomorrow).
"""

from __future__ import annotations

import tkinter as tk

from views.theme import theme


class Tooltip:
    """Show a small label after hovering 500ms; hide on leave/press/scroll."""

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
