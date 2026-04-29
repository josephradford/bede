import httpx

from bede_data.config import settings


async def fetch_weather() -> dict:
    """Proxy weather data from Homepage API's weather widget (which itself fetches from BOM)."""
    url = f"{settings.homepage_api_url}/api/widgets/weather"
    params = {"location": settings.bom_location} if settings.bom_location else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
