from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from bede_data.config import settings

OBSERVATIONS_URL = "https://data.airquality.nsw.gov.au/api/Data/get_Observations"
PARAMETERS = ["PM2.5", "PM10", "NO2", "OZONE"]

_CATEGORY_RANKS = {
    "Good": 0,
    "Fair": 1,
    "Poor": 2,
    "Very Poor": 3,
    "Extremely Poor": 4,
}


async def fetch_air_quality(site_id: str | None = None) -> dict:
    resolved_site = int(site_id) if site_id else settings.air_quality_site_id
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    start = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
    end = now.strftime("%Y-%m-%dT%H:%M:%S")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            OBSERVATIONS_URL,
            json={
                "Parameters": PARAMETERS,
                "Sites": [resolved_site],
                "StartDate": start,
                "EndDate": end,
                "Categories": ["Averages"],
                "SubCategories": ["Hourly"],
                "Frequency": ["Hourly average"],
            },
        )
        resp.raise_for_status()
        observations = resp.json()

    latest: dict[str, dict] = {}
    for obs in observations:
        param = obs.get("Parameter")
        if not param:
            continue
        key = (obs.get("Date", ""), obs.get("Hour", 0))
        prev_key = (latest[param].get("Date", ""), latest[param].get("Hour", 0)) if param in latest else ("", -1)
        if key > prev_key:
            latest[param] = obs

    readings = {}
    worst_category = None
    for param, obs in latest.items():
        readings[param] = {
            "value": obs.get("Value"),
            "category": obs.get("AirQualityCategory"),
            "hour": obs.get("HourDescription"),
        }
        cat = obs.get("AirQualityCategory")
        if cat and (worst_category is None or _CATEGORY_RANKS.get(cat, -1) > _CATEGORY_RANKS.get(worst_category, -1)):
            worst_category = cat

    return {
        "site_id": resolved_site,
        "readings": readings,
        "category": worst_category or "Unknown",
        "updated": now.isoformat(),
    }
