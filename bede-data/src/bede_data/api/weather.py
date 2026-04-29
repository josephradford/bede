from fastapi import APIRouter

from bede_data.live.air_quality import fetch_air_quality
from bede_data.live.weather import fetch_weather

router = APIRouter(prefix="/api", tags=["weather"])


@router.get("/weather")
async def get_weather():
    return await fetch_weather()


@router.get("/air-quality")
async def get_air_quality(site_id: str | None = None):
    return await fetch_air_quality(site_id)
