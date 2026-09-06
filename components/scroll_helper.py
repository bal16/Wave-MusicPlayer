"""Scrolling support for CTkScrollableFrame lists.

Background: on the reporter's machine a touchpad gesture arrives as
plain <Button-4/5> (verified with /tmp/opencode/scroll_probe.py), and the
built-in CTkScrollableFrame handler routes those via an ancestry check
(_check_if_valid_scroll). To make scrolling deterministic no matter
which nested child widget sits under the cursor, every row widget also
gets an explicit wheel binding that scrolls exactly once ("break" stops
the global handler from firing a second time for the same notch).

Keyboard navigation (Up/Down/PageUp/PageDown/Home/End) is registered
per list and only drives the list currently mapped.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

_registry: list[Any] = []
_keys_bound = False


def _visible_frame() -> Any | None:
    """The single registered list currently mapped (only one is at a time)."""
    for sf in _registry:
        try:
            if sf._parent_frame.winfo_ismapped():
                return sf
        except tk.TclError:
            continue
    return None


def _on_key(event: tk.Event) -> str | None:
    # Never hijack text editing or sliders.
    if isinstance(event.widget, (tk.Entry, tk.Text, ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkSlider)):
        return None
    sf = _visible_frame()
    if sf is None:
        return None
    canvas = sf._parent_canvas
    keysym = event.keysym
    try:
        if keysym == "Up":
            canvas.yview_scroll(-2, "units")
        elif keysym == "Down":
            canvas.yview_scroll(2, "units")
        elif keysym == "Prior":
            canvas.yview_scroll(-1, "pages")
        elif keysym == "Next":
            canvas.yview_scroll(1, "pages")
        elif keysym == "Home":
            canvas.yview_moveto(0.0)
        elif keysym == "End":
            canvas.yview_moveto(1.0)
        else:
            return None
    except tk.TclError:
        return None
    return "break"


def register_scrollable_frame(scrollable_frame: Any) -> Any:
    """Register a list for keyboard nav + widen its scrollbar. Idempotent."""
    global _keys_bound
    if scrollable_frame not in _registry:
        _registry.append(scrollable_frame)
    try:
        scrollable_frame._scrollbar.configure(width=20)
    except (tk.TclError, AttributeError):
        pass
    if not _keys_bound:
        master = scrollable_frame.winfo_toplevel()
        for seq in ("<Up>", "<Down>", "<Prior>", "<Next>", "<Home>", "<End>"):
            master.bind_all(seq, _on_key, add=True)
        _keys_bound = True
    return scrollable_frame


def enable_wheel_scroll(widget: Any, scrollable_frame: Any) -> None:
    """Bind Button-4/5 directly so this widget always scrolls its list once.

    The "break" stops the widget→class→toplevel→all chain, so the global
    CTkScrollableFrame handler does not scroll a second time. Attach to
    every widget of a row (frame, labels, buttons); canvas gaps keep
    working through the built-in global handler.
    """
    canvas = scrollable_frame._parent_canvas

    def _scroll(delta: int) -> str:
        try:
            if canvas.yview() != (0.0, 1.0):
                canvas.yview_scroll(delta, "units")
        except tk.TclError:
            pass
        return "break"

    widget.bind("<Button-4>", lambda _e: _scroll(-1), add="+")
    widget.bind("<Button-5>", lambda _e: _scroll(1), add="+")
