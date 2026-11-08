"""Unit tests for views/widgets/scan_dialog.py (Tk faked)."""

from __future__ import annotations

import tkinter

from tests.support import fake_tk
from views.widgets.scan_dialog import ScanDialog


def make_dialog():
    return ScanDialog(fake_tk.FakeWidget())


def test_show_started_creates_dialog_and_bar():
    dialog = make_dialog()
    dialog.show_started()
    assert dialog._dialog is not None
    assert dialog._bar is not None
    assert dialog._bar.get() == 0
    assert dialog._dialog.kwargs["title"] == "Scanning music"
    assert dialog._dialog.kwargs["geometry"] == "320x140"
    assert dialog._dialog.kwargs["grab_set"] is True


def test_show_started_closes_stale_dialog():
    dialog = make_dialog()
    dialog.show_started()
    first = dialog._dialog
    dialog.show_started()
    assert first._destroyed is True
    assert dialog._dialog is not first


def test_show_progress_without_dialog_is_noop():
    make_dialog().show_progress(1, 2)


def test_show_progress_updates_bar_and_title():
    dialog = make_dialog()
    dialog.show_started()
    dialog.show_progress(1, 4)
    assert dialog._bar.get() == 0.25
    assert dialog._dialog.kwargs["title"] == "Scanning music — 1/4"


def test_show_progress_clamps_fraction():
    dialog = make_dialog()
    dialog.show_started()
    dialog.show_progress(9, 4)
    assert dialog._bar.get() == 1.0
    dialog.show_progress(-1, 4)
    assert dialog._bar.get() == 0.0


def test_show_progress_zero_total():
    dialog = make_dialog()
    dialog.show_started()
    dialog.show_progress(5, 0)
    assert dialog._bar.get() == 0.0


def test_show_progress_ignores_destroyed_dialog():
    dialog = make_dialog()
    dialog.show_started()
    dialog._dialog.destroy()
    dialog.show_progress(1, 2)  # must not raise


def test_show_finished_closes_and_clears():
    dialog = make_dialog()
    dialog.show_started()
    top = dialog._dialog
    dialog.show_finished()
    assert top._destroyed is True
    assert dialog._dialog is None
    assert dialog._bar is None


def test_show_finished_is_idempotent():
    dialog = make_dialog()
    dialog.show_finished()
    dialog.show_finished()


def test_show_finished_swallows_close_errors():
    dialog = make_dialog()
    dialog.show_started()

    def boom():
        raise RuntimeError("tcl gone")

    dialog._dialog.destroy = boom
    dialog.show_finished()
    assert dialog._dialog is None


def test_show_failed_closes_and_shows_error():
    dialog = make_dialog()
    dialog.show_started()
    top = dialog._dialog
    dialog.show_failed("disk gone")
    assert top._destroyed is True
    assert dialog._dialog is None
    assert tkinter.messagebox.errors
    assert tkinter.messagebox.errors[-1][0] == ("Scan failed", "disk gone")
