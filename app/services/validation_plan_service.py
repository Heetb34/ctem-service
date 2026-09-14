from sqlalchemy.orm import Session

from app.models.exposure import Exposure
from app.models.validation_plan import ValidationPlan


def create_validation_plan(db: Session, cycle_id: int):

    exposures = (
        db.query(Exposure)
        .filter(
            Exposure.cycle_id == cycle_id,
            Exposure.priority.in_(["Critical", "High"])
        )
        .all()
    )

    if not exposures:
        return []

    validation_plans = []

    for exposure in exposures:

        # Avoid duplicate validation plans
        existing = (
            db.query(ValidationPlan)
            .filter(
                ValidationPlan.exposure_id == exposure.id
            )
            .first()
        )

        if existing:
            validation_plans.append(existing)
            continue

        # Decide validation type
        if exposure.severity == "Critical":
            validation_type = "Manual Penetration Testing"
        else:
            validation_type = "Automated Validation"

        plan = ValidationPlan(
            cycle_id=cycle_id,
            exposure_id=exposure.id,
            validation_type=validation_type,
            validation_status="Planned",
            remarks="Generated automatically after prioritization"
        )

        db.add(plan)
        db.flush()

        validation_plans.append(plan)

    db.commit()

    return validation_plans