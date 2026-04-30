import sqlite3
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/vault-queue", tags=["vault-queue"])


class QueueStatus(str, Enum):
    pending = "pending"
    published = "published"
    failed = "failed"


class QueueItemCreate(BaseModel):
    content_type: str
    content: str
    vault_path: str | None = None


class QueueItemUpdate(BaseModel):
    status: QueueStatus
    error_detail: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.post("", status_code=201)
def enqueue(body: QueueItemCreate, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "INSERT INTO vault_publish_queue (content_type, content, vault_path, created_at) VALUES (?, ?, ?, ?)",
        (body.content_type, body.content, body.vault_path, _now()),
    )
    conn.commit()
    return _get_item(conn, cursor.lastrowid)


@router.get("")
def list_queue(
    status: QueueStatus | None = Query(None),
    limit: int = Query(50),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, content_type, content, vault_path, status, error_detail, created_at, published_at FROM vault_publish_queue"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status.value)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(query, params)
    return {"items": [dict(r) for r in cursor.fetchall()]}


@router.put("/{item_id}")
def update_queue_item(
    item_id: int,
    body: QueueItemUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    existing = _get_item(conn, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Queue item not found")

    published_at = _now() if body.status == QueueStatus.published else None
    conn.execute(
        "UPDATE vault_publish_queue SET status = ?, error_detail = ?, published_at = COALESCE(?, published_at) WHERE id = ?",
        (body.status.value, body.error_detail, published_at, item_id),
    )
    conn.commit()
    return _get_item(conn, item_id)


def _get_item(conn: sqlite3.Connection, item_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, content_type, content, vault_path, status, error_detail, created_at, published_at FROM vault_publish_queue WHERE id = ?",
        (item_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None
