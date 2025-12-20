from sqlmodel import SQLModel, create_engine, Session
from loguru import logger

DB_NAME = "database.db"

sqlite_url = f"sqlite:///{DB_NAME}"
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """
    This function will be called when the Splash Screen is loading. \n
    His job is to create a table if one does not already exist.
    """
    # Import schema here so SQLModel knows which tables to create
    from models.schema import Song, Playlist, PlaylistSongLink  # noqa: F401
    
    # Magic command to create tables
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized successfully.")

def get_session():
    """Helper to get a database connection"""
    return Session(engine)