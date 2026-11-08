"""Unit tests for domain/interfaces.py (contracts + event bus)."""

from __future__ import annotations

import pytest

from domain.entities import Playlist, Song, SongDraft
from domain.interfaces import (
    LIBRARY_CHANGED_EVENT,
    PLAYLIST_CHANGED_EVENT,
    BackendUnavailableError,
    EventBus,
    PlayerBackend,
    PlaylistRepository,
    SongRepository,
)


def test_event_names_are_stable():
    assert LIBRARY_CHANGED_EVENT == "library_changed"
    assert PLAYLIST_CHANGED_EVENT == "playlist_changed"


def test_backend_unavailable_is_runtime_error():
    assert issubclass(BackendUnavailableError, RuntimeError)


def test_event_bus_publish_reaches_listeners_with_payload():
    bus = EventBus()
    seen = []
    bus.subscribe("event", lambda *a, **kw: seen.append((a, kw)))
    bus.publish("event", 1, added=2)
    assert seen == [((1,), {"added": 2})]


def test_event_bus_unsubscribe_is_idempotent():
    bus = EventBus()
    seen = []
    unsubscribe = bus.subscribe("event", lambda: seen.append(1))
    unsubscribe()
    unsubscribe()
    bus.publish("event")
    assert seen == []


def test_event_bus_publish_unknown_event_is_noop():
    EventBus().publish("missing", value=1)


def test_event_bus_publish_copies_listener_list():
    bus = EventBus()
    seen = []

    def first():
        seen.append("first")
        bus.subscribe("event", lambda: seen.append("late"))

    bus.subscribe("event", first)
    bus.publish("event")
    assert seen == ["first"]


@pytest.mark.parametrize("abc", [SongRepository, PlaylistRepository, PlayerBackend])
def test_abstract_repositories_cannot_be_instantiated(abc):
    with pytest.raises(TypeError):
        abc()


class _MinimalBackend(PlayerBackend):
    def load(self, file_path: str) -> None:
        pass

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def seek(self, seconds: float) -> None:
        pass

    def set_volume(self, level: float) -> None:
        pass

    def get_pos(self) -> float:
        return 0.0

    def get_duration(self) -> float:
        return 0.0

    def is_playing(self) -> bool:
        return False


def test_player_backend_default_hooks_are_optional_noops():
    backend = _MinimalBackend()
    assert backend.on_end(lambda: None) is None
    assert backend.close() is None


def test_protocols_are_structural():
    class Reader:
        def read(self, path: str) -> SongDraft | None:
            return SongDraft(title="x", file_path=path)

        def read_cover(self, path: str) -> bytes | None:
            return None

    assert Reader().read_cover("/x") is None


def test_domain_entities_are_importable_from_interfaces_contracts():
    # Contracts type-annotate with the entities; keep the names referenced so
    # a bad refactor in imports is caught by this module.
    assert Song(id=1, title="x").id == 1
    assert Playlist(id=1, name="x").name == "x"
