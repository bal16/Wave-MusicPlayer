"""Unit tests for infrastructure/player_vlc.py.

python-vlc/libvlc is mocked at the ``sys.modules`` boundary: the backend must
stay importable without native libvlc, which is exactly what these tests pin.
"""

from __future__ import annotations

import sys
import types

import pytest

from domain.interfaces import BackendUnavailableError
from infrastructure import player_vlc
from infrastructure.player_vlc import VlcBackend


class FakeEvents:
    def __init__(self) -> None:
        self.attached: list[tuple] = []

    def event_attach(self, event, callback) -> None:
        self.attached.append((event, callback))


class FakeMedia:
    def __init__(self, path: str) -> None:
        self.path = path
        self.parse_calls: list[tuple] = []
        self.duration_ms: int | None = 5000
        self.parse_error: Exception | None = None
        self.duration_error: Exception | None = None

    def parse_with_options(self, flag, timeout) -> None:
        self.parse_calls.append((flag, timeout))
        if self.parse_error is not None:
            raise self.parse_error

    def get_duration(self):
        if self.duration_error is not None:
            raise self.duration_error
        return self.duration_ms


class FakePlayer:
    def __init__(self) -> None:
        self.events = FakeEvents()
        self.event_manager_error: Exception | None = None
        self.media: FakeMedia | None = None
        self.playing = False
        self.time_ms = 0
        self.length_ms = 0
        self.volume = 100
        self.stop_error: Exception | None = None
        self.time_error: Exception | None = None
        self.length_error: Exception | None = None
        self.media_error: Exception | None = None
        self.release_error: Exception | None = None
        self.released = 0

    def event_manager(self):
        if self.event_manager_error is not None:
            raise self.event_manager_error
        return self.events

    def set_media(self, media) -> None:
        self.media = media

    def play(self) -> None:
        self.playing = True

    def set_pause(self, value) -> None:
        self.playing = not value

    def stop(self) -> None:
        if self.stop_error is not None:
            raise self.stop_error
        self.playing = False

    def set_time(self, ms) -> None:
        self.time_ms = ms

    def audio_set_volume(self, value) -> None:
        self.volume = value

    def get_time(self):
        if self.time_error is not None:
            raise self.time_error
        return self.time_ms

    def get_media(self):
        if self.media_error is not None:
            raise self.media_error
        return self.media

    def get_length(self):
        if self.length_error is not None:
            raise self.length_error
        return self.length_ms

    def is_playing(self) -> bool:
        return self.playing

    def release(self) -> None:
        self.released += 1
        if self.release_error is not None:
            raise self.release_error


class FakeInstance:
    def __init__(self) -> None:
        self.player = FakePlayer()
        self.medias: list[FakeMedia] = []
        self.released = 0
        self.release_error: Exception | None = None

    def media_player_new(self):
        return self.player

    def media_new(self, path):
        media = FakeMedia(path)
        self.medias.append(media)
        return media

    def release(self) -> None:
        self.released += 1
        if self.release_error is not None:
            raise self.release_error


class FakeEventType:
    MediaPlayerEndReached = "MediaPlayerEndReached"


class FakeParseFlag:
    local = 1


def make_vlc_module(*, instance_error: Exception | None = None):
    module = types.ModuleType("vlc")
    module.EventType = FakeEventType
    module.MediaParseFlag = FakeParseFlag
    module.instance = FakeInstance()

    def Instance(_args):
        if instance_error is not None:
            raise instance_error
        return module.instance

    module.Instance = Instance
    return module


@pytest.fixture()
def vlc(monkeypatch):
    module = make_vlc_module()
    monkeypatch.setitem(sys.modules, "vlc", module)
    return module


@pytest.fixture()
def backend(vlc):
    return VlcBackend()


# -- availability --


def test_is_available_false_without_python_vlc(monkeypatch):
    monkeypatch.setitem(sys.modules, "vlc", None)
    assert player_vlc.is_available() is False


def test_is_available_true_for_libvlc_3(monkeypatch, vlc):
    monkeypatch.setattr("infrastructure.probe.run_probe", lambda code: (0, "3.0.20"))
    assert player_vlc.is_available() is True


def test_is_available_false_when_probe_fails(monkeypatch, vlc):
    monkeypatch.setattr("infrastructure.probe.run_probe", lambda code: (1, ""))
    assert player_vlc.is_available() is False


def test_is_available_rejects_libvlc_4(monkeypatch, vlc):
    monkeypatch.setattr("infrastructure.probe.run_probe", lambda code: (0, "4.0.0-dev"))
    assert player_vlc.is_available() is False


# -- construction --


def test_construction_raises_without_python_vlc(monkeypatch):
    monkeypatch.setitem(sys.modules, "vlc", None)
    with pytest.raises(BackendUnavailableError, match="python-vlc"):
        VlcBackend()


