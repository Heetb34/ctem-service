from datetime import datetime, timezone
from uuid import UUID, uuid4


def build_exposure_detected_event(
    *, cycle_id: int, exposure, tenant_id: UUID, user_id: str | None = None
) -> dict:
    """Build the versioned, tenant-scoped event consumed by Workflow."""
    return {
        "event_id": str(uuid4()),
        "event_type": "ExposureDetected",
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "cycle_id": cycle_id,
        "severity": (exposure.severity or "").strip().lower(),
        "user_id": user_id,
        "exposure": {
            "id": exposure.id,
            "cycle_id": cycle_id,
            "asset_name": exposure.asset_name,
            "vulnerability": exposure.vulnerability,
            "severity": exposure.severity,
            "risk_score": exposure.risk_score,
            "status": exposure.status,
        },
    }
