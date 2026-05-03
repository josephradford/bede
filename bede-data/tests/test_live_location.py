import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bede_data.live.location import (
    GeoCache,
    OwnTracksNotConfiguredError,
    cluster_points,
    fetch_owntracks_points,
    haversine_m,
    reverse_geocode,
)


def test_haversine_same_point():
    assert haversine_m(-33.8688, 151.2093, -33.8688, 151.2093) == 0.0


def test_haversine_known_distance():
    d = haversine_m(-33.8688, 151.2093, -33.8704, 151.2069)
    assert 200 < d < 400


def test_cluster_points_single_cluster():
    points = [
        {"lat": -33.8688, "lon": 151.2093, "tst": 1000},
        {"lat": -33.8689, "lon": 151.2094, "tst": 1060},
        {"lat": -33.8687, "lon": 151.2092, "tst": 1120},
    ]
    clusters = cluster_points(points, radius_m=200, gap_seconds=300)
    assert len(clusters) == 1
    assert clusters[0]["point_count"] == 3
    assert clusters[0]["arrived_tst"] == 1000
    assert clusters[0]["departed_tst"] == 1120


def test_cluster_points_multiple_clusters():
    points = [
        {"lat": -33.8688, "lon": 151.2093, "tst": 1000},
        {"lat": -33.8689, "lon": 151.2094, "tst": 1060},
        {"lat": -33.9000, "lon": 151.2500, "tst": 2000},
        {"lat": -33.9001, "lon": 151.2501, "tst": 2060},
    ]
    clusters = cluster_points(points, radius_m=200, gap_seconds=300)
    assert len(clusters) == 2


def test_cluster_points_time_gap_splits():
    points = [
        {"lat": -33.8688, "lon": 151.2093, "tst": 1000},
        {"lat": -33.8689, "lon": 151.2094, "tst": 2000},
    ]
    clusters = cluster_points(points, radius_m=200, gap_seconds=300)
    assert len(clusters) == 2


def test_geocache_stores_and_retrieves(tmp_db):
    cache = GeoCache()
    cache.put(-33.8688, 151.2093, "Sydney Opera House")
    assert cache.get(-33.8688, 151.2093) == "Sydney Opera House"


def test_geocache_rounds_coordinates(tmp_db):
    cache = GeoCache()
    cache.put(-33.86881234, 151.20931234, "Sydney Opera House")
    assert cache.get(-33.86889999, 151.20939999) == "Sydney Opera House"


def test_geocache_miss(tmp_db):
    cache = GeoCache()
    assert cache.get(-33.8688, 151.2093) is None


def test_geocache_persists_to_db(tmp_db):
    cache1 = GeoCache()
    cache1.put(-33.8688, 151.2093, "Sydney Opera House")
    cache2 = GeoCache()
    assert cache2.get(-33.8688, 151.2093) == "Sydney Opera House"


@pytest.mark.asyncio
async def test_reverse_geocode_caches_result(tmp_db, monkeypatch):
    import bede_data.live.location as loc

    monkeypatch.setattr(loc, "_geocache", GeoCache())
    monkeypatch.setattr(loc, "_last_nominatim_call", 0.0)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"display_name": "Test Place"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)

    result = await reverse_geocode(-33.8688, 151.2093)
    assert result == "Test Place"
    assert mock_client.get.call_count == 1

    result2 = await reverse_geocode(-33.8688, 151.2093)
    assert result2 == "Test Place"
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_reverse_geocode_fallback_on_error(tmp_db, monkeypatch):
    import bede_data.live.location as loc

    monkeypatch.setattr(loc, "_geocache", GeoCache())
    monkeypatch.setattr(loc, "_last_nominatim_call", 0.0)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("connection failed"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)

    result = await reverse_geocode(-33.8688, 151.2093)
    assert result == "-33.8688, 151.2093"


@pytest.mark.asyncio
async def test_reverse_geocode_fallback_not_cached(tmp_db, monkeypatch):
    import bede_data.live.location as loc

    fresh_cache = GeoCache()
    monkeypatch.setattr(loc, "_geocache", fresh_cache)
    monkeypatch.setattr(loc, "_last_nominatim_call", 0.0)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("connection failed"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)

    await reverse_geocode(-33.8688, 151.2093)
    assert fresh_cache.get(-33.8688, 151.2093) is None


@pytest.mark.asyncio
async def test_reverse_geocode_rate_limits(tmp_db, monkeypatch):
    import bede_data.live.location as loc

    monkeypatch.setattr(loc, "_geocache", GeoCache())
    monkeypatch.setattr(loc, "_last_nominatim_call", 0.0)

    call_times: list[float] = []

    async def tracking_get(*args, **kwargs):
        call_times.append(time.monotonic())
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"display_name": f"Place {len(call_times)}"}
        return resp

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = tracking_get
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)

    await reverse_geocode(-33.8688, 151.2093)
    await reverse_geocode(-34.0000, 150.0000)

    assert len(call_times) == 2
    gap = call_times[1] - call_times[0]
    assert gap >= 0.9


@pytest.mark.asyncio
async def test_fetch_owntracks_raises_when_user_not_configured(monkeypatch):
    from bede_data import config

    monkeypatch.setattr(config.settings, "owntracks_user", "")
    monkeypatch.setattr(config.settings, "owntracks_device", "phone")
    with pytest.raises(OwnTracksNotConfiguredError):
        await fetch_owntracks_points(0, 1000)


@pytest.mark.asyncio
async def test_fetch_owntracks_raises_when_device_not_configured(monkeypatch):
    from bede_data import config

    monkeypatch.setattr(config.settings, "owntracks_user", "joe")
    monkeypatch.setattr(config.settings, "owntracks_device", "")
    with pytest.raises(OwnTracksNotConfiguredError):
        await fetch_owntracks_points(0, 1000)


@pytest.mark.asyncio
async def test_fetch_owntracks_returns_empty_on_416(monkeypatch):
    from unittest.mock import AsyncMock

    from bede_data import config

    monkeypatch.setattr(config.settings, "owntracks_user", "joe")
    monkeypatch.setattr(config.settings, "owntracks_device", "phone")
    monkeypatch.setattr(config.settings, "owntracks_url", "http://owntracks-test:8083")

    mock_response = AsyncMock()
    mock_response.status_code = 416

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)
    result = await fetch_owntracks_points(0, 1000)
    assert result == []
