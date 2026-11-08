"""Unit tests for services/player_service.py (backend is a fake)."""

from __future__ import annotations

import pytest

from services.player_service import (
    STATE_CHANGED_EVENT,
    TRACK_CHANGED_EVENT,
    PlayerService,
)
from tests.support.doubles import FakeBackend, make_song


@pytest.fixture()
def backend():
    return FakeBackend()


@pytest.fixture()
def service(backend):
    return PlayerService(backend)


def _songs(n=3):
    return [make_song(i, duration=200.0) for i in range(1, n + 1)]


# -- state --


def test_current_is_none_for_empty_queue(service):
    assert service.current is None


def test_is_playing_and_volume_delegate_to_backend(service, backend):
    assert service.is_playing is False
    backend.playing = True
    assert service.is_playing is True
    assert service.volume == 1.0


def test_get_pos_delegates(service, backend):
    backend.pos = 4.0
    assert service.get_pos() == 4.0


def test_get_duration_falls_back_to_song_metadata(service, backend):
    service.play_queue([make_song(1, duration=225.0)])
    assert backend.get_duration() == 0.0
    assert service.get_duration() == 225.0


def test_get_duration_prefers_backend(service, backend):
    backend.durations["/music/1.mp3"] = 180.0
    service.play_queue([make_song(1, duration=225.0)])
    assert service.get_duration() == 180.0


def test_get_duration_zero_without_current_song(service):
    assert service.get_duration() == 0.0


# -- queue / transport --


def test_play_queue_starts_at_index(service, backend):
    current = service.play_queue(_songs(), 1)
    assert current.id == 2
    assert backend.loaded == "/music/2.mp3"
    assert backend.playing is True


def test_play_queue_empty_is_noop(service, backend):
    assert service.play_queue([]) is None
    assert service.current is None
    assert backend.load_calls == []


@pytest.mark.parametrize(("index", "expected"), [(-5, 1), (99, 3)])
def test_play_queue_clamps_index(service, index, expected):
    assert service.play_queue(_songs(), index).id == expected


def test_play_queue_copies_the_list(service):
    songs = _songs(2)
    service.play_queue(songs, 0)
    songs.append(make_song(3))
    assert [service.next().id, service.next().id] == [2, 1]


def test_play_pause_empty_queue_is_false(service, backend):
    assert service.play_pause() is False
    assert backend.pause_calls == backend.play_calls == 0


def test_play_pause_toggles(service, backend):
    service.play_queue([make_song(1)])
    assert backend.playing is True
    assert service.play_pause() is False
    assert service.play_pause() is True


def test_next_prev_wrap_around(service):
    service.play_queue(_songs(2), 1)
    assert service.next().id == 1
    assert service.prev().id == 2


def test_next_prev_empty_queue_return_none(service):
    assert service.next() is None
    assert service.prev() is None


def test_prev_restarts_when_well_into_song(service, backend):
    service.play_queue(_songs(2), 1)
    backend.pos = 10.0
    assert service.prev().id == 2
    assert backend.pos == 0.0
    assert backend.seek_calls == [0.0]


def test_seek_clamps_to_duration(service, backend):
    backend.durations["/music/1.mp3"] = 200.0
    service.play_queue([make_song(1)])
    assert service.seek(9999) == 200.0
    assert service.seek(-5) == 0.0


def test_seek_without_known_duration_only_clamps_negative(service, backend):
    service.play_queue([make_song(1, duration=0.0)])
    assert service.seek(50) == 50.0
    assert service.seek(-1) == 0.0


def test_set_volume_clamps_and_unmutes(service, backend):
    service.toggle_mute()
    assert service.volume == 0.0
    assert service.set_volume(0.5) == 0.5
    assert service.volume == 0.5
    assert backend.volume == 0.5
    assert service.set_volume(5) == 1.0
    assert service.set_volume(-5) == 0.0


def test_toggle_mute_restores_previous_volume(service, backend):
    service.set_volume(0.5)
    assert service.toggle_mute() is True
    assert backend.volume == 0.0
    assert service.volume == 0.0
    assert service.toggle_mute() is False
    assert backend.volume == 0.5


def test_stop_clears_queue_and_publishes(service, backend):
    states = []
    service.subscribe(STATE_CHANGED_EVENT, lambda playing=False, **kw: states.append(playing))
    service.play_queue([make_song(1)])
    service.stop()
    assert service.current is None
    assert backend.stop_calls >= 1
    assert states[-1] is False


def test_shutdown_stops_and_closes(service, backend):
    service.play_queue([make_song(1)])
    service.shutdown()
    assert backend.close_calls == 1
    assert service.current is None


def test_shutdown_closes_backend_even_when_stop_fails(service, backend, monkeypatch):
    def boom():
        raise RuntimeError("stop failed")

    monkeypatch.setattr(service, "stop", boom)
    with pytest.raises(RuntimeError):
        service.shutdown()
    assert backend.close_calls == 1


# -- events --


def test_listeners_receive_track_and_state(service):
    events = []

    def on_track(song=None, **kw):
        events.append(("track", song.id))

    def on_state(playing=False, **kw):
        events.append(("state", playing))

    service.subscribe(TRACK_CHANGED_EVENT, on_track)
    service.subscribe(STATE_CHANGED_EVENT, on_state)
    service.play_queue([make_song(7)])
    assert ("track", 7) in events
    assert ("state", True) in events


def test_volume_and_mute_publish_state(service):
    states = []
    service.subscribe(STATE_CHANGED_EVENT, lambda playing=False, **kw: states.append(playing))
    service.set_volume(0.5)
    service.toggle_mute()
    assert states == [False, False]


def test_listener_added_during_publish_is_not_called_twice(service):
    calls = []

    def first(**kwargs):
        calls.append("first")
        service.subscribe("event", lambda **kw: calls.append("late"))

    service.subscribe("event", first)
    service._publish("event")
    assert calls == ["first"]


# -- internals --


def test_play_current_empty_queue_is_noop(service, backend):
    service._play_current()
    assert backend.load_calls == []


def test_media_end_empty_queue_is_noop(service):
    service._on_media_end()
    assert service.current is None


def test_auto_next_wraps_on_media_end(service, backend):
    service.play_queue(_songs(2), 1)
    backend.simulate_end()
    assert service.current.id == 1
    assert backend.loaded == "/music/1.mp3"
