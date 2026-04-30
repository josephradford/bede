import httpx

from bede_data_mcp.config import settings


async def _request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(base_url=settings.bede_data_url, timeout=30.0) as c:
            r = await c.request(method, path, params=params, json=body)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"bede-data returned {e.response.status_code}", "detail": e.response.text}
    except (httpx.ConnectError, httpx.TimeoutException):
        return {"error": "bede-data unavailable"}


async def get(path: str, **params) -> dict:
    p = {k: v for k, v in params.items() if v is not None}
    return await _request("GET", path, params=p)


async def post(path: str, body: dict | None = None) -> dict:
    return await _request("POST", path, body=body)


async def put(path: str, body: dict | None = None) -> dict:
    return await _request("PUT", path, body=body)


async def delete(path: str) -> dict:
    return await _request("DELETE", path)
