import sqlite3
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/message-queue", tags=["message-queue"])


class MsgStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class MsgCreate(BaseModel):
    message: str
    source: str


class MsgUpdate(BaseModel):
    status: MsgStatus


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.post("", status_code=201)
def enqueue_message(body: MsgCreate, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "INSERT INTO message_queue (message, source, created_at) VALUES (?, ?, ?)",
        (body.message, body.source, _now()),
    )
    conn.commit()
    return _get_msg(conn, cursor.lastrowid)


@router.get("")
def list_messages(
    status: MsgStatus | None = Query(None),
    limit: int = Query(50),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, message, source, status, created_at, processed_at FROM message_queue"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status.value)
    query += " ORDER BY created_at ASC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(query, params)
    return {"messages": [dict(r) for r in cursor.fetchall()]}


@router.put("/{msg_id}")
def update_message(msg_id: int, body: MsgUpdate, conn: sqlite3.Connection = Depends(get_db)):
    existing = _get_msg(conn, msg_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Message not found")
    processed_at = _now() if body.status in (MsgStatus.done, MsgStatus.failed) else None
    conn.execute(
        "UPDATE message_queue SET status = ?, processed_at = COALESCE(?, processed_at) WHERE id = ?",
        (body.status.value, processed_at, msg_id),
    )
    conn.commit()
    return _get_msg(conn, msg_id)


def _get_msg(conn: sqlite3.Connection, msg_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, message, source, status, created_at, processed_at FROM message_queue WHERE id = ?",
        (msg_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None
