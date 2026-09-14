import httpx

async def async_http_call(method: str, url: str, headers: dict = None, json: dict = None, timeout: int = 30):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers, json=json)
        response.raise_for_status()
        return response.json()
