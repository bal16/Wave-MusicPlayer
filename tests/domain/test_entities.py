"""Unit tests for domain/entities.py."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC

import pytest

from domain.entities import Playlist, Song, SongDraft, _utcnow


def test_utcnow_is_timezone_aware_utc():
    now = _utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_song_draft_defaults():
    draft = SongDraft(title="Song")
    assert draft.title == "Song"
    assert draft.artist == "Unknown Artist"
    assert draft.album == "Unknown Album"
    assert draft.file_path == ""
    assert draft.duration == 0.0


def test_song_defaults():
    song = Song(id=1, title="Song")
    assert song.id == 1
    assert song.artist == "Unknown Artist"
    assert song.album == "Unknown Album"
    assert song.file_path == ""
    assert song.duration == 0.0
    assert song.is_favorite is False
    assert song.added_at.tzinfo is not None


def test_playlist_defaults():
    playlist = Playlist(id=1, name="Mix")
    assert playlist.description == ""
    assert playlist.song_count == 0
    assert playlist.created_at.tzinfo is not None


@pytest.mark.parametrize(
    "entity", [SongDraft(title="x"), Song(id=1, title="x"), Playlist(id=1, name="x")]
)
def test_entities_are_frozen(entity):
    with pytest.raises(FrozenInstanceError):
        entity.title = "changed"  # type: ignore[misc]


def test_entities_compare_by_value():
    from datetime import UTC, datetime

    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    assert Song(id=1, title="A", added_at=stamp) == Song(id=1, title="A", added_at=stamp)
    assert Song(id=1, title="A", added_at=stamp) != Song(id=2, title="A", added_at=stamp)
