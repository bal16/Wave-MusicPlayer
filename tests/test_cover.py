"""Cover art tests: tagger bytes, service delegation, decode fallback.

GUI-free — decoding is tested without instantiating widgets (CTkImage
creation needs no display, widget layout is covered by manual smoke).
"""

import io

from domain.entities import Song
from services.library_service import LibraryService


def _song(song_id=1, path="/m/1.flac"):
    return Song(
        id=song_id,
        title="T",
        artist="A",
        album="B",
        file_path=path,
        duration=200.0,
    )


class FakeImage:
    def __init__(self, data):
        self.data = data


class FakeImages:
    def __init__(self, data):
        self.any = FakeImage(data) if data is not None else None


class FakeTinyTag:
    data = b"cover-bytes"
    fail = False

    @staticmethod
    def get(path, image=False):
        assert image is True
        if FakeTinyTag.fail:
            raise RuntimeError("unreadable")
        return type("Tag", (), {"images": FakeImages(FakeTinyTag.data)})()


def _png_bytes(color=(10, 20, 30), size=(32, 32)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_read_cover_returns_bytes(monkeypatch):
    import tinytag

    from infrastructure.audio_tagger import TinyTagAudioTagger

    monkeypatch.setattr(tinytag, "TinyTag", FakeTinyTag)
    FakeTinyTag.fail = False
    assert TinyTagAudioTagger().read_cover("/m/1.flac") == b"cover-bytes"


def test_read_cover_none_paths(monkeypatch, tmp_path):
    import tinytag

    from infrastructure.audio_tagger import TinyTagAudioTagger

    monkeypatch.setattr(tinytag, "TinyTag", FakeTinyTag)
    tagger = TinyTagAudioTagger()
    assert tagger.read_cover("/m/song.ogg") is None  # unsupported format
    FakeTinyTag.fail = True
    assert tagger.read_cover("/m/1.flac") is None  # read error
    FakeTinyTag.fail = False


class FakeRepo:
    def __init__(self, songs=None):
        self.songs = {s.id: s for s in (songs or [])}

    def get_by_id(self, song_id):
        return self.songs.get(song_id)


class FakeReader:
    def __init__(self, data=b"img"):
        self.data = data
        self.paths = []

    def read(self, path):
        raise AssertionError("not under test")

    def read_cover(self, path):
        self.paths.append(path)
        return self.data


class PlainTagger:
    """Metadata-only tagger without cover support."""

    def read(self, path):
        raise AssertionError("not under test")


def test_service_get_cover_delegates():
    service = LibraryService(FakeRepo([_song()]), tagger=FakeReader())
    assert service.get_cover(1) == b"img"
    assert service.get_cover(999) is None


def test_service_get_cover_without_reader_support():
    service = LibraryService(FakeRepo([_song()]), tagger=PlainTagger())
    assert service.get_cover(1) is None


def test_decode_cover_valid_and_garbage():
    from components.PlayerBar import PlayerBar

    assert PlayerBar._decode_cover(_png_bytes()) is not None
    assert PlayerBar._decode_cover(b"not-an-image") is None
