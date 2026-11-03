import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

def _validate_metadata(v: dict[str, Any]) -> dict[str, Any]:
    allowed = (str, int, bool, type(None), float)

    def _walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, val in x.items():
                if not isinstance(k, str):
                    raise ValueError("metadata keys must be strings")
                _walk(val)
        elif isinstance(x, list):
            for val in x:
                _walk(val)
        elif not isinstance(x, allowed):
            raise ValueError(f"unsupported metadata type: {type(x).__name__}")

    _walk(v)
    return v

class EvidenceMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: uuid.UUID
    tenant_id: uuid.UUID
    exposure_id: uuid.UUID | None
    workflow_execution_id: uuid.UUID | None
    content_sha256: str
    size_bytes: int
    content_type: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    s3_key: str
    prev_hash: str
    digest: str
    created_by: uuid.UUID
    created_at: datetime

class VerifyResult(BaseModel):
    ok: bool
    evidence_id: uuid.UUID | None = None
    checked: int = 0
    broken_at: uuid.UUID | None = None
    reason: str | None = None

class DownloadURL(BaseModel):
    url: str
    expires_in_seconds: int

class ListResponse(BaseModel):
    items: list[EvidenceMeta]
    next_cursor: str | None = None

class VerifyChainResponse(BaseModel):
    ok: bool
    chain_length: int
    broken_at: uuid.UUID | None = None
    reason: str | None = None

class UploadResponse(BaseModel):
    evidence_id: uuid.UUID
    digest: str
    content_sha256: str
    idempotent_replay: bool = False

RoleClaim = Literal["evidence_writer", "evidence_reader", "auditor"]
