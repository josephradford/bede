import sqlite3
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryType(str, Enum):
    fact = "fact"
    preference = "preference"
    correction = "correction"
    commitment = "commitment"


class MemoryCreate(BaseModel):
    content: str
    type: MemoryType
    source_conversation: str | None = None
    supersedes: int | None = None


class MemoryUpdate(BaseModel):
    content: str | None = None
    type: MemoryType | None = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.post("", status_code=201)
def create_memory(
    body: MemoryCreate,
    conn: sqlite3.Connection = Depends(get_db),
):
    now = _now()
    cursor = conn.execute(
        """INSERT INTO memories (content, type, source_conversation, created_at)
           VALUES (?, ?, ?, ?)""",
        (body.content, body.type.value, body.source_conversation, now),
    )
    mem_id = cursor.lastrowid

    if body.supersedes is not None:
        conn.execute(
            "UPDATE memories SET active = 0, superseded_by = ? WHERE id = ?",
            (mem_id, body.supersedes),
        )

    conn.commit()
    return _get_memory_by_id(conn, mem_id)


@router.get("")
def list_memories(
    type: MemoryType | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, content, type, created_at, last_referenced_at, source_conversation, superseded_by, active FROM memories WHERE active = 1"
    params: list = []

    if type:
        query += " AND type = ?"
        params.append(type.value)
    if search:
        query += " AND content LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    return {"memories": [dict(row) for row in cursor.fetchall()]}


@router.put("/{memory_id}")
def update_memory(
    memory_id: int,
    body: MemoryUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    existing = _get_memory_by_id(conn, memory_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found")

    updates = {}
    if body.content is not None:
        updates["content"] = body.content
    if body.type is not None:
        updates["type"] = body.type.value

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id = ?",
            [*updates.values(), memory_id],
        )
        conn.commit()

    return _get_memory_by_id(conn, memory_id)


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    conn.execute("UPDATE memories SET active = 0 WHERE id = ?", (memory_id,))
    conn.commit()
    return {"status": "deleted", "id": memory_id}


@router.post("/{memory_id}/reference")
def reference_memory(
    memory_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    now = _now()
    conn.execute(
        "UPDATE memories SET last_referenced_at = ? WHERE id = ?",
        (now, memory_id),
    )
    conn.commit()
    return _get_memory_by_id(conn, memory_id)


def _get_memory_by_id(conn: sqlite3.Connection, memory_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, content, type, created_at, last_referenced_at, source_conversation, superseded_by, active FROM memories WHERE id = ?",
        (memory_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    result = dict(row)
    result["active"] = bool(result["active"])
    return result
