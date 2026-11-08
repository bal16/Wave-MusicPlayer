"""Reusable in-memory doubles shared by service/controller/widget tests.

These are hand-written fakes rather than ``MagicMock`` because most tests
assert on state transitions, not only call counts. Third-party boundaries
(Tk, VLC, miniaudio, TinyTag) are mocked separately in their own tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.entities import Playlist, Song, SongDraft
from domain.interfaces import PlayerBackend


def make_song(song_id: int | None = 1, **kwargs) -> Song:
    base = {
        "id": song_id,
        "title": f"Title {song_id}",
        "artist": "Artist",
        "album": "Album",
        "file_path": f"/music/{song_id}.mp3",
        "duration": 200.0,
        "is_favorite": False,
        "added_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(kwargs)
    return Song(**base)


def make_playlist(playlist_id: int | None = 1, **kwargs) -> Playlist:
    base = {
        "id": playlist_id,
        "name": f"Playlist {playlist_id}",
        "description": "",
        "song_count": 0,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(kwargs)
    return Playlist(**base)


def make_draft(path: str, **kwargs) -> SongDraft:
    base = {
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "file_path": path,
        "duration": 200.0,
    }
    base.update(kwargs)
    return SongDraft(**base)


class FakeBackend(PlayerBackend):
    """Deterministic in-memory audio engine (never touches real audio)."""

    def __init__(self, durations: dict[str, float] | None = None) -> None:
        self.loaded: str | None = None
        self.playing = False
        self.pos = 0.0
        self.durations = durations or {}
        self.volume = 1.0
        self.end_callback = None
        self.load_calls: list[str] = []
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0
        self.close_calls = 0
        self.seek_calls: list[float] = []

    def load(self, file_path: str) -> None:
        self.loaded = file_path
        self.load_calls.append(file_path)
        self.pos = 0.0

    def play(self) -> None:
        self.playing = True
        self.play_calls += 1

    def pause(self) -> None:
        self.playing = False
        self.pause_calls += 1

    def stop(self) -> None:
        self.playing = False
        self.pos = 0.0
        self.stop_calls += 1

    def seek(self, seconds: float) -> None:
        self.pos = max(0.0, seconds)
        self.seek_calls.append(seconds)

    def set_volume(self, level: float) -> None:
        self.volume = max(0.0, min(1.0, level))

    def get_pos(self) -> float:
        return self.pos

    def get_duration(self) -> float:
        return self.durations.get(self.loaded, 0.0)

    def is_playing(self) -> bool:
        return self.playing

    def on_end(self, callback) -> None:
        self.end_callback = callback

    def close(self) -> None:
        self.close_calls += 1
        self.playing = False

    def simulate_end(self) -> None:
        self.playing = False
        self.end_callback()


class FakeLibrary:
    """Minimal LibraryService stand-in (records calls, replays songs)."""

    def __init__(self, songs: list[Song] | None = None, cover: bytes | None = None) -> None:
        self.songs = songs or []
        self.cover = cover
        self.subscribers: list = []
        self.scanned: list[tuple[str, object]] = []
        self.favorites: list[int] = []

    def subscribe(self, listener) -> None:
        self.subscribers.append(listener)

    def add_all(self, drafts) -> int:
        self.songs.extend(drafts)
        return len(drafts)

    def scan_folder(self, path, progress=None) -> int:
        self.scanned.append((path, progress))
        return 0

    def list_songs(self, query: str = "", favorites_only: bool = False) -> list[Song]:
        return list(self.songs)

    def get_song(self, song_id: int) -> Song | None:
        return next((s for s in self.songs if s.id == song_id), None)

    def get_cover(self, song_id: int) -> bytes | None:
        return self.cover

    def toggle_favorite(self, song_id: int) -> bool:
        self.favorites.append(song_id)
        return True


class FakePlayer:
    """Minimal PlayerService stand-in for controller tests."""

    def __init__(self) -> None:
        self.subscribers: dict[str, list] = {}
        self.current = None

    def subscribe(self, event: str, listener) -> None:
        self.subscribers.setdefault(event, []).append(listener)

    def play_queue(self, songs, index: int = 0):
        self.current = songs[index] if songs else None
        return self.current

    def play_pause(self) -> bool:
        return True

    def next(self):
        return None

    def prev(self):
        return None

    def seek(self, seconds: float) -> float:
        return seconds

    def get_duration(self) -> float:
        return 200.0

    def get_pos(self) -> float:
        return 0.0

    def set_volume(self, level: float) -> None:
        pass

    def toggle_mute(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    @property
    def is_playing(self) -> bool:
        return False


class FakePlaylists:
    """Minimal PlaylistService stand-in."""

    def __init__(self) -> None:
        self.subscribers: list = []
        self.created: list = []

    def subscribe(self, listener) -> None:
        self.subscribers.append(listener)

    def create_playlist(self, name: str, description: str = ""):
        playlist = make_playlist(len(self.created) + 1, name=name, description=description)
        self.created.append(playlist)
        return playlist

    def rename_playlist(self, playlist_id: int, name: str):
        return make_playlist(playlist_id, name=name)

    def delete_playlist(self, playlist_id: int) -> bool:
        return True

    def list_playlists(self) -> list:
        return list(self.created)

    def get_playlist(self, playlist_id: int):
        return next((p for p in self.created if p.id == playlist_id), None)

    def add_song(self, playlist_id: int, song_id: int) -> bool:
        return True

    def remove_song(self, playlist_id: int, song_id: int) -> bool:
        return True

    def songs_in_playlist(self, playlist_id: int) -> list:
        return []


class FakeView:
    """Records every view call a controller may make (no Tk)."""

    def __init__(self) -> None:
        self.shown: list[list[Song]] = []
        self.tracks: list[Song] = []
        self.progress: list[tuple[float, float]] = []
        self.playing_states: list[bool] = []
        self.muted_states: list[bool] = []
        self.scheduled: list[tuple[int, object, tuple]] = []
        self.playlists_shown: list[list[Playlist]] = []
        self.playlist_songs_shown: list[tuple[Playlist, list[Song]]] = []
        self.scan_started = 0
        self.scan_progress: list[tuple[int, int]] = []
        self.scan_finished = 0
        self.scan_failures: list[str] = []
        self.refreshed_rows: list[Song] = []
        self.refresh_current_calls = 0
        self.withdrawn = 0
        self.destroyed = 0

    # -- library / playlists --
    def show_songs(self, songs) -> None:
        self.shown.append(list(songs))

    def show_playlists(self, playlists) -> None:
        self.playlists_shown.append(list(playlists))

    def show_playlist_songs(self, playlist, songs) -> None:
        self.playlist_songs_shown.append((playlist, list(songs)))

    # -- player --
    def show_track(self, song) -> None:
        self.tracks.append(song)

    def set_progress(self, seconds: float, total: float) -> None:
        self.progress.append((seconds, total))

    def set_playing(self, playing: bool) -> None:
        self.playing_states.append(playing)

    def set_muted(self, muted: bool) -> None:
        self.muted_states.append(muted)

    def refresh_song_row(self, song) -> None:
        self.refreshed_rows.append(song)

    def refresh_current_view(self) -> None:
        self.refresh_current_calls += 1

    # -- scan dialog --
    def show_scan_started(self) -> None:
        self.scan_started += 1

    def show_scan_progress(self, done: int, total: int) -> None:
        self.scan_progress.append((done, total))

    def show_scan_finished(self) -> None:
        self.scan_finished += 1

    def show_scan_failed(self, message: str) -> None:
        self.scan_failures.append(message)

    # -- window plumbing --
    def after(self, ms: int, func, *args):
        self.scheduled.append((ms, func, args))
        return f"after-{len(self.scheduled)}"

    def withdraw(self) -> None:
        self.withdrawn += 1

    def destroy(self) -> None:
        self.destroyed += 1

    def mainloop(self) -> None:
        self.mainloop_called = True

    def run_scheduled(self) -> None:
        pending, self.scheduled = self.scheduled, []
        for _, func, args in pending:
            func(*args)
