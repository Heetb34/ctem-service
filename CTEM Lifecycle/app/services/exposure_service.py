from sqlalchemy.orm import Session

from app.models.exposure import Exposure
from app.models.outbox_event import OutboxEvent
from app.schemas.exposure import ExposureCreate
from app.services.exposure_event_service import build_exposure_detected_event


def create_exposure(
    db: Session,
    cycle_id: int,
    exposure: ExposureCreate
):

    new_exposure = Exposure(
        cycle_id=cycle_id,
        asset_name=exposure.asset_name,
        vulnerability=exposure.vulnerability,
        severity=exposure.severity,
        risk_score=exposure.risk_score
    )

    db.add(new_exposure)
    db.flush()

    if exposure.tenant_id is not None:
        event = build_exposure_detected_event(
            cycle_id=cycle_id,
            exposure=new_exposure,
            tenant_id=exposure.tenant_id,
            user_id=exposure.user_id,
        )
        db.add(
            OutboxEvent(
                event_id=event["event_id"],
                topic="exposure-events",
                payload=event,
            )
        )

    db.commit()
    db.refresh(new_exposure)

    return new_exposure

def get_exposures(db: Session, cycle_id: int):
    return (
        db.query(Exposure)
        .filter(Exposure.cycle_id == cycle_id)
        .all()
    )
