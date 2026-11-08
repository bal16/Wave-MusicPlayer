"""Headless fakes for Tkinter / CustomTkinter.

Third-party GUI toolkits are battle-tested upstream; our tests only need to
verify how *our* widgets call them. These fakes record every configure /
bind / pack call so view unit tests run without a display (no Xvfb, no
Tcl interpreter, no flakiness).

Install them before importing any ``views`` module::

    from tests.support import fake_tk
    fake_tk.install()
"""

from __future__ import annotations

import sys
import types
from typing import Any


class FakeTclError(Exception):
    """Stand-in for tkinter.TclError."""


class FakeEvent:
    """Minimal event object passed to bound callbacks."""

    def __init__(self, widget: Any = None, keysym: str = "", **kwargs: Any) -> None:
        self.widget = widget
        self.keysym = keysym
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeCanvas:
    """Minimal canvas used by CTkScrollableFrame fakes."""

    def __init__(self) -> None:
        self.scroll_calls: list[tuple[int | float, str]] = []
        self.moveto_calls: list[float] = []
        self._view: tuple[float, float] = (0.0, 1.0)

    def set_view(self, first: float, last: float) -> None:
        self._view = (first, last)

    def yview(self) -> tuple[float, float]:
        return self._view

    def yview_scroll(self, amount: int | float, what: str) -> None:
        self.scroll_calls.append((amount, what))

    def yview_moveto(self, fraction: float) -> None:
        self.moveto_calls.append(fraction)


