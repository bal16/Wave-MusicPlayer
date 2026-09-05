"""Fase 2 (F3 Play) tests: PlayerService, backend factory, controller wiring.

GUI-free — the service is tested against an in-memory FakeBackend, never
real audio. The VLC/miniaudio backends are covered by the manual smoke
checklist (docs/smoke-fase2.md).
"""

import pytest

from app.container import create_player_backend
from controllers.main_controller import TICK_MS, MainController
from domain.entities import Song
from domain.interfaces import BackendUnavailableError, PlayerBackend
from services.player_service import (
    STATE_CHANGED_EVENT,
    TRACK_CHANGED_EVENT,
    PlayerService,
)


def _song(song_id, **kw):
    base = {
        "id": song_id,
        "title": f"Title {song_id}",
        "artist": "Artist",
        "album": "Album",
        "file_path": f"/music/{song_id}.mp3",
        "duration": 200.0,
    }
    base.update(kw)
    return Song(**base)


class FakeBackend(PlayerBackend):
    """In-memory PlayerBackend: no audio, deterministic behavior."""

    def __init__(self, durations=None):
        self.loaded = None
        self.playing = False
        self.pos = 0.0
        self.durations = durations or {}
        self.volume = 1.0
        self.end_callback = None

    def load(self, file_path):
        self.loaded = file_path
        self.pos = 0.0

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False
        self.pos = 0.0

    def seek(self, seconds):
        self.pos = max(0.0, seconds)

    def set_volume(self, level):
        self.volume = max(0.0, min(1.0, level))

    def get_pos(self):
        return self.pos

    def get_duration(self):
        return self.durations.get(self.loaded, 0.0)

    def is_playing(self):
        return self.playing

    def on_end(self, callback):
        self.end_callback = callback

    def simulate_end(self):
        self.playing = False
        self.end_callback()


def _service(n=3, **kw):
    backend = FakeBackend(**kw)
    return PlayerService(backend), backend


# -- PlayerService --


def test_play_queue_starts_at_index():
    service, backend = _service()
    songs = [_song(1), _song(2), _song(3)]
    current = service.play_queue(songs, 1)
    assert current.id == 2
    assert backend.loaded == "/music/2.mp3"
    assert service.is_playing is True


def test_play_queue_empty_is_noop():
    service, _ = _service()
    assert service.play_queue([]) is None
    assert service.current is None


def test_next_prev_wrap_around():
    service, _ = _service()
    songs = [_song(1), _song(2)]
    service.play_queue(songs, 1)
    assert service.next().id == 1  # wraps to first
    assert service.prev().id == 2  # wraps to last


def test_prev_restarts_when_well_into_song():
    service, backend = _service()
    service.play_queue([_song(1), _song(2)], 1)
    backend.pos = 10.0
    assert service.prev().id == 2  # restarts instead of stepping back
    assert backend.pos == 0.0


def test_play_pause_toggles():
    service, _ = _service()
    assert service.play_pause() is False  # empty queue
    service.play_queue([_song(1)])
    assert service.play_pause() is False  # was playing -> paused
    assert service.play_pause() is True


def test_seek_clamps_to_duration():
    backend_durations = {"/music/1.mp3": 200.0}
    service, backend = _service(durations=backend_durations)
    service.play_queue([_song(1)])
    assert service.seek(9999) == 200.0
    assert backend.pos == 200.0
    assert service.seek(-5) == 0.0


def test_volume_and_mute():
    service, backend = _service()
    service.play_queue([_song(1)])
    assert service.set_volume(0.5) == 0.5
    assert backend.volume == 0.5
    assert service.toggle_mute() is True
    assert backend.volume == 0.0
    assert service.volume == 0.0
    assert service.toggle_mute() is False
    assert backend.volume == 0.5  # restored


def test_auto_next_wraps_on_media_end():
    service, backend = _service()
    service.play_queue([_song(1), _song(2)], 1)
    backend.simulate_end()
    assert service.current.id == 1  # wrapped
    assert backend.loaded == "/music/1.mp3"


