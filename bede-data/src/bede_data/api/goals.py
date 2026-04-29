import sqlite3
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/goals", tags=["goals"])


class GoalStatus(str, Enum):
    active = "active"
    completed = "completed"
    dropped = "dropped"


class GoalCreate(BaseModel):
    name: str
    description: str | None = None
    deadline: str | None = None
    measurable_indicators: str | None = None


class GoalUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    deadline: str | None = None
    measurable_indicators: str | None = None
    status: GoalStatus | None = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_goal(conn: sqlite3.Connection, goal_id: int) -> dict:
    cursor = conn.execute(
        "SELECT id, name, description, deadline, measurable_indicators, status, created_at, updated_at FROM goals WHERE id = ?",
        (goal_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return dict(row)


@router.post("", status_code=201)
def create_goal(
    body: GoalCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    now = _now()
    cursor = conn.execute(
        """INSERT INTO goals (name, description, deadline, measurable_indicators, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            body.name,
            body.description,
            body.deadline,
            body.measurable_indicators,
            now,
            now,
        ),
    )
    conn.commit()
    return _get_goal(conn, cursor.lastrowid)


@router.get("")
def list_goals(
    status: GoalStatus | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, name, description, deadline, measurable_indicators, status, created_at, updated_at FROM goals"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status.value)
    query += " ORDER BY created_at DESC"
    cursor = conn.execute(query, params)
    return {"goals": [dict(row) for row in cursor.fetchall()]}


@router.get("/{goal_id}")
def get_goal(
    goal_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    return _get_goal(conn, goal_id)


@router.put("/{goal_id}")
def update_goal(
    goal_id: int,
    body: GoalUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    _get_goal(conn, goal_id)

    updates = {}
    for field in ("name", "description", "deadline", "measurable_indicators"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = val
    if body.status is not None:
        updates["status"] = body.status.value
    updates["updated_at"] = _now()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE goals SET {set_clause} WHERE id = ?",
        [*updates.values(), goal_id],
    )
    conn.commit()
    return _get_goal(conn, goal_id)
