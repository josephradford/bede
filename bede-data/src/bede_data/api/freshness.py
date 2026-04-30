import sqlite3

from fastapi import APIRouter, Depends

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/freshness", tags=["freshness"])


@router.get("")
def get_freshness(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "SELECT source, last_received_at, expected_interval_seconds, updated_at FROM data_freshness ORDER BY source"
    )
    return {"sources": [dict(r) for r in cursor.fetchall()]}
