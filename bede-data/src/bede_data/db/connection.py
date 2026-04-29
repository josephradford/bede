import sqlite3
from collections.abc import Generator

from bede_data.config import settings


def init_db() -> None:
    """Initialise the SQLite database, creating the file if it doesn't exist."""
    import os
    db_path = settings.sqlite_db_path
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection and close it on teardown."""
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
