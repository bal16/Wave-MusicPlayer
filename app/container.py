"""Composition root: engine -> repo -> service -> view -> controller.

Phase 0 keeps the legacy View untouched; the container only builds the
backend graph and attaches the thin controller to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Engine

from controllers.main_controller import MainController
from domain.interfaces import EventBus
from infrastructure.audio_tagger import TinyTagAudioTagger
from infrastructure.db import engine as default_engine
from infrastructure.song_repository import SqlSongRepository
from services.library_service import LibraryService


@dataclass
class Container:
    engine: Engine
    repo: SqlSongRepository
    library: LibraryService
    bus: EventBus
    controller: MainController | None = None


def build_container(view: Any | None = None, engine: Engine | None = None) -> Container:
    """Build backend services; optionally attach a view + controller."""
    eng = engine or default_engine
    bus = EventBus()
    repo = SqlSongRepository(eng)
    library = LibraryService(repo, tagger=TinyTagAudioTagger(), event_bus=bus)
    container = Container(engine=eng, repo=repo, library=library, bus=bus)
    if view is not None:
        controller = MainController(view=view, library=library)
        container.controller = controller
    return container
