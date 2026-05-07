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
async def test_fetch_air_quality_not_configured():
    from bede_data.live.air_quality import fetch_air_quality

    with patch("bede_data.live.air_quality.settings") as mock_settings:
        mock_settings.air_quality_site_id = 0
        result = await fetch_air_quality()
        assert "error" in result


@pytest.mark.asyncio
async def test_fetch_air_quality():
    from bede_data.live.air_quality import fetch_air_quality

    mock_response = httpx.Response(
        200,
        json=[
            {
                "Site_Id": 919,
                "Parameter": "PM2.5",
                "Date": "2026-05-07",
                "Hour": 14,
                "HourDescription": "2pm",
                "Value": 8.3,
                "AirQualityCategory": "Good",
            },
            {
                "Site_Id": 919,
                "Parameter": "PM10",
                "Date": "2026-05-07",
                "Hour": 14,
                "HourDescription": "2pm",
                "Value": 18.1,
                "AirQualityCategory": "Good",
            },
        ],
        request=httpx.Request("POST", "http://test"),
    )
    with (
        patch("bede_data.live.air_quality.settings") as mock_settings,
        patch("bede_data.live.air_quality.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.air_quality_site_id = 919
        mock_settings.timezone = "Australia/Sydney"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_air_quality()
        assert result["category"] == "Good"
        assert result["site_id"] == 919
        assert "PM2.5" in result["readings"]
        assert result["readings"]["PM2.5"]["value"] == 8.3


@pytest.mark.asyncio
async def test_fetch_air_quality_with_site_id():
    from bede_data.live.air_quality import fetch_air_quality

    mock_response = httpx.Response(
        200,
        json=[
            {
                "Site_Id": 1148,
                "Parameter": "PM2.5",
                "Date": "2026-05-07",
                "Hour": 14,
                "HourDescription": "2pm",
                "Value": 12.0,
                "AirQualityCategory": "Fair",
            },
        ],
        request=httpx.Request("POST", "http://test"),
    )
    with patch("bede_data.live.air_quality.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await fetch_air_quality(site_id="1148")
        assert result["site_id"] == 1148
        assert result["category"] == "Fair"
