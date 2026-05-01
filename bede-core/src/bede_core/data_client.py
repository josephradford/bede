import httpx


class DataClient:
    def __init__(self, base_url: str):
        self._base_url = base_url

    async def _request(
        self, method: str, path: str, params: dict | None = None, body: dict | None = None
    ) -> dict:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as c:
                r = await c.request(method, path, params=params, json=body)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"bede-data returned {e.response.status_code}", "detail": e.response.text}
        except (httpx.ConnectError, httpx.TimeoutException):
            return {"error": "bede-data unavailable"}

    async def get(self, path: str, **params) -> dict:
        p = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", path, params=p)

    async def post(self, path: str, body: dict | None = None) -> dict:
        return await self._request("POST", path, body=body)

    async def put(self, path: str, body: dict | None = None) -> dict:
        return await self._request("PUT", path, body=body)

    async def delete(self, path: str) -> dict:
        return await self._request("DELETE", path)
