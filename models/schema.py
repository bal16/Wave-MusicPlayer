"""Legacy schema path — re-export shim over infrastructure.models.

Canonical location is infrastructure.models (see docs/schema.md).
Kept so old imports (tests, view, controller) keep working during migration.
"""

from infrastructure.models import Playlist, PlaylistSongLink, Song

__all__ = ["Playlist", "PlaylistSongLink", "Song"]