def test_listeners_receive_track_and_state():
    service, _ = _service()
    events = []

    def on_track(song=None, **kw):
        events.append(("track", song.id))

    def on_state(playing=False, **kw):
        events.append(("state", playing))

    service.subscribe(TRACK_CHANGED_EVENT, on_track)
    service.subscribe(STATE_CHANGED_EVENT, on_state)
    service.play_queue([_song(7)])
    assert ("track", 7) in events
    assert ("state", True) in events


def test_duration_falls_back_to_song_metadata():
    service, _ = _service()  # backend knows no durations
    service.play_queue([_song(1, duration=225.0)])
    assert service.get_duration() == 225.0


# -- Probes --


def test_probe_reports_subprocess_outcome():
    from infrastructure.probe import probe_in_subprocess, run_probe

    assert probe_in_subprocess("pass") is True
    assert probe_in_subprocess("raise SystemExit(1)") is False
    assert run_probe("print('3.0.20')") == (0, "3.0.20")
    assert run_probe("raise SystemExit(2)")[0] == 2


# -- Factory --


def test_factory_prefers_vlc(monkeypatch):
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setattr(vlcmod, "is_available", lambda: True)
    seen = []
    monkeypatch.setattr(vlcmod, "VlcBackend", lambda: seen.append("vlc") or FakeBackend())
    name, backend = create_player_backend()
    assert name == "vlc"
    assert seen == ["vlc"]
    assert isinstance(backend, FakeBackend)


def test_factory_falls_back_to_miniaudio(monkeypatch):
    import infrastructure.player_miniaudio as mini
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setattr(vlcmod, "is_available", lambda: False)
    monkeypatch.setattr(mini, "is_available", lambda: True)
    monkeypatch.setattr(mini, "MiniaudioBackend", FakeBackend)
    name, backend = create_player_backend()
    assert name == "miniaudio"
    assert isinstance(backend, FakeBackend)


def test_factory_raises_when_nothing_available(monkeypatch):
    import infrastructure.player_miniaudio as mini
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setattr(vlcmod, "is_available", lambda: False)
    monkeypatch.setattr(mini, "is_available", lambda: False)
    with pytest.raises(BackendUnavailableError):
        create_player_backend()


def test_factory_env_forces_miniaudio(monkeypatch):
    import infrastructure.player_miniaudio as mini
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "miniaudio")
    monkeypatch.setattr(vlcmod, "is_available", lambda: True)

    def no_vlc():
        raise AssertionError("must not construct VLC")

    monkeypatch.setattr(vlcmod, "VlcBackend", no_vlc)
    monkeypatch.setattr(mini, "is_available", lambda: True)
    monkeypatch.setattr(mini, "MiniaudioBackend", FakeBackend)
    name, backend = create_player_backend()
    assert name == "miniaudio"
    assert isinstance(backend, FakeBackend)


def test_factory_env_vlc_unavailable_falls_back(monkeypatch):
    import infrastructure.player_miniaudio as mini
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "vlc")
    monkeypatch.setattr(vlcmod, "is_available", lambda: False)
    monkeypatch.setattr(mini, "is_available", lambda: True)
    monkeypatch.setattr(mini, "MiniaudioBackend", FakeBackend)
    name, _ = create_player_backend()
    assert name == "miniaudio"


def test_factory_env_unknown_uses_auto(monkeypatch):
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "bogus")
    monkeypatch.setattr(vlcmod, "is_available", lambda: True)
    monkeypatch.setattr(vlcmod, "VlcBackend", FakeBackend)
    name, _ = create_player_backend()
    assert name == "vlc"


# -- Controller wiring --


class FakeLibrary:
    def __init__(self, songs=None):
        self.songs = songs or []
        self.subscribers = []

    def subscribe(self, listener):
        self.subscribers.append(listener)

    def list_songs(self, query="", favorites_only=False):
        return list(self.songs)

    def get_song(self, song_id):
        return next((s for s in self.songs if s.id == song_id), None)

    def toggle_favorite(self, song_id):
        return True


