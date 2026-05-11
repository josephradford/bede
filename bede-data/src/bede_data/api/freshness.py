import sqlite3
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends

from bede_data.config import settings
from bede_data.db.connection import get_db

router = APIRouter(prefix="/api/freshness", tags=["freshness"])


def _fetch_owntracks_freshness() -> dict | None:
    try:
        resp = httpx.get(
            f"{settings.owntracks_url}/api/0/last",
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            tst = data[0].get("tst")
        elif isinstance(data, dict):
            tst = data.get("tst")
        else:
            return None
        if tst is None:
            return None
        last_received = datetime.fromtimestamp(tst, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return {
            "source": "owntracks",
            "last_received_at": last_received,
            "expected_interval_seconds": 3600,
            "always_expected": 1,
            "updated_at": None,
        }
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None


@router.get("")
def get_freshness(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "SELECT source, last_received_at, expected_interval_seconds, always_expected, updated_at FROM data_freshness ORDER BY source"
    )
    sources = [dict(r) for r in cursor.fetchall()]

    owntracks = _fetch_owntracks_freshness()
    if owntracks is not None:
        sources.append(owntracks)
        sources.sort(key=lambda s: s["source"])

    return {"sources": sources}
