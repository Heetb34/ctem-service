from sqlalchemy.orm import Session

from app.models.validation_plan import ValidationPlan
from app.models.remediation import RemediationTracking


def create_remediation(
    db: Session,
    cycle_id: int,
    assigned_to: str,
    remediation_status: str,
    completion_date,
    remediation_notes,
):

    validations = (
        db.query(ValidationPlan)
        .filter(
            ValidationPlan.cycle_id == cycle_id,
            ValidationPlan.validation_status == "Scheduled"
        )
        .all()
    )

    if not validations:
        return []

    remediation_list = []

    for validation in validations:

        existing = (
            db.query(RemediationTracking)
            .filter(RemediationTracking.exposure_id == validation.exposure_id)
            .first()
        )

        if existing:
            remediation_list.append(existing)
            continue

        remediation = RemediationTracking(
            cycle_id=cycle_id,
            exposure_id=validation.exposure_id,
            remediation_status=remediation_status,
            assigned_to=assigned_to,
            completion_date=completion_date,
            remediation_notes=remediation_notes
        )

        db.add(remediation)
        db.flush()

        remediation_list.append(remediation)

    db.commit()

    return remediation_list