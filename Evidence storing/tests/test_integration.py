import io

import pytest

from evidence_repo.hashing import sha256_hex
from evidence_repo.storage import get_bytes
from tests.conftest import auth

@pytest.mark.asyncio
async def test_end_to_end_presign_and_content(client, token):
    payload = b"integration payload"
    files = {"file": ("p.bin", io.BytesIO(payload), "application/octet-stream")}
    r = await client.post("/evidence", files=files, headers=auth(token))
    eid = r.json()["evidence_id"]
    assert r.json()["content_sha256"] == sha256_hex(payload)

    # Fetch the blob back through storage layer (proxy for presigned URL)
    meta = (await client.get(f"/evidence/{eid}", headers=auth(token))).json()
    blob = await get_bytes(meta["s3_key"])
    assert sha256_hex(blob) == meta["content_sha256"]

    # presigned URL is issued
    d = await client.get(f"/evidence/{eid}/download", headers=auth(token))
    assert d.status_code == 200
    assert d.json()["expires_in_seconds"] > 0
