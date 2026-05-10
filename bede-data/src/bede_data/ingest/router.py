import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from bede_data.db.connection import get_db
from bede_data.ingest.auth import verify_ingest_token
from bede_data.ingest.health_parser import parse_health_payload
from bede_data.ingest.usage_parser import parse_usage_payload

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _upsert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    """INSERT OR REPLACE rows into the given table. Column names come from the first row's keys. Does not commit — caller is responsible for committing the transaction."""
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO [{table}] ({col_names}) VALUES ({placeholders})"
    conn.executemany(sql, [[row[c] for c in columns] for row in rows])
    return len(rows)


def _replace_daily(
    conn: sqlite3.Connection,
    table: str,
    date: str,
    device: str | None,
    rows: list[dict],
) -> int:
    """Delete all existing rows for the date (and device, if given) then insert the new rows. Used for data sources like screen time where each export is a complete daily snapshot."""
    if not rows:
        return 0
    if device:
        conn.execute(
            f"DELETE FROM [{table}] WHERE date = ? AND device = ?", (date, device)
        )
    else:
        conn.execute(f"DELETE FROM [{table}] WHERE date = ?", (date,))
    return _upsert_rows(conn, table, rows)


def _update_freshness(
    conn: sqlite3.Connection, source: str, expected_interval: int, *, always_expected: bool = True
):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """INSERT OR REPLACE INTO data_freshness
           (source, last_received_at, expected_interval_seconds, always_expected, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (source, now, expected_interval, int(always_expected), now),
    )


@router.post("/health")
def ingest_health(
    payload: dict,
    _token: str = Depends(verify_ingest_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    parsed = parse_health_payload(payload)
    total = 0
    counts = {}
    for table in ("health_metrics", "sleep_phases", "workouts", "medications", "state_of_mind"):
        n = _upsert_rows(conn, table, parsed[table])
        total += n
        counts[table] = n
    _HEALTH_SOURCE_KEYS = {
        "health_metrics": "health_metrics",
        "sleep_phases": "sleep",
        "workouts": "workouts",
        "medications": "medications",
        "state_of_mind": "state_of_mind",
    }
    for table, source_key in _HEALTH_SOURCE_KEYS.items():
        if counts[table] > 0:
            _update_freshness(conn, source_key, 1800)
    conn.commit()
    return {"status": "ok", "records": total}


_USAGE_FRESHNESS = {
    "screen_time_mac": {"files": {"screentime.csv"}, "always_expected": True},
    "screen_time_iphone": {"files": {"iphone-screentime.csv"}, "always_expected": True},
    "safari_history": {"prefix": "safari", "always_expected": True},
    "youtube_history": {"prefix": "youtube", "always_expected": False},
    "podcasts": {"prefix": "podcasts", "always_expected": False},
    "claude_sessions": {"prefix": "claude-sessions", "always_expected": False},
    "bede_sessions": {"prefix": "bede-sessions", "always_expected": False},
}


def _usage_sources_present(files: dict[str, str]) -> set[str]:
    """Return the set of freshness source keys whose files appear in the upload."""
    present = set()
    filenames = set(files.keys())
    for source_key, spec in _USAGE_FRESHNESS.items():
        if "files" in spec:
            if spec["files"] & filenames:
                present.add(source_key)
        elif "prefix" in spec:
            if any(f.startswith(spec["prefix"]) for f in filenames):
                present.add(source_key)
    return present


@router.post("/usage")
def ingest_usage(
    payload: dict,
    _token: str = Depends(verify_ingest_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    parsed = parse_usage_payload(payload)
    date = payload.get("date", "")
    total = 0

    if parsed["screen_time"]:
        devices = {r["device"] for r in parsed["screen_time"]}
        for device in devices:
            device_rows = [r for r in parsed["screen_time"] if r["device"] == device]
            total += _replace_daily(conn, "screen_time", date, device, device_rows)

    total += _upsert_rows(conn, "safari_history", parsed["safari_history"])
    total += _upsert_rows(conn, "youtube_history", parsed["youtube_history"])
    total += _upsert_rows(conn, "podcasts", parsed["podcasts"])
    total += _upsert_rows(conn, "claude_sessions", parsed["claude_sessions"])
    total += _upsert_rows(conn, "bede_sessions", parsed["bede_sessions"])
    total += _upsert_rows(conn, "music_listens", parsed.get("music_listens", []))

    for source_key in _usage_sources_present(payload.get("files", {})):
        spec = _USAGE_FRESHNESS[source_key]
        _update_freshness(conn, source_key, 10800, always_expected=spec["always_expected"])

    conn.commit()
    return {"status": "ok", "records": total}
