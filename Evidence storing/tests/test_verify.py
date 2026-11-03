import io

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.conftest import auth
from evidence_repo.db import get_sessionmaker


async def _upload(client, token, content: bytes) -> str:
    files = {
        "file": ("ev.txt", io.BytesIO(content), "text/plain")
    }

    response = await client.post(
        "/evidence",
        files=files,
        headers=auth(token),
    )

    assert response.status_code == 201, response.text
    return response.json()["evidence_id"]


@pytest.mark.asyncio
async def test_application_cannot_tamper_with_evidence(client, token):
    eid = await _upload(client, token, b"tamperme")

    # The restricted application account must not modify evidence.
    with pytest.raises(
        DBAPIError,
        match="permission denied for table evidence",
    ):
        async with get_sessionmaker()() as session:
            async with session.begin():
                await session.execute(
                    text("""
                        UPDATE evidence
                        SET metadata_json = CAST(:metadata AS jsonb)
                        WHERE evidence_id = :id
                    """),
                    {
                        "metadata": '{"tampered":true}',
                        "id": eid,
                    },
                )

    # The denied modification must leave the hash chain valid.
    response = await client.get(
        "/chains/verify",
        headers=auth(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True