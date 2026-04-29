from unittest.mock import AsyncMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_fetch_weather():
    from bede_data.live.weather import fetch_weather

    mock_response = httpx.Response(
        200,
        json={
            "current": {"temp_c": 22, "condition": "Sunny"},
            "forecast": [{"date": "2026-04-29", "max": 25, "min": 15}],
        },
        request=httpx.Request("GET", "http://test"),
    )
    with patch("bede_data.live.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_weather()
        assert result["current"]["temp_c"] == 22


@pytest.mark.asyncio
async def test_fetch_air_quality():
    from bede_data.live.air_quality import fetch_air_quality

    mock_response = httpx.Response(
        200,
        json={
            "aqi": 42,
            "category": "Good",
        },
        request=httpx.Request("GET", "http://test"),
    )
    with patch("bede_data.live.air_quality.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_air_quality()
        assert result["aqi"] == 42
