import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

GENESIS = "GENESIS"

def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON across languages: sorted keys, no whitespace, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_stream(stream, chunk_size: int = 1 << 20) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        h.update(chunk)
        size += len(chunk)
    return h.hexdigest(), size

def rfc3339_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def compute_digest(
    *,
    prev_hash: str,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
    exposure_id: uuid.UUID | None,
    workflow_execution_id: uuid.UUID | None,
    content_sha256: str,
    size_bytes: int,
    content_type: str,
    metadata: dict,
    created_at: datetime,
    created_by: uuid.UUID,
) -> str:
    payload = {
        "prev_hash": prev_hash,
        "tenant_id": str(tenant_id),
        "evidence_id": str(evidence_id),
        "exposure_id": str(exposure_id) if exposure_id else None,
        "workflow_execution_id": str(workflow_execution_id) if workflow_execution_id else None,
        "content_sha256": content_sha256,
        "size_bytes": size_bytes,
        "content_type": content_type,
        "metadata": metadata,
        "created_at": rfc3339_utc(created_at),
        "created_by": str(created_by),
    }
    return sha256_hex(canonical_json(payload))
