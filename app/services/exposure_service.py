from sqlalchemy.orm import Session

from app.models.exposure import Exposure
from app.schemas.exposure import ExposureCreate


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
    db.commit()
    db.refresh(new_exposure)

    return new_exposure