class FakePlaylistsNoop:
    def subscribe(self, listener):
        pass


class FakePlayerView:
    """Fake view with player-bar display API (no Tk)."""

    def __init__(self):
        self.tracks = []
        self.progress = []
        self.playing_states = []
        self.muted_states = []
        self.scheduled = []
        self.shown = []

    def show_songs(self, songs):
        self.shown.append(list(songs))

    def show_track(self, song):
        self.tracks.append(song.id)

    def set_progress(self, sec, total):
        self.progress.append((sec, total))

    def set_playing(self, playing):
        self.playing_states.append(playing)

    def set_muted(self, muted):
        self.muted_states.append(muted)

    def after(self, ms, func, *args):
        self.scheduled.append((ms, func, args))
        return "after-id"


def _controller(n=3):
    songs = [_song(i) for i in range(1, n + 1)]
    backend = FakeBackend({s.file_path: 200.0 for s in songs})
    player = PlayerService(backend)
    view = FakePlayerView()
    controller = MainController(
        view=view, library=FakeLibrary(songs), player=player, playlists=FakePlaylistsNoop()
    )
    return controller, view, backend


def _take_scheduled(view, ms):
    """Pop the first scheduled callback with the given delay."""
    for i, (each_ms, _func, _args) in enumerate(view.scheduled):
        if each_ms == ms:
            return view.scheduled.pop(i)
    raise AssertionError(f"No scheduled callback with delay {ms}")


def test_select_queues_full_library_at_clicked_index():
    controller, view, backend = _controller()
    controller.handle_select_song(2)
    assert backend.loaded == "/music/2.mp3"
    assert view.tracks == [2]


def test_tick_pushes_progress_and_stops_when_paused():
    controller, view, backend = _controller()
    controller.handle_select_song(1)

    _, tick, _ = _take_scheduled(view, TICK_MS)
    backend.pos = 5.0
    tick()
    assert view.progress[-1] == (5.0, 200.0)

    backend.playing = False  # paused: ticker stands down
    scheduled_before = len(view.scheduled)
    tick()
    assert len(view.scheduled) == scheduled_before


def test_tick_skips_progress_while_seeking():
    controller, view, backend = _controller()
    controller.handle_select_song(1)
    controller.seeking = True
    _, tick, _ = _take_scheduled(view, TICK_MS)
    tick()
    assert view.progress == []


def test_track_change_marshals_through_after():
    controller, view, backend = _controller()
    controller.handle_select_song(1)
    view.tracks.clear()
    view.scheduled.clear()
    backend.simulate_end()  # auto-next fires on the (fake) audio thread
    assert view.tracks == []  # not touched directly...
    # ...but exactly one UI update was scheduled.
    ms, func, args = _take_scheduled(view, 0)
    assert ms == 0
    func(*args)
    assert view.tracks == [2]  # wrapped queue: 1 -> 2


def test_mute_updates_view():
    controller, view, _ = _controller()
    controller.handle_select_song(1)
    controller.handle_mute()
    assert view.muted_states == [True]


def test_service_shutdown_stops_and_clears():
    service, _ = _service()
    states = []
    service.subscribe(STATE_CHANGED_EVENT, lambda playing=False, **kw: states.append(playing))
    service.play_queue([_song(1)])
    service.shutdown()
    assert service.current is None
    assert states[-1] is False


def test_controller_shutdown_releases_and_destroys():
    class ShutdownPlayer:
        def __init__(self):
            self.shutdowns = 0

        def subscribe(self, event, listener):
            pass

        def shutdown(self):
            self.shutdowns += 1

    class DestroyView(FakePlayerView):
        def __init__(self):
            super().__init__()
            self.destroyed = False

        def destroy(self):
            self.destroyed = True

    view, player = DestroyView(), ShutdownPlayer()
    controller = MainController(
        view=view, library=FakeLibrary(), player=player, playlists=FakePlaylistsNoop()
    )
    controller.shutdown()
    assert player.shutdowns == 1
    assert view.destroyed is True
