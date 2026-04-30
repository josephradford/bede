import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from bede_data_mcp import client


async def test_get_filters_none_params():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.request.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client.get("/test", foo="bar", baz=None)

    mock_http.request.assert_called_once_with(
        "GET", "/test", params={"foo": "bar"}, json=None
    )
    assert result == {"ok": True}


async def test_get_connection_error():
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.request.side_effect = httpx.ConnectError("refused")

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client.get("/test")

    assert result["error"] == "bede-data unavailable"


async def test_get_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_response
    )

    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.request.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client.get("/test")

    assert result["error"] == "bede-data returned 500"


async def test_post_sends_body():
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.request.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client.post("/test", {"key": "value"})

    mock_http.request.assert_called_once_with(
        "POST", "/test", params=None, json={"key": "value"}
    )
    assert result == {"id": 1}
