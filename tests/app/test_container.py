"""Unit tests for app/container.py (wiring + backend selection)."""

from __future__ import annotations

import pytest
from sqlmodel import SQLModel, create_engine

from app import container as container_module
from app.container import Container, build_container, create_player_backend
from domain.interfaces import BackendUnavailableError
from tests.support.doubles import FakeBackend, FakeView


def _engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/c.db")
    SQLModel.metadata.create_all(engine)
    return engine


# -- backend factory --


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
    assert create_player_backend()[0] == "miniaudio"


def test_factory_env_vlc_unavailable_falls_back(monkeypatch):
    import infrastructure.player_miniaudio as mini
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "vlc")
    monkeypatch.setattr(vlcmod, "is_available", lambda: False)
    monkeypatch.setattr(mini, "is_available", lambda: True)
    monkeypatch.setattr(mini, "MiniaudioBackend", FakeBackend)
    assert create_player_backend()[0] == "miniaudio"


def test_factory_env_unknown_uses_auto(monkeypatch):
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "bogus")
    monkeypatch.setattr(vlcmod, "is_available", lambda: True)
    monkeypatch.setattr(vlcmod, "VlcBackend", FakeBackend)
    assert create_player_backend()[0] == "vlc"


def test_factory_env_vlc_forced_and_available(monkeypatch):
    import infrastructure.player_vlc as vlcmod

    monkeypatch.setenv("WAVE_AUDIO_BACKEND", "vlc")
    monkeypatch.setattr(vlcmod, "is_available", lambda: True)
    monkeypatch.setattr(vlcmod, "VlcBackend", FakeBackend)
    assert create_player_backend()[0] == "vlc"


# -- container --


def test_build_container_without_view(tmp_path):
    container = build_container(view=None, engine=_engine(tmp_path), backend=FakeBackend())
    assert isinstance(container, Container)
    assert container.library is not None
    assert container.player is not None
    assert container.playlists is not None
    assert container.controller is None
    assert container.backend_name == "FakeBackend"
    assert container.library.scan_folder("") == 0


def test_build_container_with_view_attaches_controller(tmp_path):
    view = FakeView()
    container = build_container(view=view, engine=_engine(tmp_path), backend=FakeBackend())
    assert container.controller is not None
    assert container.controller.view is view


def test_build_container_autodetects_backend_when_none(monkeypatch, tmp_path):
    backend = FakeBackend()
    monkeypatch.setattr(container_module, "create_player_backend", lambda: ("vlc", backend))
    container = build_container(view=None, engine=_engine(tmp_path), backend=None)
    assert container.backend_name == "vlc"
    assert container.player._backend is backend


def test_container_dataclass_fields(tmp_path):
    container = build_container(view=None, engine=_engine(tmp_path), backend=FakeBackend())
    assert container.engine is not None
    assert container.repo is not None
    assert container.bus is not None
