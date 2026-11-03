import asyncio

from sqlalchemy import select

from evidence_repo.db import get_engine
from evidence_repo.hashing import compute_digest
from evidence_repo.models import Evidence


async def main():
    engine = get_engine()

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                select(Evidence.__table__).order_by(
                    Evidence.__table__.c.created_at
                )
            )
            rows = result.mappings().all()

        mismatches = []

        for row in rows:
            calculated = compute_digest(
                prev_hash=row["prev_hash"],
                tenant_id=row["tenant_id"],
                evidence_id=row["evidence_id"],
                exposure_id=row["exposure_id"],
                workflow_execution_id=row["workflow_execution_id"],
                content_sha256=row["content_sha256"],
                size_bytes=row["size_bytes"],
                content_type=row["content_type"],
                metadata=row["metadata_json"],
                created_at=row["created_at"],
                created_by=row["created_by"],
            )

            if calculated != row["digest"]:
                mismatches.append(
                    (
                        row["evidence_id"],
                        row["created_at"],
                        row["digest"],
                        calculated,
                    )
                )

        print(f"Total records checked: {len(rows)}")
        print(f"Digest mismatches: {len(mismatches)}")

        for evidence_id, created_at, stored, calculated in mismatches[:20]:
            print(f"\nEvidence ID: {evidence_id}")
            print(f"Created at: {created_at}")
            print(f"Stored digest: {stored}")
            print(f"Calculated digest: {calculated}")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())