"""ScanDialog — modal progress dialog for background folder scans.

Owned by View (self.scan_dialog); driven by the controller on the UI
thread only. Thin show_scan_* wrappers stay on View so the controller
API does not change.
"""

from __future__ import annotations

import customtkinter as ctk
from loguru import logger


class ScanDialog:
    """Small determinate progress dialog. At most one instance is open."""

    def __init__(self, master) -> None:
        self._master = master
        self._dialog: ctk.CTkToplevel | None = None
        self._bar: ctk.CTkProgressBar | None = None

    def show_started(self) -> None:
        """Open the dialog (closing any stale one first)."""
        self.show_finished()
        top = ctk.CTkToplevel(self._master)
        top.title("Scanning music")
        top.geometry("320x140")
        top.transient(self._master)
        top.grab_set()
        ctk.CTkLabel(top, text="Scanning folder…").pack(pady=(20, 10), padx=20)
        bar = ctk.CTkProgressBar(top, width=260)
        bar.set(0)
        bar.pack(pady=5, padx=20)
        self._dialog = top
        self._bar = bar

    def show_progress(self, done: int, total: int) -> None:
        """Update the determinate bar (no-op without an open dialog)."""
        if self._dialog is None or not self._dialog.winfo_exists():
            return
        fraction = (done / total) if total > 0 else 0.0
        assert self._bar is not None
        self._bar.set(max(0.0, min(1.0, fraction)))
        self._dialog.title(f"Scanning music — {done}/{total}")

    def show_finished(self) -> None:
        """Close the progress dialog if open."""
        if self._dialog is not None:
            try:
                if self._dialog.winfo_exists():
                    self._dialog.destroy()
            except Exception as e:
                logger.debug(f"Scan dialog close failed (ignored): {e}")
            self._dialog = None
            self._bar = None

    def show_failed(self, message: str) -> None:
        """Close the dialog and surface the error."""
        from tkinter import messagebox

        self.show_finished()
        messagebox.showerror("Scan failed", message)
