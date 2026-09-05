"""Legacy database path — re-export shim over infrastructure.db.

Canonical engine lives in infrastructure.db with an absolute data/app.db
path. Kept so legacy imports keep working during migration.
"""

from infrastructure.db import DB_PATH, DB_URL, engine, get_session, init_db

# Legacy name used across old code/tests.
DB_NAME = str(DB_PATH)

__all__ = ["DB_NAME", "DB_PATH", "DB_URL", "engine", "get_session", "init_db"]
