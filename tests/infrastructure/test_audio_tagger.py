"""Unit tests for infrastructure/audio_tagger.py (TinyTag mocked)."""

from __future__ import annotations

import os

import pytest
import tinytag

from infrastructure import audio_tagger
from infrastructure.audio_tagger import (
    SUPPORTED_AUDIO_EXTENSIONS,
    TinyTagAudioTagger,
    is_supported,
    normalize_path,
)


class FakeImage:
    def __init__(self, data):
        self.data = data


class FakeImages:
    def __init__(self, data):
        self.any = FakeImage(data) if data is not None else None


def _tag(**overrides):
    values = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "duration": 185.7,
        "images": FakeImages(b"cover"),
    }
    values.update(overrides)
    return type("Tag", (), values)()


@pytest.fixture()
def fake_tinytag(monkeypatch):
    class FakeTinyTag:
        calls: list[tuple] = []
        result = _tag()
        error: Exception | None = None

        @classmethod
        def get(cls, path, image=False):
            cls.calls.append((path, image))
            if cls.error is not None:
                raise cls.error
            return cls.result

    FakeTinyTag.calls = []
    monkeypatch.setattr(tinytag, "TinyTag", FakeTinyTag)
    return FakeTinyTag


def test_supported_formats_locked_to_mp3_flac():
    assert SUPPORTED_AUDIO_EXTENSIONS == frozenset({".mp3", ".flac"})


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("song.mp3", True),
        ("song.MP3", True),
        ("/x/y.flac", True),
        ("song.ogg", False),
        ("song.m4a", False),
        ("song.wav", False),
        ("song", False),
    ],
)
def test_is_supported(path, expected):
    assert is_supported(path) is expected


def test_normalize_path_is_absolute_and_normalized():
    assert os.path.isabs(normalize_path("rel/song.mp3"))
    assert normalize_path("a/./b/../song.mp3") == os.path.abspath("a/song.mp3")


def test_read_rejects_unsupported_without_touching_tinytag(fake_tinytag):
    assert TinyTagAudioTagger().read("song.ogg") is None
    assert fake_tinytag.calls == []


def test_read_maps_metadata(fake_tinytag):
    draft = TinyTagAudioTagger().read("/music/song.mp3")
    assert draft.title == "Title"
    assert draft.artist == "Artist"
    assert draft.album == "Album"
    assert draft.duration == 185.7
    assert draft.file_path == os.path.abspath("/music/song.mp3")
    assert fake_tinytag.calls == [(os.path.abspath("/music/song.mp3"), False)]


def test_read_falls_back_for_missing_metadata(fake_tinytag):
    fake_tinytag.result = _tag(title=None, artist=None, album=None, duration=None)
    draft = TinyTagAudioTagger().read("/music/real.mp3")
    assert draft.title == "real.mp3"
    assert draft.artist == "Unknown Artist"
    assert draft.album == "Unknown Album"
    assert draft.duration == 0.0


def test_read_returns_none_on_tagger_error(fake_tinytag):
    fake_tinytag.error = RuntimeError("corrupt")
    assert TinyTagAudioTagger().read("/music/song.mp3") is None


def test_read_cover_returns_bytes(fake_tinytag):
    assert TinyTagAudioTagger().read_cover("/music/song.flac") == b"cover"
    assert fake_tinytag.calls == [(os.path.abspath("/music/song.flac"), True)]


def test_read_cover_returns_none_for_unsupported_format(fake_tinytag):
    assert TinyTagAudioTagger().read_cover("/music/song.ogg") is None
    assert fake_tinytag.calls == []


def test_read_cover_returns_none_when_no_embedded_art(fake_tinytag):
    fake_tinytag.result = _tag(images=FakeImages(None))
    assert TinyTagAudioTagger().read_cover("/music/song.mp3") is None


def test_read_cover_returns_none_on_tagger_error(fake_tinytag):
    fake_tinytag.error = RuntimeError("unreadable")
    assert TinyTagAudioTagger().read_cover("/music/song.mp3") is None


def test_module_exposes_supported_helper():
    assert audio_tagger.is_supported("x.flac") is True
