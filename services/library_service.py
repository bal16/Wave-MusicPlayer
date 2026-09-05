"""LibraryService — F1 (scan) + F2 (list/favorite) logic.

Pure Python: no Tk, no SQLModel, no TinyTag. All collaborators are
injected as interfaces; unit-test with a fake repo + tagger.

Threading: scan_folder() is designed to run on a worker thread. It never
touches widgets; progress goes to the optional callback and completion is
announced via the library_changed event (the controller marshals both to
the UI thread with after()).
"""

from __future__ import annotations

import os
from collections.abc import Callable

from loguru import logger

from domain.entities import Song, SongDraft
from domain.interfaces import (
    LIBRARY_CHANGED_EVENT,
    AudioTagger,
    CoverArtReader,
    EventBus,
    SongRepository,
)


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

    def scan_folder(
        self,
        folder_path: str,
        progress: Callable[[int, int], None] | None = None,
    ) -> int:
        """Recursively scan mp3+flac into the DB. Return the new-song count.

        Cancelled dialog (""/None/missing dir) returns 0 instead of crashing.
        progress(done, total) is called as files are parsed (two-pass walk
        so total is known upfront). Publishes nothing when nothing is added.
        """
        if not folder_path:
            logger.debug("scan_folder cancelled/empty — nothing to do")
            return 0
        if not os.path.isdir(folder_path):
            logger.warning(f"scan_folder: not a directory: {folder_path!r}")
            return 0

        all_files = [
            os.path.join(root, name)
            for root, _dirs, files in os.walk(folder_path)
            for name in files
        ]
        total = len(all_files)

        drafts: list[SongDraft] = []
        for done, full in enumerate(all_files, start=1):
            draft = self._tagger.read(full)
            if draft is not None:
                drafts.append(draft)
            if progress is not None:
                progress(done, total)

        added = self._repo.add_all(drafts)
        logger.info(f"scan_folder {folder_path!r}: {added} new / {len(drafts)} parsed")
        if added and self._bus is not None:
            self._bus.publish(LIBRARY_CHANGED_EVENT, added=added)
        return added

    def list_songs(self, query: str = "", favorites_only: bool = False) -> list[Song]:
        return self._repo.list_all(query=query, favorites_only=favorites_only)

    def get_song(self, song_id: int) -> Song | None:
        return self._repo.get_by_id(song_id)

    def get_cover(self, song_id: int) -> bytes | None:
        """Embedded cover bytes for a song, or None.

        Requires the injected tagger to also satisfy CoverArtReader
        (TinyTagAudioTagger does; pure-metadata taggers return None).
        """
        song = self._repo.get_by_id(song_id)
        if song is None:
            return None
        reader: CoverArtReader | None = self._tagger
        read_cover = getattr(reader, "read_cover", None)
        if read_cover is None:
            return None
        return read_cover(song.file_path)

    def toggle_favorite(self, song_id: int) -> bool | None:
        return self._repo.toggle_favorite(song_id)
