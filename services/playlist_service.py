"""PlaylistService — F4 (playlist) logic.

Pure Python: no Tk, no SQLModel. Publishes playlist_changed so views
refresh without polling.
"""

from __future__ import annotations

from loguru import logger

from domain.entities import Playlist, Song
from domain.interfaces import PLAYLIST_CHANGED_EVENT, EventBus, PlaylistRepository


class PlaylistService:
    def __init__(
        self,
        repo: PlaylistRepository,
        event_bus: EventBus | None = None,
    ):
        self._repo = repo
        self._bus = event_bus

    def _changed(self) -> None:
        if self._bus is not None:
            self._bus.publish(PLAYLIST_CHANGED_EVENT)

    def subscribe(self, listener) -> None:
        """Subscribe to playlist_changed events (no-op without a bus)."""
        if self._bus is not None:
            self._bus.subscribe(PLAYLIST_CHANGED_EVENT, listener)

    def create_playlist(self, name: str, description: str = "") -> Playlist:
        playlist = self._repo.create(name, description)
        logger.info(f"Playlist created: {playlist.name}")
        self._changed()
        return playlist

    def rename_playlist(self, playlist_id: int, name: str) -> Playlist | None:
        playlist = self._repo.rename(playlist_id, name)
        if playlist is not None:
            self._changed()
        return playlist

    def delete_playlist(self, playlist_id: int) -> bool:
        deleted = self._repo.delete(playlist_id)
        if deleted:
            self._changed()
        return deleted

    def list_playlists(self) -> list[Playlist]:
        return self._repo.list_all()

    def get_playlist(self, playlist_id: int) -> Playlist | None:
        return self._repo.get_by_id(playlist_id)

    def add_song(self, playlist_id: int, song_id: int) -> bool:
        added = self._repo.add_song(playlist_id, song_id)
        if added:
            self._changed()
        return added

    def remove_song(self, playlist_id: int, song_id: int) -> bool:
        removed = self._repo.remove_song(playlist_id, song_id)
        if removed:
            self._changed()
        return removed

    def songs_in_playlist(self, playlist_id: int) -> list[Song]:
        return self._repo.songs_in_playlist(playlist_id)
