import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from bede_data.analytics.engine import run_analytics, store_flags
from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/flags")
def get_flags(
    severity: str | None = Query(None),
    acknowledged: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, signal, severity, detail, data, computed_at, acknowledged FROM analytics_flags WHERE 1=1"
    params: list = []
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if acknowledged is not None:
        query += " AND acknowledged = ?"
        params.append(int(acknowledged))
    query += " ORDER BY computed_at DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    flags = [dict(r) for r in cursor.fetchall()]
    for f in flags:
        f["acknowledged"] = bool(f["acknowledged"])
    return {"flags": flags}


@router.post("/run")
def trigger_analytics(
    conn: sqlite3.Connection = Depends(get_db),
):
    flags = run_analytics(conn)
    count = store_flags(conn, flags)
    return {"status": "ok", "flags_stored": count}


@router.put("/flags/{flag_id}/acknowledge")
def acknowledge_flag(
    flag_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.execute("SELECT id FROM analytics_flags WHERE id = ?", (flag_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Flag not found")
    conn.execute("UPDATE analytics_flags SET acknowledged = 1 WHERE id = ?", (flag_id,))
    conn.commit()
    cursor = conn.execute(
        "SELECT id, signal, severity, detail, data, computed_at, acknowledged FROM analytics_flags WHERE id = ?",
        (flag_id,),
    )
    r = dict(cursor.fetchone())
    r["acknowledged"] = bool(r["acknowledged"])
    return r
