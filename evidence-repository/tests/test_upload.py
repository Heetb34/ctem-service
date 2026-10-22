import io
import uuid

import pytest

from tests.conftest import auth

@pytest.mark.asyncio
async def test_upload_and_fetch(client, token):
    files = {"file": ("ev.txt", io.BytesIO(b"hello"), "text/plain")}
    data = {"metadata": '{"source":"unit"}'}
    r = await client.post("/evidence", files=files, data=data, headers=auth(token))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["idempotent_replay"] is False

    r2 = await client.get(f"/evidence/{body['evidence_id']}", headers=auth(token))
    assert r2.status_code == 200
    m = r2.json()
    assert m["content_sha256"] == body["content_sha256"]
    assert m["metadata"] == {"source": "unit"}

@pytest.mark.asyncio
async def test_idempotent_upload(client, token):
    idem = str(uuid.uuid4())
    files = {"file": ("ev.txt", io.BytesIO(b"once"), "text/plain")}
    h = {**auth(token), "Idempotency-Key": idem}
    r1 = await client.post("/evidence", files=files, headers=h)
    files2 = {"file": ("ev.txt", io.BytesIO(b"once"), "text/plain")}
    r2 = await client.post("/evidence", files=files2, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["evidence_id"] == r2.json()["evidence_id"]
    assert r2.json()["idempotent_replay"] is True

@pytest.mark.asyncio
async def test_exposure_link(client, token):
    eid = uuid.uuid4()
    files = {"file": ("e.txt", io.BytesIO(b"x"), "text/plain")}
    data = {"exposure_id": str(eid)}
    r = await client.post("/evidence", files=files, data=data, headers=auth(token))
    assert r.status_code == 201

    r2 = await client.get(f"/evidence?exposure_id={eid}", headers=auth(token))
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 1
