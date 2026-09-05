"""Fase 4 (Polish) tests: threaded scan, progress, guards, lazy icons.

GUI-free — threads are exercised with fakes; Tk widgets are never built.
"""

import threading
import time

from controllers.main_controller import MainController
from services.library_service import LibraryService


class FakeRepo:
    def __init__(self):
        self.drafts = []

    def add_all(self, drafts):
        self.drafts.extend(drafts)
        return len(drafts)

    def list_all(self, query="", favorites_only=False):
        return []

    def get_by_id(self, song_id):
        return None

    def toggle_favorite(self, song_id):
        return True


class FakeTagger:
    def read(self, path):
        from domain.entities import SongDraft

        return SongDraft(title="t", file_path=path)


class FakeView:
    """Records scan-dialog calls and after() scheduling (no Tk)."""

    def __init__(self):
        self.started = 0
        self.progress_calls = []
        self.finished = 0
        self.failures = []
        self.scheduled = []

    def show_scan_started(self):
        self.started += 1

    def show_scan_progress(self, done, total):
        self.progress_calls.append((done, total))

    def show_scan_finished(self):
        self.finished += 1

    def show_scan_failed(self, message):
        self.failures.append(message)

    def show_songs(self, songs):
        pass

    def after(self, ms, func, *args):
        self.scheduled.append((ms, func, args))
        return "after-id"

    def run_scheduled(self):
        pending, self.scheduled = self.scheduled, []
        for _, func, args in pending:
            func(*args)


class FakePlayer:
    def subscribe(self, event, listener):
        pass


class FakePlaylists:
    def subscribe(self, listener):
        pass


def _service(**kw):
    return LibraryService(FakeRepo(), tagger=FakeTagger(), **kw)


def _controller(library=None):
    view = FakeView()
    controller = MainController(
        view=view,
        library=library or _service(),
        player=FakePlayer(),
        playlists=FakePlaylists(),
    )
    return controller, view


# -- Service progress --


def test_scan_reports_determinate_progress(tmp_path):
    for name in ["a.mp3", "b.flac", "c.txt"]:
        (tmp_path / name).write_bytes(b"x")
    seen = []
    service = _service()
    assert service.scan_folder(str(tmp_path), progress=lambda d, t: seen.append((d, t))) == 3
    assert [d for d, _ in seen] == [1, 2, 3]
    assert {t for _, t in seen} == {3}


def test_scan_empty_folder_reports_nothing(tmp_path):
    seen = []
    service = _service()
    assert service.scan_folder(str(tmp_path), progress=lambda d, t: seen.append((d, t))) == 0
    assert seen == []


# -- Controller threading --


def test_second_scan_while_running_is_ignored():
    controller, view = _controller()
    controller._scanning = True
    controller.handle_add_folder("/music")
    assert view.started == 0


def test_background_scan_runs_off_thread_and_finishes(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"x")
    controller, view = _controller()
    controller.handle_add_folder(str(tmp_path))
    assert view.started == 1

    deadline = time.time() + 10
    while controller._scanning and time.time() < deadline:
        time.sleep(0.05)
    assert not controller._scanning
    assert threading.current_thread() is threading.main_thread()
    view.run_scheduled()  # drain progress + finish callbacks on the fake UI loop
    assert view.finished == 1
    assert view.progress_calls[-1] == (1, 1)


def test_background_scan_failure_surfaces(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"x")

    class BoomRepo(FakeRepo):
        def add_all(self, drafts):
            raise RuntimeError("disk gone")

    service = _service()
    service._repo = BoomRepo()
    controller, view = _controller(library=service)
    controller._scan_in_background(str(tmp_path))
    assert controller._scanning is False
    view.run_scheduled()
    assert view.failures == ["disk gone"]
    assert view.finished == 1


# -- Lazy icons --


def test_config_import_loads_no_images():
    import config

    assert not hasattr(config, "ICON_LOGO")
    assert config.COLOR_ACCENT == "#2ccae6"
    assert config.FONT_SANS_SERIF == "Arial"
