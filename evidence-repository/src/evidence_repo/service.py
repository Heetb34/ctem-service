
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from . import storage
from .events import publish
from .hashing import GENESIS, compute_digest, sha256_hex
from .logging import log
from .models import ChainHead, Evidence
from .schemas import VerifyChainResponse, VerifyResult


class ConflictError(Exception):
    pass


async def _get_or_init_head(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> ChainHead:
    # Lock the chain head row for this tenant.
    await session.execute(
        text(
            "INSERT INTO chain_heads"
            "(tenant_id, head_hash, head_evidence_id, chain_length) "
            "VALUES (:t, :h, NULL, 0) "
            "ON CONFLICT (tenant_id) DO NOTHING"
        ),
        {"t": str(tenant_id), "h": GENESIS},
    )

    row = (
        await session.execute(
            select(ChainHead)
            .where(ChainHead.tenant_id == tenant_id)
            .with_for_update()
        )
    ).scalar_one()

    return row


async def _find_by_idem(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    idem_key: str,
) -> Evidence | None:
    return (
        await session.execute(
            select(Evidence).where(
                Evidence.tenant_id == tenant_id,
                Evidence.idempotency_key == idem_key,
            )
        )
    ).scalar_one_or_none()


async def upload(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    body: bytes,
    content_type: str,
    exposure_id: uuid.UUID | None,
    workflow_execution_id: uuid.UUID | None,
    metadata: dict[str, Any],
    idempotency_key: str | None,
    retention_days: int,
) -> tuple[Evidence, bool]:

    if idempotency_key:
        existing = await _find_by_idem(
            session,
            tenant_id,
            idempotency_key,
        )
        if existing is not None:
            return existing, True

    content_sha256 = sha256_hex(body)
    size = len(body)
    evidence_id = uuid.uuid4()

    head = await _get_or_init_head(session, tenant_id)

    # Generate the timestamp after acquiring the chain lock.
    created_at = datetime.now(timezone.utc)
    prev_hash = head.head_hash

    digest = compute_digest(
        prev_hash=prev_hash,
        tenant_id=tenant_id,
        evidence_id=evidence_id,
        exposure_id=exposure_id,
        workflow_execution_id=workflow_execution_id,
        content_sha256=content_sha256,
        size_bytes=size,
        content_type=content_type,
        metadata=metadata,
        created_at=created_at,
        created_by=user_id,
    )

    key = storage.build_key(tenant_id, evidence_id)

    version_id = await storage.put_immutable(
        key,
        body,
        content_type,
        retention_days,
    )

    ev = Evidence(
        evidence_id=evidence_id,
        tenant_id=tenant_id,
        exposure_id=exposure_id,
        workflow_execution_id=workflow_execution_id,
        content_sha256=content_sha256,
        size_bytes=size,
        content_type=content_type,
        metadata_json=metadata,
        s3_key=key,
        s3_version_id=version_id or None,
        prev_hash=prev_hash,
        digest=digest,
        idempotency_key=idempotency_key,
        created_by=user_id,
        created_at=created_at,
    )

    session.add(ev)

    head.head_hash = digest
    head.head_evidence_id = evidence_id
    head.chain_length = head.chain_length + 1
    head.updated_at = created_at

    await session.flush()

    await publish(
        "EvidenceUploaded",
        tenant_id,
        {
            "evidence_id": str(evidence_id),
            "content_sha256": content_sha256,
            "size_bytes": size,
            "exposure_id": (
                str(exposure_id) if exposure_id else None
            ),
            "workflow_execution_id": (
                str(workflow_execution_id)
                if workflow_execution_id else None
            ),
        },
    )

    log.info(
        "evidence_uploaded",
        evidence_id=str(evidence_id),
        tenant_id=str(tenant_id),
    )

    return ev, False


async def get_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> Evidence | None:
    return (
        await session.execute(
            select(Evidence).where(
                Evidence.tenant_id == tenant_id,
                Evidence.evidence_id == evidence_id,
            )
        )
    ).scalar_one_or_none()


async def list_evidence(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    exposure_id: uuid.UUID | None,
    workflow_execution_id: uuid.UUID | None,
    limit: int,
    ctem_cycle_id: int | None = None,
    ctem_exposure_id: int | None = None,
) -> list[Evidence]:

    q = select(Evidence).where(
        Evidence.tenant_id == tenant_id
    )

    if exposure_id:
        q = q.where(
            Evidence.exposure_id == exposure_id
        )

    if workflow_execution_id:
        q = q.where(
            Evidence.workflow_execution_id == workflow_execution_id
        )

    if ctem_cycle_id is not None:
        q = q.where(
            Evidence.metadata_json["ctem_cycle_id"].astext
            == str(ctem_cycle_id)
        )

    if ctem_exposure_id is not None:
        q = q.where(
            Evidence.metadata_json["ctem_exposure_id"].astext
            == str(ctem_exposure_id)
        )

    q = q.order_by(
        Evidence.created_at.desc()
    ).limit(limit)

    return list(
        (await session.execute(q)).scalars().all()
    )

async def verify_one(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
) -> VerifyResult:

    ev = await get_evidence(
        session,
        tenant_id,
        evidence_id,
    )

    if ev is None:
        return VerifyResult(
            ok=False,
            reason="not_found",
            evidence_id=evidence_id,
        )

    recomputed = compute_digest(
        prev_hash=ev.prev_hash,
        tenant_id=ev.tenant_id,
        evidence_id=ev.evidence_id,
        exposure_id=ev.exposure_id,
        workflow_execution_id=ev.workflow_execution_id,
        content_sha256=ev.content_sha256,
        size_bytes=ev.size_bytes,
        content_type=ev.content_type,
        metadata=ev.metadata_json,
        created_at=ev.created_at,
        created_by=ev.created_by,
    )

    if recomputed != ev.digest:
        await publish(
            "EvidenceTampered",
            tenant_id,
            {
                "evidence_id": str(evidence_id),
                "reason": "digest_mismatch",
            },
        )

        return VerifyResult(
            ok=False,
            evidence_id=evidence_id,
            checked=1,
            broken_at=evidence_id,
            reason="digest_mismatch",
        )

    try:
        blob = await storage.get_bytes(
            ev.s3_key,
            ev.s3_version_id,
        )

    except Exception as e:
        await publish(
            "EvidenceTampered",
            tenant_id,
            {
                "evidence_id": str(evidence_id),
                "reason": f"s3_error:{e}",
            },
        )

        return VerifyResult(
            ok=False,
            evidence_id=evidence_id,
            checked=1,
            broken_at=evidence_id,
            reason="s3_unreadable",
        )

    if sha256_hex(blob) != ev.content_sha256:
        await publish(
            "EvidenceTampered",
            tenant_id,
            {
                "evidence_id": str(evidence_id),
                "reason": "content_mismatch",
            },
        )

        return VerifyResult(
            ok=False,
            evidence_id=evidence_id,
            checked=1,
            broken_at=evidence_id,
            reason="content_mismatch",
        )

    await publish(
        "EvidenceVerified",
        tenant_id,
        {"evidence_id": str(evidence_id)},
    )

    return VerifyResult(
        ok=True,
        evidence_id=evidence_id,
        checked=1,
    )


async def verify_chain(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> VerifyChainResponse:

    rows = list(
        (
            await session.execute(
                select(Evidence).where(
                    Evidence.tenant_id == tenant_id
                )
            )
        )
        .scalars()
        .all()
    )

    head = (
        await session.execute(
            select(ChainHead).where(
                ChainHead.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()

    def failed(
        reason: str,
        broken_at: uuid.UUID | None = None,
    ) -> VerifyChainResponse:
        return VerifyChainResponse(
            ok=False,
            chain_length=len(rows),
            broken_at=broken_at,
            reason=reason,
        )

    # Handle an empty evidence chain.
    if not rows:
        if head is not None and (
            head.chain_length != 0
            or head.head_hash != GENESIS
            or head.head_evidence_id is not None
        ):
            return failed("head_mismatch")

        return VerifyChainResponse(
            ok=True,
            chain_length=0,
        )

    # Build a lookup using the previous hash.
    links: dict[str, Evidence] = {}

    for ev in rows:
        if ev.prev_hash in links:
            await publish(
                "EvidenceTampered",
                tenant_id,
                {
                    "evidence_id": str(ev.evidence_id),
                    "reason": "chain_fork",
                },
            )

            return failed(
                "chain_fork",
                ev.evidence_id,
            )

        links[ev.prev_hash] = ev

    # Follow the actual chain from GENESIS.
    expected_prev = GENESIS
    visited: set[uuid.UUID] = set()
    last_evidence_id: uuid.UUID | None = None

    for _ in range(len(rows)):
        ev = links.get(expected_prev)

        if ev is None:
            await publish(
                "EvidenceTampered",
                tenant_id,
                {
                    "reason": "prev_hash_mismatch",
                },
            )

            return failed("prev_hash_mismatch")

        if ev.evidence_id in visited:
            return failed(
                "chain_cycle",
                ev.evidence_id,
            )

        visited.add(ev.evidence_id)

        recomputed = compute_digest(
            prev_hash=ev.prev_hash,
            tenant_id=ev.tenant_id,
            evidence_id=ev.evidence_id,
            exposure_id=ev.exposure_id,
            workflow_execution_id=ev.workflow_execution_id,
            content_sha256=ev.content_sha256,
            size_bytes=ev.size_bytes,
            content_type=ev.content_type,
            metadata=ev.metadata_json,
            created_at=ev.created_at,
            created_by=ev.created_by,
        )

        if recomputed != ev.digest:
            await publish(
                "EvidenceTampered",
                tenant_id,
                {
                    "evidence_id": str(ev.evidence_id),
                    "reason": "digest_mismatch",
                },
            )

            return failed(
                "digest_mismatch",
                ev.evidence_id,
            )

        expected_prev = ev.digest
        last_evidence_id = ev.evidence_id

    # Confirm that every record was visited.
    if len(visited) != len(rows):
        return failed("chain_length_mismatch")

    # Confirm that the stored chain head is correct.
    if head is None:
        return failed("head_missing")

    if (
        head.head_hash != expected_prev
        or head.chain_length != len(rows)
        or head.head_evidence_id != last_evidence_id
    ):
        return failed("head_mismatch")

    return VerifyChainResponse(
        ok=True,
        chain_length=len(rows),
    )
