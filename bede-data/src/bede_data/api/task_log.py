import sqlite3
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskStatus(str, Enum):
    running = "running"
    success = "success"
    failure = "failure"
    timeout = "timeout"


class TaskLogCreate(BaseModel):
    task_name: str
    start_time: str
    status: TaskStatus


class TaskLogUpdate(BaseModel):
    status: TaskStatus | None = None
    end_time: str | None = None
    duration_seconds: float | None = None
    error_detail: str | None = None


@router.post("/log", status_code=201)
def log_task(
    body: TaskLogCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    cursor = conn.execute(
        "INSERT INTO task_executions (task_name, start_time, status) VALUES (?, ?, ?)",
        (body.task_name, body.start_time, body.status.value),
    )
    conn.commit()
    return _get_execution(conn, cursor.lastrowid)


@router.put("/log/{execution_id}")
def update_task_log(
    execution_id: int,
    body: TaskLogUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    existing = _get_execution(conn, execution_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Execution not found")

    updates = {}
    if body.status is not None:
        updates["status"] = body.status.value
    if body.end_time is not None:
        updates["end_time"] = body.end_time
    if body.duration_seconds is not None:
        updates["duration_seconds"] = body.duration_seconds
    if body.error_detail is not None:
        updates["error_detail"] = body.error_detail

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE task_executions SET {set_clause} WHERE id = ?",
            [*updates.values(), execution_id],
        )
        conn.commit()

    return _get_execution(conn, execution_id)


@router.get("/history")
def get_task_history(
    task_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, task_name, start_time, end_time, duration_seconds, status, error_detail, created_at FROM task_executions"
    params: list = []
    if task_name:
        query += " WHERE task_name = ?"
        params.append(task_name)
    query += " ORDER BY start_time DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(query, params)
    return {"executions": [dict(row) for row in cursor.fetchall()]}


def _get_execution(conn: sqlite3.Connection, exec_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, task_name, start_time, end_time, duration_seconds, status, error_detail, created_at FROM task_executions WHERE id = ?",
        (exec_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None
