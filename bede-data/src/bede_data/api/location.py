from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from fastapi.responses import JSONResponse

from bede_data.live.location import (
    OwnTracksNotConfiguredError,
    cluster_points,
    fetch_owntracks_points,
    reverse_geocode,
)

router = APIRouter(prefix="/api/location", tags=["location"])


def _resolve_date(date_str: str, tz: ZoneInfo) -> str:
    if date_str == "today":
        return datetime.now(tz).strftime("%Y-%m-%d")
    if date_str == "yesterday":
        return (datetime.now(tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    return date_str


def _local_day_to_utc_range(date_str: str, tz: ZoneInfo) -> tuple[int, int]:
    """Return (from_ts, to_ts) UTC epoch seconds for a local calendar day."""
    local_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return int(local_start.timestamp()), int(local_end.timestamp())


@router.get("/summary")
async def get_location_summary(
    date: str = Query(...),
    tz: str = Query("Australia/Sydney"),
):
    tz_info = ZoneInfo(tz)
    d = _resolve_date(date, tz_info)
    from_ts, to_ts = _local_day_to_utc_range(d, tz_info)
    try:
        points = await fetch_owntracks_points(from_ts, to_ts)
    except OwnTracksNotConfiguredError as e:
        return JSONResponse(status_code=503, content={"error": str(e)})
    clusters = cluster_points(points)

    stops = []
    for c in clusters:
        name = await reverse_geocode(c["lat"], c["lon"])
        stops.append(
            {
                "name": name,
                "lat": c["lat"],
                "lon": c["lon"],
                "arrived": datetime.fromtimestamp(
                    c["arrived_tst"], tz=tz_info
                ).isoformat()
                if isinstance(c["arrived_tst"], (int, float))
                else c["arrived_tst"],
                "departed": datetime.fromtimestamp(
                    c["departed_tst"], tz=tz_info
                ).isoformat()
                if isinstance(c["departed_tst"], (int, float))
                else c["departed_tst"],
                "point_count": c["point_count"],
            }
        )

    return {"date": d, "stops": stops}


@router.get("/raw")
async def get_location_raw(
    from_date: str = Query(...),
    to_date: str = Query(...),
    tz: str = Query("Australia/Sydney"),
):
    tz_info = ZoneInfo(tz)
    resolved_from = _resolve_date(from_date, tz_info)
    resolved_to = _resolve_date(to_date, tz_info)
    from_ts, _ = _local_day_to_utc_range(resolved_from, tz_info)
    _, to_ts = _local_day_to_utc_range(resolved_to, tz_info)
    try:
        points = await fetch_owntracks_points(from_ts, to_ts)
    except OwnTracksNotConfiguredError as e:
        return JSONResponse(status_code=503, content={"error": str(e)})
    return {"from_date": from_date, "to_date": to_date, "points": points}
