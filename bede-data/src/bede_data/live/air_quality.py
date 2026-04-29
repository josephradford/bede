import httpx


AIR_QUALITY_URL = "https://data.airquality.nsw.gov.au/api/Data/get_SiteDetails"


async def fetch_air_quality(site_id: str | None = None) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(AIR_QUALITY_URL)
        resp.raise_for_status()
        return resp.json()
