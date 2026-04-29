import sqlite3
from collections.abc import Generator

from bede_data.config import settings
from bede_data.db.schema import SCHEMA_SQL, SCHEMA_VERSION


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA_SQL)
        existing = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if existing is None or existing < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            conn.commit()
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
