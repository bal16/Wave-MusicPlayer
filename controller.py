from __future__ import annotations

import os
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import Session, select  # Import Session untuk dipakai di method
from tinytag import TinyTag

from models.schema import Song  # Import Model Data (Tabel)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from view import View


class MainController:
    def __init__(self, model: Engine, view: View):
        self.db_engine = model
        self.view = view

        logger.debug("MainController initialized with DB Engine and View")
        self.view.mainloop()
        logger.info("Application main loop has started")

    def add_music_from_folder(self, folder_path: str):
        logger.info(f"Processing folder: {folder_path}")

        # List all files in the folder
        file_lists = os.listdir(folder_path)

        # Select only songs
        song_files = [f for f in file_lists if f.lower().endswith(".flac")]

        song_paths = [os.path.join(folder_path, f) for f in song_files]

        songs: list[Song] = []

        for song_path in song_paths:
            try:
                tag = TinyTag.get(song_path)
                new_song = Song(
                    title=tag.title or os.path.basename(song_path),
                    artist=tag.artist or "Unknown Artist",
                    album=tag.album or "Unknown Album",
                    duration=int(tag.duration) if tag.duration else 0,
                    file_path=song_path,
                )

                songs.append(new_song)

            except Exception as e:
                logger.error(f"Error processing file {song_path}: {e}")

        logger.info(f"Total songs to add: {len(songs)}")

        with Session(self.db_engine) as session:
            for song in songs:
                statement = select(Song).where(Song.file_path == song.file_path)
                result = session.exec(statement).first()
                if result:
                    logger.info(f"Song already exists in DB: {song.title} - {song.file_path}")
                else:
                    session.add(song)
                    logger.info(f"Added song to DB: {song.title} - {song.file_path}")
            session.commit()
