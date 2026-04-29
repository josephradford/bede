import os
import sqlite3

from fastapi import APIRouter, Depends

from bede_data.config import settings
from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("")
def get_storage(conn: sqlite3.Connection = Depends(get_db)):
    db_path = settings.sqlite_db_path
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = []
    for row in cursor.fetchall():
        table_name = row["name"]
        count_cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM [{table_name}]")
        count = count_cursor.fetchone()["cnt"]
        tables.append({"name": table_name, "row_count": count})

    return {"db_size_bytes": db_size, "tables": tables}
