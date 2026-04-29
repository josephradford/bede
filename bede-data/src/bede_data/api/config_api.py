import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/config", tags=["config"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- Schedules ----

class ScheduleCreate(BaseModel):
    task_name: str
    cron_expression: str
    prompt: str
    model: str | None = None
    timeout_seconds: int = 300
    interactive: bool = False
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    cron_expression: str | None = None
    prompt: str | None = None
    model: str | None = None
    timeout_seconds: int | None = None
    interactive: bool | None = None
    enabled: bool | None = None


@router.post("/schedules", status_code=201)
def create_schedule(body: ScheduleCreate, conn: sqlite3.Connection = Depends(get_db)):
    now = _now()
    cursor = conn.execute(
        """INSERT INTO schedules (task_name, cron_expression, prompt, model, timeout_seconds, interactive, enabled, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (body.task_name, body.cron_expression, body.prompt, body.model,
         body.timeout_seconds, int(body.interactive), int(body.enabled), now, now),
    )
    conn.commit()
    return _get_schedule(conn, cursor.lastrowid)


@router.get("/schedules")
def list_schedules(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "SELECT id, task_name, cron_expression, prompt, model, timeout_seconds, interactive, enabled, created_at, updated_at FROM schedules ORDER BY task_name"
    )
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["interactive"] = bool(r["interactive"])
        r["enabled"] = bool(r["enabled"])
    return {"schedules": rows}


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, body: ScheduleUpdate, conn: sqlite3.Connection = Depends(get_db)):
    existing = _get_schedule(conn, schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    updates: dict = {"updated_at": _now()}
    for field in ("cron_expression", "prompt", "model", "timeout_seconds"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = val
    if body.interactive is not None:
        updates["interactive"] = int(body.interactive)
    if body.enabled is not None:
        updates["enabled"] = int(body.enabled)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE schedules SET {set_clause} WHERE id = ?", [*updates.values(), schedule_id])
    conn.commit()
    return _get_schedule(conn, schedule_id)


def _get_schedule(conn: sqlite3.Connection, sid: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, task_name, cron_expression, prompt, model, timeout_seconds, interactive, enabled, created_at, updated_at FROM schedules WHERE id = ?",
        (sid,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    r = dict(row)
    r["interactive"] = bool(r["interactive"])
    r["enabled"] = bool(r["enabled"])
    return r


# ---- Settings (key-value) ----

class SettingValue(BaseModel):
    value: str


@router.put("/settings/{key}")
def set_setting(key: str, body: SettingValue, conn: sqlite3.Connection = Depends(get_db)):
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, body.value, _now()),
    )
    conn.commit()
    return {"key": key, "value": body.value}


@router.get("/settings/{key}")
def get_setting(key: str, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("SELECT key, value, updated_at FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return dict(row)


@router.get("/settings")
def list_settings(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute("SELECT key, value, updated_at FROM settings ORDER BY key")
    return {"settings": [dict(r) for r in cursor.fetchall()]}


# ---- Monitored Items ----

class MonitoredItemCreate(BaseModel):
    category: str
    name: str
    config: str


class MonitoredItemUpdate(BaseModel):
    name: str | None = None
    config: str | None = None
    enabled: bool | None = None


@router.post("/monitored-items", status_code=201)
def create_monitored_item(body: MonitoredItemCreate, conn: sqlite3.Connection = Depends(get_db)):
    now = _now()
    cursor = conn.execute(
        "INSERT INTO monitored_items (category, name, config, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (body.category, body.name, body.config, now, now),
    )
    conn.commit()
    return _get_monitored_item(conn, cursor.lastrowid)


@router.get("/monitored-items")
def list_monitored_items(category: str | None = Query(None), conn: sqlite3.Connection = Depends(get_db)):
    query = "SELECT id, category, name, config, enabled, created_at, updated_at FROM monitored_items WHERE enabled = 1"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY name"
    cursor = conn.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["enabled"] = bool(r["enabled"])
    return {"items": rows}


@router.delete("/monitored-items/{item_id}")
def delete_monitored_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("UPDATE monitored_items SET enabled = 0 WHERE id = ?", (item_id,))
    conn.commit()
    return {"status": "deleted", "id": item_id}


def _get_monitored_item(conn: sqlite3.Connection, item_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, category, name, config, enabled, created_at, updated_at FROM monitored_items WHERE id = ?",
        (item_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    r = dict(row)
    r["enabled"] = bool(r["enabled"])
    return r