class FakeWidget:
    """Record-and-replay Tk widget.

    Every mutating Tk call is stored on ``kwargs``/``children``/``bindings``
    so tests can assert on behaviour without a real display.
    """

    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        self.master = master
        self.kwargs = dict(kwargs)
        self.children: list[FakeWidget] = []
        self.bindings: dict[str, list[Any]] = {}
        self.text = kwargs.get("text", "")
        self.image = kwargs.get("image")
        self._destroyed = False
        self._mapped = True
        self._after_counter = 0
        self._after_jobs: list[tuple[int, int, Any, tuple]] = []
        if master is not None and hasattr(master, "children"):
            master.children.append(self)

    # -- configuration --
    def configure(self, **kwargs: Any) -> None:
        self.kwargs.update(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "image" in kwargs:
            self.image = kwargs["image"]

    config = configure

    def cget(self, key: str) -> Any:
        return self.kwargs.get(key)

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    # -- geometry managers --
    def pack(self, **kwargs: Any) -> None:
        self.kwargs["pack"] = kwargs
        self._mapped = True

    def pack_forget(self) -> None:
        self._mapped = False

    def grid(self, **kwargs: Any) -> None:
        self.kwargs["grid"] = kwargs
        self._mapped = True

    def grid_remove(self) -> None:
        self._mapped = False

    def grid_forget(self) -> None:
        self.grid_remove()

    def place(self, **kwargs: Any) -> None:
        self.kwargs["place"] = kwargs

    def grid_columnconfigure(self, column: int, **kwargs: Any) -> None:
        self.kwargs[f"column:{column}"] = kwargs

    def grid_rowconfigure(self, row: int, **kwargs: Any) -> None:
        self.kwargs[f"row:{row}"] = kwargs

    # -- lifecycle --
    def destroy(self) -> None:
        self._destroyed = True
        for child in list(self.children):
            child.destroy()

    def winfo_exists(self) -> bool:
        return not self._destroyed

    def winfo_ismapped(self) -> bool:
        return self._mapped and not self._destroyed

    def winfo_toplevel(self) -> FakeWidget:
        widget: FakeWidget = self
        while getattr(widget, "master", None) is not None:
            widget = widget.master
        return widget

    def winfo_screenwidth(self) -> int:
        return 1920

    def winfo_screenheight(self) -> int:
        return 1080

    def winfo_rootx(self) -> int:
        return 100

    def winfo_rooty(self) -> int:
        return 200

    def winfo_height(self) -> int:
        return 24

    # -- events --
    def bind(self, sequence: str | None = None, func: Any = None, add: Any = None) -> None:
        if sequence is not None:
            self.bindings.setdefault(sequence, []).append(func)

    def unbind(self, sequence: str | None = None) -> None:
        if sequence is not None:
            self.bindings.pop(sequence, None)

    def bind_all(self, sequence: str | None = None, func: Any = None, add: Any = None) -> None:
        self.bind(sequence, func, add)

    def emit(self, sequence: str, event: FakeEvent | None = None, **kwargs: Any) -> None:
        payload = event or FakeEvent(widget=self, **kwargs)
        for callback in list(self.bindings.get(sequence, [])):
            if callback is not None:
                callback(payload)

    def invoke(self) -> Any:
        """Run the widget's ``command`` callback (button click)."""
        command = self.kwargs.get("command")
        return command() if command is not None else None

    # -- timers --
    def after(self, ms: int, func: Any = None, *args: Any) -> int:
        self._after_counter += 1
        job_id = self._after_counter
        if func is not None:
            self._after_jobs.append((job_id, ms, func, args))
            # Run inline so chunked rendering and scheduling are deterministic.
            func(*args)
        return job_id

    def after_cancel(self, job_id: int) -> None:
        self._after_jobs = [job for job in self._after_jobs if job[0] != job_id]

    def update(self) -> None:
        pass

    def update_idletasks(self) -> None:
        pass

    def mainloop(self) -> None:
        self.kwargs["mainloop"] = True

    # -- window manager --
    def title(self, text: str | None = None) -> None:
        self.kwargs["title"] = text

    def geometry(self, spec: str | None = None) -> None:
        self.kwargs["geometry"] = spec

    def wm_geometry(self, spec: str | None = None) -> None:
        self.geometry(spec)

    def protocol(self, name: str, func: Any = None) -> None:
        self.kwargs[f"protocol:{name}"] = func

    def withdraw(self) -> None:
        self._mapped = False

    def deiconify(self) -> None:
        self._mapped = True

    def overrideredirect(self, flag: bool = True) -> None:
        self.kwargs["overrideredirect"] = flag

    def wm_overrideredirect(self, flag: bool = True) -> None:
        self.overrideredirect(flag)

    def attributes(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs["attributes"] = (args, kwargs)

    def transient(self, master: Any = None) -> None:
        self.kwargs["transient"] = master

    def grab_set(self) -> None:
        self.kwargs["grab_set"] = True

    def grab_release(self) -> None:
        self.kwargs["grab_release"] = True

    def wait_window(self, window: Any = None) -> None:
        self.kwargs["wait_window"] = window

    # -- value widgets --
    def set(self, value: Any) -> None:
        self.kwargs["value"] = value
        self.kwargs["_value"] = value

    def get(self) -> Any:
        return self.kwargs.get("_value", self.kwargs.get("value", 0))

    def insert(self, index: Any, text: str) -> None:
        self.kwargs["inserted"] = (index, text)
        self.text = text


class FakeEntry(FakeWidget):
    pass


class FakeText(FakeWidget):
    pass


class FakeToplevel(FakeWidget):
    pass


class FakeLabel(FakeWidget):
    pass


class FakeCTk(FakeWidget):
    pass


class FakeCTkFrame(FakeWidget):
    pass


class FakeCTkLabel(FakeWidget):
    pass


class FakeCTkButton(FakeWidget):
    pass


class FakeCTkSlider(FakeWidget):
    pass


class FakeCTkEntry(FakeWidget):
    pass


class FakeCTkTextbox(FakeWidget):
    pass


class FakeCTkToplevel(FakeWidget):
    pass


class FakeCTkProgressBar(FakeWidget):
    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.kwargs["_value"] = 0


class FakeScrollableFrame(FakeWidget):
    def __init__(self, master: Any = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._parent_frame = self
        self._parent_canvas = FakeCanvas()
        self._scrollbar = FakeWidget(self)


class FakeCTkImage:
    def __init__(self, light_image: Any = None, dark_image: Any = None, size: Any = None) -> None:
        self.light_image = light_image
        self.dark_image = dark_image
        self.size = size


class FakeVariable:
    def __init__(self, value: Any = None, master: Any = None) -> None:
        self._value = value

    def get(self) -> Any:
        return self._value

    def set(self, value: Any) -> None:
        self._value = value


class FakeInputDialog:
    """CTkInputDialog fake; set ``next_value`` per test."""

    next_value: str | None = None
    instances: list[FakeInputDialog] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._entry = FakeEntry()
        self._initial: str | None = None
        FakeInputDialog.instances.append(self)

    def get_input(self) -> str | None:
        return FakeInputDialog.next_value


class FakeMessagebox:
    def __init__(self) -> None:
        self.errors: list[tuple] = []

    def showerror(self, *args: Any, **kwargs: Any) -> None:
        self.errors.append((args, kwargs))


class FakeFiledialog:
    def __init__(self) -> None:
        self.askdirectory_result: str = ""
        self.askdirectory_calls = 0

    def askdirectory(self, *args: Any, **kwargs: Any) -> str:
        self.askdirectory_calls += 1
        return self.askdirectory_result


# Shared module-level recorders used by assertions.
appearance_modes: list[str] = []
color_themes: list[str] = []


def _make_customtkinter() -> types.ModuleType:
    module = types.ModuleType("customtkinter")
    module.CTk = FakeCTk
    module.CTkToplevel = FakeCTkToplevel
    module.CTkFrame = FakeCTkFrame
    module.CTkLabel = FakeCTkLabel
    module.CTkButton = FakeCTkButton
    module.CTkSlider = FakeCTkSlider
    module.CTkScrollableFrame = FakeScrollableFrame
    module.CTkProgressBar = FakeCTkProgressBar
    module.CTkInputDialog = FakeInputDialog
    module.CTkEntry = FakeCTkEntry
    module.CTkTextbox = FakeCTkTextbox
    module.CTkImage = FakeCTkImage
    module.StringVar = FakeVariable
    module.BooleanVar = FakeVariable
    module.IntVar = FakeVariable
    module.set_appearance_mode = appearance_modes.append
    module.set_default_color_theme = color_themes.append

    filedialog = FakeFiledialog()
    module.filedialog = filedialog
    module.messagebox = FakeMessagebox()
    module._filedialog = filedialog
    return module


def _make_tkinter() -> types.ModuleType:
    module = types.ModuleType("tkinter")
    module.TclError = FakeTclError
    module.Event = FakeEvent
    module.Toplevel = FakeToplevel
    module.Label = FakeLabel
    module.Entry = FakeEntry
    module.Text = FakeText
    module.messagebox = FakeMessagebox()
    module.filedialog = FakeFiledialog()
    module._messagebox = module.messagebox
    return module


_installed = False


def install() -> None:
    """Force the fakes into ``sys.modules`` before view imports happen."""
    global _installed
    if _installed:
        return

    ctk = _make_customtkinter()
    tk = _make_tkinter()

    sys.modules["customtkinter"] = ctk
    sys.modules["tkinter"] = tk
    sys.modules["tkinter.messagebox"] = tk.messagebox
    sys.modules["tkinter.filedialog"] = tk.filedialog
    _installed = True


def reset() -> None:
    """Reset recorder state between tests."""
    appearance_modes.clear()
    color_themes.clear()
    FakeInputDialog.next_value = None
    FakeInputDialog.instances.clear()
    ctk = sys.modules.get("customtkinter")
    if ctk is not None:
        ctk.messagebox.errors.clear()
        ctk._filedialog.askdirectory_result = ""
        ctk._filedialog.askdirectory_calls = 0
    tk = sys.modules.get("tkinter")
    if tk is not None:
        tk.messagebox.errors.clear()
        tk.filedialog.askdirectory_result = ""
        tk.filedialog.askdirectory_calls = 0


def widget_by_text(root: FakeWidget, text: str) -> FakeWidget | None:
    """Depth-first search for a descendant widget whose ``text`` matches."""
    for child in root.children:
        if child.text == text or child.kwargs.get("text") == text:
            return child
        found = widget_by_text(child, text)
        if found is not None:
            return found
    return None
