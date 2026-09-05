"""Tagger + container + theme tests (all GUI-free, no display needed)."""

import os

from domain.entities import SongDraft
from infrastructure.audio_tagger import (
    SUPPORTED_AUDIO_EXTENSIONS,
    TinyTagAudioTagger,
    is_supported,
    normalize_path,
)
from views.theme import format_duration, theme


def test_supported_formats_locked_to_mp3_flac():
    assert SUPPORTED_AUDIO_EXTENSIONS == frozenset({".mp3", ".flac"})
    assert is_supported("song.MP3")
    assert is_supported("/x/y.flac")
    assert not is_supported("song.ogg")
    assert not is_supported("song.m4a")
    assert not is_supported("song.wav")


def test_normalize_path_is_absolute():
    assert os.path.isabs(normalize_path("rel/song.mp3"))


def test_tagger_rejects_unsupported_without_touching_tinytag(tmp_path):
    tagger = TinyTagAudioTagger()
    f = tmp_path / "song.ogg"
    f.write_bytes(b"x")
    assert tagger.read(str(f)) is None


def test_tagger_maps_metadata_with_fallbacks(tmp_path, monkeypatch):
    import infrastructure.audio_tagger as mod

    f = tmp_path / "real.mp3"
    f.write_bytes(b"x")

    class FakeTag:
        title = None
        artist = None
        album = "Some Album"
        duration = 185.7

    class FakeTinyTag:
        @staticmethod
        def get(path):
            assert path.endswith(".mp3")
            return FakeTag()

    monkeypatch.setattr(mod, "TinyTag", FakeTinyTag, raising=False)
    # Patch the local import reference used inside read().
    import tinytag

    monkeypatch.setattr(tinytag, "TinyTag", FakeTinyTag, raising=True)
    draft = TinyTagAudioTagger().read(str(f))
    assert isinstance(draft, SongDraft)
    assert draft.title == "real.mp3"  # basename fallback
    assert draft.artist == "Unknown Artist"
    assert draft.album == "Some Album"
    assert draft.duration == 185.7


def _dummy_backend():
    """Audio-free backend: PlayerService only needs on_end at construction."""

    class DummyBackend:
        def on_end(self, callback):
            self.end_callback = callback

    return DummyBackend()


def test_container_builds_without_view_or_tk(tmp_path):
    from sqlmodel import SQLModel, create_engine

    from app.container import build_container

    engine = create_engine(f"sqlite:///{tmp_path}/c.db")
    SQLModel.metadata.create_all(engine)
    container = build_container(view=None, engine=engine, backend=_dummy_backend())
    assert container.library is not None
    assert container.player is not None
    assert container.controller is None
    assert container.library.scan_folder("") == 0


def test_thin_controller_has_no_mainloop_side_effect(tmp_path):
    from sqlmodel import SQLModel, create_engine

    from app.container import build_container
    from controllers.main_controller import MainController

    engine = create_engine(f"sqlite:///{tmp_path}/m.db")
    SQLModel.metadata.create_all(engine)
    container = build_container(view=None, engine=engine, backend=_dummy_backend())

    class FakeView:
        def __init__(self):
            self.looped = False

        def mainloop(self):
            self.looped = True

    view = FakeView()
    controller = MainController(view=view, library=container.library, player=container.player)
    assert view.looped is False  # __init__ must not enter the loop
    controller.run()
    assert view.looped is True


def test_theme_tokens_and_duration_format():
    assert theme.colors.accent == "#2ccae6"
    assert theme.fonts.sans == "Arial"
    assert format_duration(225.9) == "3:45"
    assert format_duration(0) == "0:00"
