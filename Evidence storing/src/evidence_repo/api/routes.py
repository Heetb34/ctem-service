import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..auth import Principal, get_principal, require_roles
from ..config import get_settings
from ..db import get_sessionmaker
from ..schemas import (
    DownloadURL, EvidenceMeta, ListResponse, UploadResponse, VerifyChainResponse, VerifyResult,
)
from .. import service

router = APIRouter()


async def _session() -> AsyncSession:
    async with get_sessionmaker()() as s:
        async with s.begin():
            yield s


@router.post("/evidence", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    file: Annotated[UploadFile, File(...)],
    exposure_id: Annotated[uuid.UUID | None, Form()] = None,
    workflow_execution_id: Annotated[uuid.UUID | None, Form()] = None,
    content_type: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form()] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    principal: Principal = Depends(require_roles("evidence_writer")),
    session: AsyncSession = Depends(_session),
) -> UploadResponse:
    body = await file.read()
    if not body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "empty file")
    try:
        md = json.loads(metadata) if metadata else {}
        if not isinstance(md, dict):
            raise ValueError("metadata must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"bad metadata: {e}") from e

    ct = content_type or file.content_type or "application/octet-stream"
    ev, replayed = await service.upload(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        body=body,
        content_type=ct,
        exposure_id=exposure_id,
        workflow_execution_id=workflow_execution_id,
        metadata=md,
        idempotency_key=idempotency_key,
        retention_days=get_settings().s3_retention_days,
    )
    return UploadResponse(
        evidence_id=ev.evidence_id,
        digest=ev.digest,
        content_sha256=ev.content_sha256,
        idempotent_replay=replayed,
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceMeta)
async def get_evidence(
    evidence_id: uuid.UUID,
    principal: Principal = Depends(require_roles("evidence_writer", "evidence_reader", "auditor")),
    session: AsyncSession = Depends(_session),
) -> EvidenceMeta:
    ev = await service.get_evidence(session, principal.tenant_id, evidence_id)
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return EvidenceMeta.model_validate(ev)


@router.get("/evidence/{evidence_id}/download", response_model=DownloadURL)
async def download(
    evidence_id: uuid.UUID,
    principal: Principal = Depends(require_roles("evidence_writer", "evidence_reader", "auditor")),
    session: AsyncSession = Depends(_session),
) -> DownloadURL:
    ev = await service.get_evidence(session, principal.tenant_id, evidence_id)
    if ev is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    ttl = get_settings().presign_ttl_seconds
    url = await storage.presign_get(ev.s3_key, ev.s3_version_id, ttl)
    return DownloadURL(url=url, expires_in_seconds=ttl)


@router.get("/evidence/{evidence_id}/verify", response_model=VerifyResult)
async def verify_one(
    evidence_id: uuid.UUID,
    principal: Principal = Depends(require_roles("evidence_writer", "evidence_reader", "auditor")),
    session: AsyncSession = Depends(_session),
) -> VerifyResult:
    return await service.verify_one(session, principal.tenant_id, evidence_id)


@router.get("/evidence", response_model=ListResponse)
async def list_evidence(
    exposure_id: uuid.UUID | None = None,
    workflow_execution_id: uuid.UUID | None = None,
    ctem_cycle_id: int | None = Query(None, ge=1),
    ctem_exposure_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=500),
    principal: Principal = Depends(require_roles("evidence_writer", "evidence_reader", "auditor")),
    session: AsyncSession = Depends(_session),
) -> ListResponse:
    rows = await service.list_evidence(
        session,
        principal.tenant_id,
        exposure_id,
        workflow_execution_id,
        limit,
        ctem_cycle_id,
        ctem_exposure_id,
    )
    return ListResponse(items=[EvidenceMeta.model_validate(r) for r in rows])

@router.get("/chains/verify", response_model=VerifyChainResponse)
async def verify_chain(
    principal: Principal = Depends(require_roles("evidence_writer", "evidence_reader", "auditor")),
    session: AsyncSession = Depends(_session),
) -> VerifyChainResponse:
    return await service.verify_chain(session, principal.tenant_id)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(_session)) -> dict[str, str]:
    from sqlalchemy import text as _t

    await session.execute(_t("SELECT 1"))
    return {"status": "ready"}
