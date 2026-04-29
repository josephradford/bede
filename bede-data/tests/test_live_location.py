import math
from unittest.mock import AsyncMock, patch

import pytest

from bede_data.live.location import (
    GeoCache,
    cluster_points,
    haversine_m,
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


def test_geocache_stores_and_retrieves():
    cache = GeoCache()
    cache.put(-33.8688, 151.2093, "Sydney Opera House")
    assert cache.get(-33.8688, 151.2093) == "Sydney Opera House"


def test_geocache_rounds_coordinates():
    cache = GeoCache()
    cache.put(-33.86881234, 151.20931234, "Sydney Opera House")
    assert cache.get(-33.86889999, 151.20939999) == "Sydney Opera House"


def test_geocache_miss():
    cache = GeoCache()
    assert cache.get(-33.8688, 151.2093) is None
