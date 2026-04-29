import sqlite3

from fastapi import APIRouter, Depends

from bede_data.db.connection import get_db
from bede_data.ingest.auth import verify_ingest_token
from bede_data.ingest.health_parser import parse_health_payload

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _upsert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    for row in rows:
        conn.execute(sql, [row[c] for c in columns])
    conn.commit()
    return len(rows)


@router.post("/health")
def ingest_health(
    payload: dict,
    _token: str = Depends(verify_ingest_token),
    conn: sqlite3.Connection = Depends(get_db),
):
    parsed = parse_health_payload(payload)
    total = 0
    total += _upsert_rows(conn, "health_metrics", parsed["health_metrics"])
    total += _upsert_rows(conn, "sleep_phases", parsed["sleep_phases"])
    total += _upsert_rows(conn, "workouts", parsed["workouts"])
    total += _upsert_rows(conn, "medications", parsed["medications"])
    total += _upsert_rows(conn, "state_of_mind", parsed["state_of_mind"])
    return {"status": "ok", "records": total}
