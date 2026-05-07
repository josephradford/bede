import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/news", tags=["news"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArticleCreate(BaseModel):
    url: str
    title: str
    source_name: str
    category: str | None = None
    summary: str | None = None


class DigestMark(BaseModel):
    digest_date: str


@router.post("/articles", status_code=201)
def save_article(body: ArticleCreate, conn: sqlite3.Connection = Depends(get_db)):
    existing = conn.execute(
        "SELECT id, url, title, source_name, category, summary, fetched_at, digest_date FROM articles WHERE url = ?",
        (body.url,),
    ).fetchone()
    if existing:
        r = dict(existing)
        r["already_existed"] = True
        return JSONResponse(content=r, status_code=200)

    now = _now()
    cursor = conn.execute(
        "INSERT INTO articles (url, title, source_name, category, summary, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
        (body.url, body.title, body.source_name, body.category, body.summary, now),
    )
    conn.commit()
    return _get_article(conn, cursor.lastrowid)


@router.get("/articles")
def list_articles(
    category: str | None = Query(None),
    source_name: str | None = Query(None),
    unsent: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
):
    query = "SELECT id, url, title, source_name, category, summary, fetched_at, digest_date FROM articles WHERE 1=1"
    params: list = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if source_name:
        query += " AND source_name = ?"
        params.append(source_name)
    if unsent:
        query += " AND digest_date IS NULL"
    query += " ORDER BY fetched_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(query, params)
    return {"articles": [dict(r) for r in cursor.fetchall()]}


@router.get("/articles/exists")
def check_article_exists(
    url: str = Query(...), conn: sqlite3.Connection = Depends(get_db)
):
    row = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,)).fetchone()
    return {"exists": row is not None, "url": url}


@router.put("/articles/{article_id}/digest")
def mark_article_in_digest(
    article_id: int, body: DigestMark, conn: sqlite3.Connection = Depends(get_db)
):
    existing = _get_article(conn, article_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Article not found")
    conn.execute(
        "UPDATE articles SET digest_date = ? WHERE id = ?",
        (body.digest_date, article_id),
    )
    conn.commit()
    return _get_article(conn, article_id)


def _get_article(conn: sqlite3.Connection, article_id: int) -> dict | None:
    cursor = conn.execute(
        "SELECT id, url, title, source_name, category, summary, fetched_at, digest_date FROM articles WHERE id = ?",
        (article_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return dict(row)
