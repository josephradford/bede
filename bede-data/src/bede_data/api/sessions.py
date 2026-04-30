import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api", tags=["sessions"])


class DailySessionCreate(BaseModel):
    date: str
    session_id: str


class ScratchpadEntry(BaseModel):
    date: str
    entry_time: str
    content: str


@router.post("/sessions/daily", status_code=201)
def store_daily_session(
    body: DailySessionCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    conn.execute(
        "INSERT OR REPLACE INTO daily_sessions (date, session_id, created_at) VALUES (?, ?, datetime('now'))",
        (body.date, body.session_id),
    )
    conn.commit()
    return {"date": body.date, "session_id": body.session_id}


@router.get("/sessions/daily")
def get_daily_session(
    date: str = Query(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.execute(
        "SELECT date, session_id, created_at FROM daily_sessions WHERE date = ?",
        (date,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No session for this date")
    return dict(row)


@router.post("/scratchpad", status_code=201)
def append_scratchpad(
    body: ScratchpadEntry,
    conn: sqlite3.Connection = Depends(get_db),
):
    conn.execute(
        "INSERT OR REPLACE INTO daily_scratchpads (date, entry_time, content) VALUES (?, ?, ?)",
        (body.date, body.entry_time, body.content),
    )
    conn.commit()
    return {"status": "ok"}


@router.get("/scratchpad")
def get_scratchpad(
    date: str = Query(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.execute(
        "SELECT date, entry_time, content FROM daily_scratchpads WHERE date = ? ORDER BY entry_time",
        (date,),
    )
    return {"date": date, "entries": [dict(r) for r in cursor.fetchall()]}
