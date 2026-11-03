import asyncio
import io

import pytest

from tests.conftest import auth

@pytest.mark.asyncio
async def test_concurrent_appends_no_fork(client, token):
    async def _up(i: int):
        files = {"file": (f"e{i}.bin", io.BytesIO(f"payload-{i}".encode()), "application/octet-stream")}
        return await client.post("/evidence", files=files, headers=auth(token))

    results = await asyncio.gather(*[_up(i) for i in range(20)])
    assert all(r.status_code == 201 for r in results), [r.text for r in results if r.status_code != 201]

    # Chain must be intact
    r = await client.get("/chains/verify", headers=auth(token))
    assert r.json()["ok"] is True, r.json()
    assert r.json()["chain_length"] >= 20
