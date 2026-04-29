from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from bede_data.live.location import (
    cluster_points,
    fetch_owntracks_points,
    reverse_geocode,
)

router = APIRouter(prefix="/api/location", tags=["location"])


def _resolve_date(date_str: str) -> str:
    if date_str == "today":
        return date.today().isoformat()
    if date_str == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return date_str


def _date_to_timestamps(date_str: str) -> tuple[int, int]:
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(d.timestamp()), int((d + timedelta(days=1)).timestamp())


@router.get("/summary")
async def get_location_summary(
    date: str = Query(...),
    tz: str = Query("Australia/Sydney"),
):
    d = _resolve_date(date)
    from_ts, to_ts = _date_to_timestamps(d)
    points = await fetch_owntracks_points(from_ts, to_ts)
    clusters = cluster_points(points)
    tz_info = ZoneInfo(tz)

    stops = []
    for c in clusters:
        name = await reverse_geocode(c["lat"], c["lon"])
        stops.append({
            "name": name,
            "lat": c["lat"],
            "lon": c["lon"],
            "arrived": datetime.fromtimestamp(c["arrived_tst"], tz=tz_info).isoformat() if isinstance(c["arrived_tst"], (int, float)) else c["arrived_tst"],
            "departed": datetime.fromtimestamp(c["departed_tst"], tz=tz_info).isoformat() if isinstance(c["departed_tst"], (int, float)) else c["departed_tst"],
            "point_count": c["point_count"],
        })

    return {"date": d, "stops": stops}


@router.get("/raw")
async def get_location_raw(
    from_date: str = Query(...),
    to_date: str = Query(...),
):
    from_ts, _ = _date_to_timestamps(_resolve_date(from_date))
    _, to_ts = _date_to_timestamps(_resolve_date(to_date))
    points = await fetch_owntracks_points(from_ts, to_ts)
    return {"from_date": from_date, "to_date": to_date, "points": points}
