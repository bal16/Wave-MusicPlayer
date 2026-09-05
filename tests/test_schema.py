"""Schema tests: Song / Playlist / PlaylistSongLink roundtrips.

Runs against an isolated SQLite file in tmp_path — never touches database.db.
GUI-free by design (see docs/architecture.md).
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from models.schema import Playlist, Song


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _song(**kw):
    base = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "file_path": "/music/song.flac",
        "duration": 225.5,
    }
    base.update(kw)
    return Song(**base)


def test_add_and_list_songs(session):
    session.add(_song(file_path="/music/a.flac", title="A"))
    session.add(_song(file_path="/music/b.flac", title="B"))
    session.commit()

    rows = session.exec(select(Song).order_by(Song.title)).all()
    assert [r.title for r in rows] == ["A", "B"]


def test_file_path_unique_enforces_dedup(session):
    session.add(_song(file_path="/music/dup.flac"))
    session.commit()

    session.add(_song(file_path="/music/dup.flac", title="Copy"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_defaults_for_unknown_metadata(session):
    song = Song(title="No Tags", file_path="/music/notag.flac")
    session.add(song)
    session.commit()
    session.refresh(song)

    assert song.artist == "Unknown Artist"
    assert song.album == "Unknown Album"
    assert song.duration == 0.0
    assert song.is_favorite is False
    assert song.added_at is not None


def test_playlist_song_link(session):
    song = _song()
    playlist = Playlist(name="Chill", description="Evening mix")
    playlist.songs.append(song)
    session.add(playlist)
    session.commit()

    loaded = session.exec(select(Playlist).where(Playlist.name == "Chill")).one()
    assert [s.file_path for s in loaded.songs] == ["/music/song.flac"]
