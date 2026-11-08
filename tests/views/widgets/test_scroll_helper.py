"""Unit tests for views/widgets/scroll_helper.py (Tk faked)."""

from __future__ import annotations

import tkinter

import customtkinter as ctk

from tests.support import fake_tk
from views.widgets import scroll_helper


def mapped_frame():
    frame = fake_tk.FakeScrollableFrame()
    frame._parent_frame = frame
    frame._mapped = True
    return frame


def test_visible_frame_returns_mapped_frame():
    frame = mapped_frame()
    scroll_helper._registry.append(frame)
    assert scroll_helper._visible_frame() is frame


def test_visible_frame_skips_unmapped_and_tcl_errors():
    unmapped = mapped_frame()
    unmapped._mapped = False
    broken = mapped_frame()

    def boom():
        raise tkinter.TclError("gone")

    broken.winfo_ismapped = boom
    scroll_helper._registry.extend([unmapped, broken])
    assert scroll_helper._visible_frame() is None


def test_register_adds_once_and_widens_scrollbar():
    frame = mapped_frame()
    scroll_helper.register_scrollable_frame(frame)
    scroll_helper.register_scrollable_frame(frame)
    assert scroll_helper._registry == [frame]
    assert frame._scrollbar.kwargs["width"] == 20


def test_register_binds_keyboard_once():
    first, second = mapped_frame(), mapped_frame()
    scroll_helper.register_scrollable_frame(first)
    scroll_helper.register_scrollable_frame(second)
    assert scroll_helper._keys_bound is True
    for sequence in ("<Up>", "<Down>", "<Prior>", "<Next>", "<Home>", "<End>"):
        assert sequence in first.bindings


def test_register_tolerates_scrollbar_errors():
    frame = mapped_frame()

    def boom(**kwargs):
        raise tkinter.TclError("no scrollbar")

    frame._scrollbar.configure = boom
    scroll_helper.register_scrollable_frame(frame)


def test_enable_wheel_scroll_scrolls_once():
    frame = mapped_frame()
    frame._parent_canvas.set_view(0.0, 0.5)
    widget = fake_tk.FakeWidget()
    scroll_helper.enable_wheel_scroll(widget, frame)

    assert widget.bindings["<Button-4>"][0](None) == "break"
    assert widget.bindings["<Button-5>"][0](None) == "break"
    assert frame._parent_canvas.scroll_calls == [(-1, "units"), (1, "units")]


def test_enable_wheel_scroll_ignores_full_list():
    frame = mapped_frame()  # default view is not scrollable
    widget = fake_tk.FakeWidget()
    scroll_helper.enable_wheel_scroll(widget, frame)
    widget.bindings["<Button-4>"][0](None)
    assert frame._parent_canvas.scroll_calls == []


def test_enable_wheel_scroll_swallows_tcl_errors():
    frame = mapped_frame()

    def boom(*args):
        raise tkinter.TclError("gone")

    frame._parent_canvas.yview = boom
    widget = fake_tk.FakeWidget()
    scroll_helper.enable_wheel_scroll(widget, frame)
    assert widget.bindings["<Button-4>"][0](None) == "break"


def test_on_key_ignores_text_editing_widgets():
    frame = mapped_frame()
    scroll_helper._registry.append(frame)
    for widget in (
        tkinter.Entry(),
        tkinter.Text(),
        ctk.CTkEntry(),
        ctk.CTkTextbox(),
        ctk.CTkSlider(),
    ):
        event = fake_tk.FakeEvent(widget=widget, keysym="Up")
        assert scroll_helper._on_key(event) is None


def test_on_key_returns_none_without_visible_frame():
    event = fake_tk.FakeEvent(widget=fake_tk.FakeWidget(), keysym="Up")
    assert scroll_helper._on_key(event) is None


def test_on_key_scrolls_visible_frame():
    frame = mapped_frame()
    scroll_helper._registry.append(frame)
    canvas = frame._parent_canvas
    widget = fake_tk.FakeWidget()

    for keysym in ("Up", "Down"):
        event = fake_tk.FakeEvent(widget=widget, keysym=keysym)
        assert scroll_helper._on_key(event) == "break"
    for keysym in ("Prior", "Next"):
        event = fake_tk.FakeEvent(widget=widget, keysym=keysym)
        assert scroll_helper._on_key(event) == "break"
    for keysym in ("Home", "End"):
        event = fake_tk.FakeEvent(widget=widget, keysym=keysym)
        assert scroll_helper._on_key(event) == "break"

    assert canvas.scroll_calls == [(-2, "units"), (2, "units"), (-1, "pages"), (1, "pages")]
    assert canvas.moveto_calls == [0.0, 1.0]


def test_on_key_ignores_unknown_keysym():
    frame = mapped_frame()
    scroll_helper._registry.append(frame)
    event = fake_tk.FakeEvent(widget=fake_tk.FakeWidget(), keysym="a")
    assert scroll_helper._on_key(event) is None


def test_on_key_swallows_tcl_errors():
    frame = mapped_frame()
    scroll_helper._registry.append(frame)

    def boom(*args):
        raise tkinter.TclError("gone")

    frame._parent_canvas.yview_scroll = boom
    event = fake_tk.FakeEvent(widget=fake_tk.FakeWidget(), keysym="Up")
    assert scroll_helper._on_key(event) is None
