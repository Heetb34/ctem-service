import uuid
from datetime import datetime, timezone

from evidence_repo.hashing import canonical_json, compute_digest

def test_canonical_json_deterministic():
    a = {"b": 1, "a": [2, 3], "c": {"z": True, "y": None}}
    b = {"a": [2, 3], "c": {"y": None, "z": True}, "b": 1}
    assert canonical_json(a) == canonical_json(b)

def test_digest_is_deterministic():
    kw = dict(
        prev_hash="GENESIS",
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        evidence_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        exposure_id=None,
        workflow_execution_id=None,
        content_sha256="a" * 64,
        size_bytes=5,
        content_type="text/plain",
        metadata={"k": "v"},
        created_at=datetime(2026, 1, 5, 12, 0, 0, 123456, tzinfo=timezone.utc),
        created_by=uuid.UUID("22222222-2222-2222-2222-222222222222"),
    )
    assert compute_digest(**kw) == compute_digest(**kw)

def test_digest_changes_when_field_changes():
    base = dict(
        prev_hash="GENESIS",
        tenant_id=uuid.uuid4(),
        evidence_id=uuid.uuid4(),
        exposure_id=None,
        workflow_execution_id=None,
        content_sha256="a" * 64,
        size_bytes=5,
        content_type="text/plain",
        metadata={"k": "v"},
        created_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        created_by=uuid.uuid4(),
    )
    d1 = compute_digest(**base)
    base["size_bytes"] = 6
    d2 = compute_digest(**base)
    assert d1 != d2
