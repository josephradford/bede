from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def api(monkeypatch):
    """Mock all HTTP client functions used by server.py tools."""
    mocks = SimpleNamespace(
        get=AsyncMock(),
        post=AsyncMock(),
        put=AsyncMock(),
        delete=AsyncMock(),
    )
    for name in ("get", "post", "put", "delete"):
        monkeypatch.setattr(f"bede_data_mcp.client.{name}", getattr(mocks, name))
    return mocks
