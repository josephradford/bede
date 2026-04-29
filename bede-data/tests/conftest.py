import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bede_data.app import create_app
from bede_data.config import settings
from bede_data.db.connection import get_db, init_db


@pytest.fixture(autouse=True)
def tmp_db(tmp_path: Path) -> Generator[Path, None, None]:
    db_path = tmp_path / "test.db"
    settings.sqlite_db_path = str(db_path)
    init_db()
    yield db_path


@pytest.fixture
def db(tmp_db: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)
