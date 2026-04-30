from bede_data_mcp.server import (
    get_air_quality,
    get_location_raw,
    get_location_summary,
    get_weather,
)


async def test_get_location_summary(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "stops": [{"name": "Home", "arrived": "08:00"}],
    }
    result = await get_location_summary("2026-04-30")
    api.get.assert_called_once_with(
        "/api/location/summary", date="2026-04-30", tz="Australia/Sydney"
    )
    assert result["stops"][0]["name"] == "Home"


async def test_get_location_summary_custom_timezone(api):
    api.get.return_value = {"date": "2026-04-30", "stops": []}
    await get_location_summary("2026-04-30", timezone="America/New_York")
    api.get.assert_called_once_with(
        "/api/location/summary", date="2026-04-30", tz="America/New_York"
    )


async def test_get_location_raw(api):
    api.get.return_value = {
        "from_date": "2026-04-29",
        "to_date": "2026-04-30",
        "points": [{"lat": -33.8, "lon": 151.2}],
    }
    result = await get_location_raw("2026-04-29", "2026-04-30")
    api.get.assert_called_once_with(
        "/api/location/raw", from_date="2026-04-29", to_date="2026-04-30"
    )
    assert len(result["points"]) == 1


async def test_get_weather(api):
    api.get.return_value = {"temperature": 22, "conditions": "Partly cloudy"}
    result = await get_weather()
    api.get.assert_called_once_with("/api/weather")
    assert result["temperature"] == 22


async def test_get_air_quality(api):
    api.get.return_value = {"aqi": 42, "category": "Good"}
    result = await get_air_quality()
    api.get.assert_called_once_with("/api/air-quality")
    assert result["aqi"] == 42


async def test_get_air_quality_with_site(api):
    api.get.return_value = {"aqi": 55, "site_id": "parramatta"}
    await get_air_quality(site_id="parramatta")
    api.get.assert_called_once_with("/api/air-quality", site_id="parramatta")
