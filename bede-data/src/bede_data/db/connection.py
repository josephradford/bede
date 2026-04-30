import sqlite3
from collections.abc import Generator

from bede_data.config import settings
from bede_data.db.schema import SCHEMA_SQL, SCHEMA_VERSION, tables_needing_reset


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables (idempotent) and set WAL mode for concurrent read access."""
    conn = get_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        for table in tables_needing_reset(conn):
            conn.execute(f"DROP TABLE IF EXISTS [{table}]")
        try:
            existing = conn.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            existing = None
        if existing is not None and existing < 3:
            conn.execute("DROP TABLE IF EXISTS health_metrics")
        conn.commit()
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
    """FastAPI dependency that yields a DB connection and closes it after the request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
