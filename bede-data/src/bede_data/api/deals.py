import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- Price checks ----


class PriceCheckCreate(BaseModel):
    monitored_item_id: int
    url: str
    price: float | None = None
    currency: str = "AUD"
    in_stock: bool | None = None
    notes: str | None = None


@router.post("/price-checks", status_code=201)
def record_price_check(
    body: PriceCheckCreate, conn: sqlite3.Connection = Depends(get_db)
):
    now = _now()
    cursor = conn.execute(
        "INSERT INTO price_history (monitored_item_id, url, price, currency, in_stock, notes, checked_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            body.monitored_item_id,
            body.url,
            body.price,
            body.currency,
            int(body.in_stock) if body.in_stock is not None else None,
            body.notes,
            now,
        ),
    )
    conn.commit()
    return _get_price_check(conn, cursor.lastrowid)


@router.get("/price-history/{item_id}")
def get_price_history(
    item_id: int,
    limit: int = Query(50, ge=1, le=500),
    url: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, monitored_item_id, url, price, currency, in_stock, notes, checked_at FROM price_history WHERE monitored_item_id = ?"
    params: list = [item_id]
    if url:
        query += " AND url = ?"
        params.append(url)
    query += " ORDER BY checked_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        if r["in_stock"] is not None:
            r["in_stock"] = bool(r["in_stock"])
    return {"checks": rows}


def _get_price_check(conn: sqlite3.Connection, check_id: int) -> dict:
    cursor = conn.execute(
        "SELECT id, monitored_item_id, url, price, currency, in_stock, notes, checked_at FROM price_history WHERE id = ?",
        (check_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    r = dict(row)
    if r["in_stock"] is not None:
        r["in_stock"] = bool(r["in_stock"])
    return r


# ---- Dead URLs ----


class DeadUrlReport(BaseModel):
    url: str
    category: str | None = None
    last_error: str | None = None


class DeadUrlUpdate(BaseModel):
    disabled: bool | None = None
    last_error: str | None = None


@router.post("/dead-urls", status_code=201)
def report_dead_url(body: DeadUrlReport, conn: sqlite3.Connection = Depends(get_db)):
    now = _now()
    existing = conn.execute(
        "SELECT id, fail_count FROM dead_urls WHERE url = ?", (body.url,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE dead_urls SET fail_count = fail_count + 1, last_error = ?, checked_at = ? WHERE id = ?",
            (body.last_error, now, existing["id"]),
        )
        conn.commit()
        return JSONResponse(content=_get_dead_url(conn, existing["id"]), status_code=200)

    cursor = conn.execute(
        "INSERT INTO dead_urls (url, category, last_error, first_seen, checked_at) VALUES (?, ?, ?, ?, ?)",
        (body.url, body.category, body.last_error, now, now),
    )
    conn.commit()
    return _get_dead_url(conn, cursor.lastrowid)


@router.get("/dead-urls")
def list_dead_urls(
    category: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, url, category, fail_count, last_error, first_seen, checked_at, disabled FROM dead_urls WHERE disabled = 0"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY checked_at DESC"
    cursor = conn.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["disabled"] = bool(r["disabled"])
    return {"urls": rows}


@router.put("/dead-urls/{url_id}")
def update_dead_url(
    url_id: int, body: DeadUrlUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    existing = _get_dead_url(conn, url_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Dead URL not found")

    updates: dict = {}
    if body.disabled is not None:
        updates["disabled"] = int(body.disabled)
    if body.last_error is not None:
        updates["last_error"] = body.last_error

    if not updates:
        return _get_dead_url(conn, url_id)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE dead_urls SET {set_clause} WHERE id = ?",
        [*updates.values(), url_id],
    )
    conn.commit()
    return _get_dead_url(conn, url_id)


def _get_dead_url(conn: sqlite3.Connection, url_id: int) -> dict:
    cursor = conn.execute(
        "SELECT id, url, category, fail_count, last_error, first_seen, checked_at, disabled FROM dead_urls WHERE id = ?",
        (url_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    r = dict(row)
    r["disabled"] = bool(r["disabled"])
    return r
