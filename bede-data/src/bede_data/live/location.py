import math

import httpx

from bede_data.config import settings

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


class GeoCache:
    """In-memory cache for reverse geocode results, keyed by coordinates rounded to `precision` decimal places. Avoids redundant Nominatim calls for nearby points."""

    def __init__(self, precision: int = 3):
        self._cache: dict[tuple[float, float], str] = {}
        self._precision = precision

    def _key(self, lat: float, lon: float) -> tuple[float, float]:
        return (round(lat, self._precision), round(lon, self._precision))

    def get(self, lat: float, lon: float) -> str | None:
        return self._cache.get(self._key(lat, lon))

    def put(self, lat: float, lon: float, name: str) -> None:
        self._cache[self._key(lat, lon)] = name


_geocache = GeoCache()


def cluster_points(
    points: list[dict],
    radius_m: float = 200,
    gap_seconds: int = 300,
) -> list[dict]:
    """Group OwnTracks location points into stops. A new cluster starts when a point is more than radius_m from the current centroid or more than gap_seconds after the last point. The centroid is a running average of all points in the cluster."""
    if not points:
        return []

    sorted_pts = sorted(points, key=lambda p: p["tst"])
    clusters: list[dict] = []
    current = {
        "lat": sorted_pts[0]["lat"],
        "lon": sorted_pts[0]["lon"],
        "arrived_tst": sorted_pts[0]["tst"],
        "departed_tst": sorted_pts[0]["tst"],
        "point_count": 1,
        "lats": [sorted_pts[0]["lat"]],
        "lons": [sorted_pts[0]["lon"]],
    }

    for pt in sorted_pts[1:]:
        dist = haversine_m(current["lat"], current["lon"], pt["lat"], pt["lon"])
        time_gap = pt["tst"] - current["departed_tst"]

        if dist <= radius_m and time_gap <= gap_seconds:
            current["departed_tst"] = pt["tst"]
            current["point_count"] += 1
            current["lats"].append(pt["lat"])
            current["lons"].append(pt["lon"])
            current["lat"] = sum(current["lats"]) / len(current["lats"])
            current["lon"] = sum(current["lons"]) / len(current["lons"])
        else:
            clusters.append(_finish_cluster(current))
            current = {
                "lat": pt["lat"],
                "lon": pt["lon"],
                "arrived_tst": pt["tst"],
                "departed_tst": pt["tst"],
                "point_count": 1,
                "lats": [pt["lat"]],
                "lons": [pt["lon"]],
            }

    clusters.append(_finish_cluster(current))
    return clusters


def _finish_cluster(c: dict) -> dict:
    return {
        "lat": c["lat"],
        "lon": c["lon"],
        "arrived_tst": c["arrived_tst"],
        "departed_tst": c["departed_tst"],
        "point_count": c["point_count"],
    }


class OwnTracksNotConfiguredError(Exception):
    pass


async def fetch_owntracks_points(from_ts: int, to_ts: int) -> list[dict]:
    if not settings.owntracks_user or not settings.owntracks_device:
        raise OwnTracksNotConfiguredError(
            "OWNTRACKS_USER and OWNTRACKS_DEVICE must be set"
        )
    url = f"{settings.owntracks_url}/api/0/locations"
    params = {
        "user": settings.owntracks_user,
        "device": settings.owntracks_device,
        "from": from_ts,
        "to": to_ts,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 416:
            return []
        resp.raise_for_status()
        return resp.json().get("data", [])


async def reverse_geocode(lat: float, lon: float) -> str:
    """Resolve lat/lon to a place name via Nominatim, with GeoCache to deduplicate nearby lookups."""
    cached = _geocache.get(lat, lon)
    if cached:
        return cached
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            settings.nominatim_url,
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 18},
            headers={"User-Agent": "bede-data/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    name = data.get("display_name", f"{lat:.4f}, {lon:.4f}")
    _geocache.put(lat, lon, name)
    return name
