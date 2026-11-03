import asyncio
from sqlalchemy import select
from evidence_repo.db import get_engine
from evidence_repo.models import Evidence

IDS = [
    "dcc6ed43-dfc4-4808-b481-3a509e45fcc2",
    "89842f82-8702-4648-baf2-487961bb6272",
    "62639def-51ce-4904-abde-8a90e95717fa",
    "844418fb-91df-4097-8e7c-7a3e42078d07",
]

async def main():
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                select(Evidence.__table__).where(
                    Evidence.__table__.c.evidence_id.in_(IDS)
                )
            )
            for row in result.mappings().all():
                print("\n---", row["evidence_id"], "---")
                for key in (
                    "tenant_id", "prev_hash", "content_sha256",
                    "size_bytes", "content_type", "metadata_json",
                    "created_at", "created_by", "digest",
                ):
                    print(f"{key}: {row[key]!r}")
    finally:
        await engine.dispose()

asyncio.run(main())
