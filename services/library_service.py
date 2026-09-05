"""LibraryService — F1 (scan) + F2 (list/favorite) logic.

Pure Python: no Tk, no SQLModel, no TinyTag. All collaborators are
injected as interfaces; unit-test with a fake repo + tagger.
"""

from __future__ import annotations

import os

from loguru import logger

from domain.entities import Song, SongDraft
from domain.interfaces import LIBRARY_CHANGED_EVENT, AudioTagger, EventBus, SongRepository


class LibraryService:
    def __init__(
        self,
        repo: SongRepository,
        tagger: AudioTagger,
        event_bus: EventBus | None = None,
    ):
        self._repo = repo
        self._tagger = tagger
        self._bus = event_bus

    def subscribe(self, listener) -> None:
        """Subscribe to library_changed events (no-op without an event bus)."""
        if self._bus is not None:
            self._bus.subscribe(LIBRARY_CHANGED_EVENT, listener)

    def scan_folder(self, folder_path: str) -> int:
        """Recursively scan mp3+flac into the DB. Return the new-song count.

        Cancelled dialog (""/None/missing dir) returns 0 instead of crashing.
        """
        if not folder_path:
            logger.debug("scan_folder cancelled/empty — nothing to do")
            return 0
        if not os.path.isdir(folder_path):
            logger.warning(f"scan_folder: not a directory: {folder_path!r}")
            return 0

        drafts: list[SongDraft] = []
        for root, _dirs, files in os.walk(folder_path):
            for name in files:
                full = os.path.join(root, name)
                draft = self._tagger.read(full)
                if draft is not None:
                    drafts.append(draft)

        added = self._repo.add_all(drafts)
        logger.info(f"scan_folder {folder_path!r}: {added} new / {len(drafts)} parsed")
        if added and self._bus is not None:
            self._bus.publish(LIBRARY_CHANGED_EVENT, added=added)
        return added

    def list_songs(self, query: str = "", favorites_only: bool = False) -> list[Song]:
        return self._repo.list_all(query=query, favorites_only=favorites_only)

    def get_song(self, song_id: int) -> Song | None:
        return self._repo.get_by_id(song_id)

    def toggle_favorite(self, song_id: int) -> bool | None:
        return self._repo.toggle_favorite(song_id)
