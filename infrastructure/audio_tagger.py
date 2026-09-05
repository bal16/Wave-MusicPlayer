"""TinyTag wrapper: path -> SongDraft.

Locked decision: MVP supports MP3 + FLAC only. OGG/M4A/WAV are skipped with
a debug log (post-MVP backlog, not an error).
"""

from __future__ import annotations

import os

from loguru import logger

from domain.entities import SongDraft

SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".flac"})


def is_supported(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in SUPPORTED_AUDIO_EXTENSIONS


def normalize_path(path: str) -> str:
    return os.path.abspath(os.path.normpath(path))


class TinyTagAudioTagger:
    def read(self, path: str) -> SongDraft | None:
        from tinytag import TinyTag

        abs_path = normalize_path(path)
        if not is_supported(abs_path):
            logger.debug(f"Skip unsupported format: {abs_path}")
            return None
        try:
            tag = TinyTag.get(abs_path)
        except Exception as e:
            logger.error(f"Error reading tag {abs_path}: {e}")
            return None
        return SongDraft(
            title=tag.title or os.path.basename(abs_path),
            artist=tag.artist or "Unknown Artist",
            album=tag.album or "Unknown Album",
            file_path=abs_path,
            duration=float(tag.duration or 0.0),
        )
