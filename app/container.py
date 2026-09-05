"""Composition root: engine -> repo -> service -> view -> controller.

Audio backend selection happens here at startup: VLC when libvlc is
present, miniaudio fallback otherwise (with a visible warning).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger
from sqlalchemy.engine import Engine

from controllers.main_controller import MainController
from domain.interfaces import BackendUnavailableError, EventBus, PlayerBackend
from infrastructure.audio_tagger import TinyTagAudioTagger
from infrastructure.db import engine as default_engine
from infrastructure.playlist_repository import SqlPlaylistRepository
from infrastructure.song_repository import SqlSongRepository
from services.library_service import LibraryService
from services.player_service import PlayerService
from services.playlist_service import PlaylistService


def create_player_backend() -> tuple[str, PlayerBackend]:
    """Detect and build the audio backend. Returns (name, backend).

    Honors WAVE_AUDIO_BACKEND=vlc|miniaudio to force a backend (useful
    when auto-detection picks a crashing VLC). Defaults to auto.
    Raises BackendUnavailableError when no usable backend exists.
    """
    import os

    from infrastructure import player_miniaudio, player_vlc

    forced = os.environ.get("WAVE_AUDIO_BACKEND", "auto").lower()
    if forced not in ("auto", "vlc", "miniaudio"):
        logger.warning(f"Unknown WAVE_AUDIO_BACKEND={forced!r}, using auto")
        forced = "auto"

    if forced in ("auto", "vlc") and player_vlc.is_available():
        return "vlc", player_vlc.VlcBackend()
    if forced == "vlc":
        logger.warning("Forced VLC unavailable — trying miniaudio fallback")
    elif forced == "auto":
        logger.warning("libvlc not found — compatibility mode (miniaudio fallback)")
    if player_miniaudio.is_available():
        return "miniaudio", player_miniaudio.MiniaudioBackend()
    raise BackendUnavailableError("No audio backend available (tried vlc, miniaudio)")


@dataclass
class Container:
    engine: Engine
    repo: SqlSongRepository
    library: LibraryService
    bus: EventBus
    player: PlayerService
    playlists: PlaylistService
    backend_name: str = "vlc"
    controller: MainController | None = None


def build_container(
    view: Any | None = None,
    engine: Engine | None = None,
    backend: PlayerBackend | None = None,
) -> Container:
    """Build backend services; optionally attach a view + controller.

    Pass an explicit backend in tests to avoid touching real audio devices.
    """
    eng = engine or default_engine
    bus = EventBus()
    repo = SqlSongRepository(eng)
    library = LibraryService(repo, tagger=TinyTagAudioTagger(), event_bus=bus)
    if backend is None:
        backend_name, backend = create_player_backend()
    else:
        backend_name = type(backend).__name__
    player = PlayerService(backend)
    playlists = PlaylistService(SqlPlaylistRepository(eng), event_bus=bus)
    container = Container(
        engine=eng,
        repo=repo,
        library=library,
        bus=bus,
        player=player,
        playlists=playlists,
        backend_name=backend_name,
    )
    if view is not None:
        controller = MainController(view=view, library=library, player=player, playlists=playlists)
        container.controller = controller
    return container
