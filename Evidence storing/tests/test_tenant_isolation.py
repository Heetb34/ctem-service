import io

import pytest

from evidence_repo.auth import mint_dev_token
from tests.conftest import auth

@pytest.mark.asyncio
async def test_cross_tenant_read_forbidden(client, token):
    files = {"file": ("a.bin", io.BytesIO(b"private"), "application/octet-stream")}
    r = await client.post("/evidence", files=files, headers=auth(token))
    eid = r.json()["evidence_id"]

    other = mint_dev_token("99999999-9999-9999-9999-999999999999", "88888888-8888-8888-8888-888888888888")
    r2 = await client.get(f"/evidence/{eid}", headers=auth(other))
    assert r2.status_code == 404
