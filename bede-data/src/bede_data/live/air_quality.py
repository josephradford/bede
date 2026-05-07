from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from bede_data.config import settings

OBSERVATIONS_URL = "https://data.airquality.nsw.gov.au/api/Data/get_Observations"
PARAMETERS = ["PM2.5", "PM10", "NO2", "OZONE"]

_CATEGORY_RANKS = {
    "good": 0,
    "fair": 1,
    "poor": 2,
    "very poor": 3,
    "extremely poor": 4,
}


def _normalise_category(cat: str) -> str:
    return cat.strip().title() if cat else ""


async def fetch_air_quality(site_id: str | None = None) -> dict:
    resolved_site = int(site_id) if site_id else settings.air_quality_site_id
    if not resolved_site:
        return {"error": "AIR_QUALITY_SITE_ID not configured"}
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
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
        if obs.get("Value") is None:
            continue
        param_field = obs.get("Parameter", {})
        param = (
            param_field.get("ParameterCode")
            if isinstance(param_field, dict)
            else param_field
        )
        if not param:
            continue
        key = (obs.get("Date", ""), obs.get("Hour", 0))
        prev_key = (
            (latest[param]["_date"], latest[param]["_hour"])
            if param in latest
            else ("", -1)
        )
        if key > prev_key:
            latest[param] = {**obs, "_param": param, "_date": key[0], "_hour": key[1]}

    readings = {}
    worst_category = None
    for param, obs in latest.items():
        cat = _normalise_category(obs.get("AirQualityCategory", ""))
        param_info = obs.get("Parameter", {})
        readings[param] = {
            "value": obs.get("Value"),
            "units": param_info.get("Units") if isinstance(param_info, dict) else None,
            "category": cat or None,
            "hour": obs.get("HourDescription"),
        }
        if cat and (
            worst_category is None
            or _CATEGORY_RANKS.get(cat.lower(), -1)
            > _CATEGORY_RANKS.get(worst_category.lower(), -1)
        ):
            worst_category = cat

    return {
        "site_id": resolved_site,
        "readings": readings,
        "category": worst_category or "Unknown",
        "updated": now.isoformat(),
    }
