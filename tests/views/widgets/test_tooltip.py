"""Unit tests for views/widgets/tooltip.py (Tk faked)."""

from __future__ import annotations

import tkinter
from unittest.mock import MagicMock

from tests.support import fake_tk
from views.widgets import tooltip as module
from views.widgets.tooltip import Tooltip


def make_tooltip():
    widget = fake_tk.FakeWidget()
    return Tooltip(widget, "Helpful text"), widget


def test_constructor_binds_hover_and_dismiss_events():
    tooltip, widget = make_tooltip()
    assert tooltip.text == "Helpful text"
    for sequence in ("<Enter>", "<Leave>", "<ButtonPress-1>", "<Button-4>", "<Button-5>"):
        assert sequence in widget.bindings


def test_schedule_sets_after_job_and_cancels_previous():
    tooltip, widget = make_tooltip()
    widget.after = MagicMock(side_effect=["job-1", "job-2"])
    widget.after_cancel = MagicMock()

    tooltip._schedule()
    assert tooltip._after == "job-1"
    tooltip._schedule()
    assert widget.after_cancel.call_args[0][0] == "job-1"
    assert tooltip._after == "job-2"


def test_cancel_without_job_is_noop():
    tooltip, _ = make_tooltip()
    tooltip._cancel()


def test_cancel_swallows_tcl_errors():
    tooltip, widget = make_tooltip()
    tooltip._after = "job"

    def boom(_job):
        raise tkinter.TclError("gone")

    widget.after_cancel = boom
    tooltip._cancel()
    assert tooltip._after is None


def test_show_creates_toplevel_and_label():
    tooltip, _ = make_tooltip()
    tooltip._show()
    assert tooltip.tip is not None
    assert tooltip.tip.kwargs["overrideredirect"] is True
    assert tooltip.tip.kwargs["geometry"] == "+110+228"
    assert tooltip.tip.children  # the label


def test_show_is_idempotent_while_visible():
    tooltip, _ = make_tooltip()
    tooltip._show()
    tip = tooltip.tip
    tooltip._show()
    assert tooltip.tip is tip


def test_show_swallows_tcl_errors(monkeypatch):
    tooltip, _ = make_tooltip()

    def boom(*args, **kwargs):
        raise tkinter.TclError("no display")

    monkeypatch.setattr(module.tk, "Toplevel", boom)
    tooltip._show()
    assert tooltip.tip is None


def test_hide_cancels_and_destroys_tip():
    tooltip, widget = make_tooltip()
    widget.after = MagicMock(return_value="job")
    widget.after_cancel = MagicMock()
    tooltip._schedule()
    tooltip._show()
    tip = tooltip.tip

    tooltip._hide()

    assert tip._destroyed is True
    assert tooltip.tip is None
    assert tooltip._after is None


def test_hide_swallows_destroy_errors():
    tooltip, _ = make_tooltip()
    tooltip._show()

    def boom():
        raise tkinter.TclError("gone")

    tooltip.tip.destroy = boom
    tooltip._hide()
    assert tooltip.tip is None