def test_construction_raises_when_libvlc_cannot_start(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "vlc", make_vlc_module(instance_error=RuntimeError("no libvlc"))
    )
    with pytest.raises(BackendUnavailableError, match="libvlc"):
        VlcBackend()


def test_construction_attaches_end_event(backend, vlc):
    events = vlc.instance.player.events
    assert backend._use_events is True
    assert events.attached[0][0] == FakeEventType.MediaPlayerEndReached
    events.attached[0][1](None)
    # No end callback registered yet, so this is a safe no-op.


def test_construction_falls_back_to_polling_without_event_api(monkeypatch):
    module = make_vlc_module()
    module.instance.player.event_manager_error = RuntimeError("no events")
    monkeypatch.setitem(sys.modules, "vlc", module)
    backend = VlcBackend()
    assert backend._use_events is False


# -- end delivery --


def test_ensure_monitor_starts_one_daemon_thread(monkeypatch):
    started = []

    class FakeThread:
        def __init__(self, target, daemon):
            started.append((target, daemon))

        def start(self):
            started[-1] = (*started[-1], "started")

    monkeypatch.setattr(player_vlc.threading, "Thread", FakeThread)
    backend = VlcBackend.__new__(VlcBackend)
    backend._use_events = False
    backend._monitor_started = False
    backend._monitor_lock = player_vlc.threading.Lock()

    backend._ensure_monitor()
    backend._ensure_monitor()

    assert len(started) == 1
    assert started[0][1] is True
    assert started[0][2] == "started"


def test_ensure_monitor_noop_with_events(monkeypatch):
    started = []
    monkeypatch.setattr(player_vlc.threading, "Thread", lambda **kw: started.append(kw))
    backend = VlcBackend.__new__(VlcBackend)
    backend._use_events = True
    backend._monitor_started = False
    backend._monitor_lock = player_vlc.threading.Lock()
    backend._ensure_monitor()
    assert started == []


def _poll_backend(player, *, expecting=True, was_playing=True, paused=False):
    backend = VlcBackend.__new__(VlcBackend)
    backend._player = player
    backend._end_callback = None
    backend._paused_by_user = paused
    backend._expecting = expecting
    backend._was_playing = was_playing
    return backend


def test_poll_end_fires_on_natural_finish(monkeypatch, vlc):
    player = vlc.instance.player
    values = iter([True, False, RuntimeError("gone")])

    def is_playing():
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return value

    player.is_playing = is_playing
    player.time_ms = 5000
    player.length_ms = 5000
    backend = _poll_backend(player)
    calls = []
    backend._end_callback = lambda: calls.append(1)
    monkeypatch.setattr(player_vlc.time, "sleep", lambda _s: None)

    backend._poll_end()

    assert calls == [1]
    assert backend._expecting is False
    assert backend._was_playing is False


def test_poll_end_ignores_user_pause(monkeypatch, vlc):
    player = vlc.instance.player
    values = iter([True, False, RuntimeError("gone")])
    player.is_playing = lambda: _next_or_raise(values)
    player.time_ms = 5000
    player.length_ms = 5000
    backend = _poll_backend(player, paused=True)
    calls = []
    backend._end_callback = lambda: calls.append(1)
    monkeypatch.setattr(player_vlc.time, "sleep", lambda _s: None)

    backend._poll_end()

    assert calls == []


def test_poll_end_ignores_position_before_end(monkeypatch, vlc):
    player = vlc.instance.player
    values = iter([True, False, RuntimeError("gone")])
    player.is_playing = lambda: _next_or_raise(values)
    player.time_ms = 1000
    player.length_ms = 5000
    backend = _poll_backend(player)
    calls = []
    backend._end_callback = lambda: calls.append(1)
    monkeypatch.setattr(player_vlc.time, "sleep", lambda _s: None)

    backend._poll_end()

    assert calls == []


def test_poll_end_resets_state_when_not_expecting(monkeypatch, vlc):
    player = vlc.instance.player
    values = iter([True, False, RuntimeError("gone")])
    player.is_playing = lambda: _next_or_raise(values)
    backend = _poll_backend(player, expecting=False)
    monkeypatch.setattr(player_vlc.time, "sleep", lambda _s: None)

    backend._poll_end()

    assert backend._was_playing is False


def _next_or_raise(values):
    value = next(values)
    if isinstance(value, Exception):
        raise value
    return value


def test_fire_end_swallows_callback_errors(backend):
    def boom():
        raise RuntimeError("callback failed")

    backend.on_end(boom)
    backend._fire_end()  # must not raise


def test_disarm_clears_flags(backend):
    backend._expecting = backend._was_playing = backend._paused_by_user = True
    backend._disarm()
    assert backend._expecting is False
    assert backend._was_playing is False
    assert backend._paused_by_user is False


