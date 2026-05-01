import re

import httpx
import pytest

from bede_core.data_client import DataClient


@pytest.fixture
def client():
    return DataClient(base_url="http://test:8001")


async def test_get_success(client, httpx_mock):
    httpx_mock.add_response(
        url="http://test:8001/api/health/sleep?date=today",
        json={"sleep": {"duration": 7.5}},
    )
    result = await client.get("/api/health/sleep", date="today")
    assert result == {"sleep": {"duration": 7.5}}


async def test_get_filters_none_params(client, httpx_mock):
    httpx_mock.add_response(
        url=re.compile(r"http://test:8001/api/memories"),
        json={"memories": []},
    )
    await client.get("/api/memories", type=None, search="test")
    request = httpx_mock.get_request()
    assert "type" not in str(request.url)
    assert "search=test" in str(request.url)


async def test_post_success(client, httpx_mock):
    httpx_mock.add_response(
        url="http://test:8001/api/memories",
        json={"id": 1, "content": "test"},
        status_code=201,
    )
    result = await client.post("/api/memories", body={"content": "test", "type": "fact"})
    assert result == {"id": 1, "content": "test"}


async def test_connection_error(client, httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    result = await client.get("/api/health/sleep", date="today")
    assert "error" in result
    assert "unavailable" in result["error"]


async def test_http_error(client, httpx_mock):
    httpx_mock.add_response(
        url="http://test:8001/api/goals/999",
        status_code=404,
        text="Not found",
    )
    result = await client.get("/api/goals/999")
    assert "error" in result
    assert "404" in result["error"]
