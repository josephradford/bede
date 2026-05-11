import sqlite3
from collections.abc import Generator

from bede_data.config import settings
from bede_data.db.schema import SCHEMA_SQL, SCHEMA_VERSION, tables_needing_reset


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.sqlite_db_path, check_same_thread=False, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
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
        if existing is not None and existing < 4:
            try:
                conn.execute("ALTER TABLE schedules ADD COLUMN task_config TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        if existing is not None and existing < 6:
            for col, default in [("playhead_seconds", 0), ("play_count", 0)]:
                try:
                    conn.execute(
                        f"ALTER TABLE podcasts ADD COLUMN {col} INTEGER DEFAULT {default}"
                    )
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        if existing is not None and existing < 7:
            try:
                conn.execute("ALTER TABLE medications ADD COLUMN status TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        if existing is not None and existing < 8:
            for col in ["kind", "valence_classification"]:
                try:
                    conn.execute(f"ALTER TABLE state_of_mind ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("ALTER TABLE state_of_mind DROP COLUMN context")
            except sqlite3.OperationalError:
                pass
            conn.commit()
        if existing is not None and existing < 11:
            try:
                conn.execute(
                    "ALTER TABLE data_freshness ADD COLUMN always_expected INTEGER NOT NULL DEFAULT 1"
                )
            except sqlite3.OperationalError:
                pass
            conn.execute(
                "DELETE FROM data_freshness WHERE source IN ('health', 'vault')"
            )
            conn.commit()
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