# -- transport --


def test_load_builds_media_and_parses_locally(backend, vlc):
    backend.load("/music/song.mp3")
    media = vlc.instance.medias[-1]
    assert media.path == "/music/song.mp3"
    assert media.parse_calls == [(FakeParseFlag.local, 5000)]
    assert vlc.instance.player.media is media
    assert backend._expecting is False


def test_load_ignores_parse_errors(backend, vlc):
    def failing_factory(path):
        media = FakeMedia(path)
        media.parse_error = RuntimeError("parse not supported")
        return media

    vlc.instance.media_new = failing_factory
    backend.load("/music/song.mp3")
    assert vlc.instance.player.media is not None


def test_play_arms_end_detection(backend, vlc):
    backend.play()
    assert vlc.instance.player.playing is True
    assert backend._expecting is True
    assert backend._paused_by_user is False


def test_pause_flags_user_initiated(backend, vlc):
    backend.pause()
    assert vlc.instance.player.playing is False
    assert backend._paused_by_user is True


def test_stop_uses_native_stop(backend, vlc):
    backend._expecting = True
    backend.stop()
    assert vlc.instance.player.playing is False
    assert backend._expecting is False


def test_stop_falls_back_to_pause_and_rewind(backend, vlc):
    player = vlc.instance.player
    player.stop_error = AttributeError("no stop on libvlc 4")
    player.time_ms = 9000
    backend.stop()
    assert player.playing is False
    assert player.time_ms == 0


def test_stop_swallows_fallback_failures(backend, vlc):
    player = vlc.instance.player
    player.stop_error = AttributeError("no stop")
    player.set_pause = lambda value: (_ for _ in ()).throw(RuntimeError("no pause"))
    backend.stop()  # must not raise


def test_seek_clamps_and_converts_to_ms(backend, vlc):
    backend.seek(1.5)
    assert vlc.instance.player.time_ms == 1500
    backend.seek(-3)
    assert vlc.instance.player.time_ms == 0


def test_set_volume_clamps_and_maps_to_percent(backend, vlc):
    backend.set_volume(0.5)
    assert vlc.instance.player.volume == 50
    backend.set_volume(2.0)
    assert vlc.instance.player.volume == 100
    backend.set_volume(-1)
    assert vlc.instance.player.volume == 0


def test_get_pos_clamps_negative(backend, vlc):
    vlc.instance.player.time_ms = -500
    assert backend.get_pos() == 0.0
    vlc.instance.player.time_ms = 2500
    assert backend.get_pos() == 2.5


def test_get_duration_prefers_media(backend, vlc):
    backend.load("/m/a.mp3")
    vlc.instance.medias[-1].duration_ms = 7000
    vlc.instance.player.length_ms = 9000
    assert backend.get_duration() == 7.0


def test_get_duration_falls_back_to_player_length(backend, vlc):
    backend.load("/m/a.mp3")
    vlc.instance.medias[-1].duration_ms = None
    vlc.instance.player.length_ms = 9000
    assert backend.get_duration() == 9.0


def test_get_duration_falls_back_when_media_raises(backend, vlc):
    backend.load("/m/a.mp3")
    vlc.instance.medias[-1].duration_error = RuntimeError("bad media")
    vlc.instance.player.length_ms = 4000
    assert backend.get_duration() == 4.0


def test_get_duration_zero_when_unavailable(backend, vlc):
    backend.load("/m/a.mp3")
    vlc.instance.medias[-1].duration_ms = -1
    vlc.instance.player.length_error = RuntimeError("no length")
    assert backend.get_duration() == 0.0


def test_get_duration_handles_missing_media(backend, vlc):
    vlc.instance.player.length_ms = 3000
    assert backend.get_duration() == 3.0


def test_is_playing_delegates(backend, vlc):
    vlc.instance.player.playing = True
    assert backend.is_playing() is True
    vlc.instance.player.playing = False
    assert backend.is_playing() is False


def test_on_end_registers_callback(backend):
    def callback() -> None:
        pass

    backend.on_end(callback)
    assert backend._end_callback is callback


def test_close_stops_and_releases(backend, vlc):
    backend.close()
    assert vlc.instance.player.released == 1
    assert vlc.instance.released == 1


def test_close_ignores_release_errors(backend, vlc):
    vlc.instance.player.release_error = RuntimeError("release failed")
    vlc.instance.release_error = RuntimeError("instance release failed")
    backend.close()  # must not raise


def test_close_continues_when_stop_raises(backend, vlc, monkeypatch):
    def boom():
        raise RuntimeError("stop blew up")

    monkeypatch.setattr(backend, "stop", boom)
    backend.close()  # must not raise
    assert vlc.instance.player.released == 1
    assert vlc.instance.released == 1
