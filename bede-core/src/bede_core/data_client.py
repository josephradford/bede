import httpx


class DataClient:
    def __init__(self, base_url: str):
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict:
        try:
            client = self._get_client()
            r = await client.request(method, path, params=params, json=body)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"bede-data returned {e.response.status_code}",
                "detail": e.response.text,
            }
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
