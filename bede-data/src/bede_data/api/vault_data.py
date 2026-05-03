import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from bede_data.db.connection import get_db
from bede_data.tz import utc_to_local

router = APIRouter(prefix="/api/vault", tags=["vault"])


def _resolve_date(date_str: str) -> str:
    if date_str == "today":
        return date.today().isoformat()
    if date_str == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return date_str


@router.get("/screen-time")
def get_screen_time(
    date: str = Query(...),
    device: str | None = Query(None),
    top_n: int | None = Query(None),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    query = "SELECT device, entry_type, name, seconds FROM screen_time WHERE date = ?"
    params: list = [d]
    if device:
        query += " AND device = ?"
        params.append(device)
    query += " ORDER BY seconds DESC"
    if top_n:
        query += " LIMIT ?"
        params.append(top_n)

    cursor = conn.execute(query, params)
    return {"date": d, "entries": [dict(row) for row in cursor.fetchall()]}


@router.get("/safari")
def get_safari(
    date: str = Query(...),
    device: str | None = Query(None),
    domain: str | None = Query(None),
    top_n: int | None = Query(None),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    query = "SELECT device, domain, title, url, visited_at FROM safari_history WHERE date = ?"
    params: list = [d]
    if device:
        query += " AND device = ?"
        params.append(device)
    if domain:
        query += " AND domain = ?"
        params.append(domain)
    query += " ORDER BY visited_at DESC"
    if top_n:
        query += " LIMIT ?"
        params.append(top_n)

    cursor = conn.execute(query, params)
    entries = [dict(row) for row in cursor.fetchall()]
    for e in entries:
        e["visited_at"] = utc_to_local(e.get("visited_at"), timezone)
    return {"date": d, "entries": entries}


@router.get("/youtube")
def get_youtube(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT title, url, visited_at FROM youtube_history WHERE date = ? ORDER BY visited_at DESC",
        (d,),
    )
    entries = [dict(row) for row in cursor.fetchall()]
    for e in entries:
        e["visited_at"] = utc_to_local(e.get("visited_at"), timezone)
    return {"date": d, "entries": entries}


@router.get("/podcasts")
def get_podcasts(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT podcast, episode, duration_seconds, played_at FROM podcasts WHERE date = ? ORDER BY played_at DESC",
        (d,),
    )
    entries = [dict(row) for row in cursor.fetchall()]
    for e in entries:
        e["played_at"] = utc_to_local(e.get("played_at"), timezone)
    return {"date": d, "entries": entries}


@router.get("/claude-sessions")
def get_claude_sessions(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT project, start_time, end_time, duration_min, turns, summary FROM claude_sessions WHERE date = ? ORDER BY start_time",
        (d,),
    )
    return {"date": d, "sessions": [dict(row) for row in cursor.fetchall()]}


@router.get("/bede-sessions")
def get_bede_sessions(
    date: str = Query(...),
    timezone: str = Query("Australia/Sydney"),
    conn: sqlite3.Connection = Depends(get_db),
):
    d = _resolve_date(date)
    cursor = conn.execute(
        "SELECT task_name, start_time, end_time, duration_min, turns, summary FROM bede_sessions WHERE date = ? ORDER BY start_time",
        (d,),
    )
    return {"date": d, "sessions": [dict(row) for row in cursor.fetchall()]}
