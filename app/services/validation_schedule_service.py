from sqlalchemy.orm import Session

from app.models.validation_plan import ValidationPlan


def schedule_validation(
    db: Session,
    cycle_id: int,
    assigned_to: str,
    planned_date
):

    plans = (
        db.query(ValidationPlan)
        .filter(ValidationPlan.cycle_id == cycle_id)
        .all()
    )

    if not plans:
        return []

    for plan in plans:
        plan.assigned_to = assigned_to
        plan.planned_date = planned_date
        plan.validation_status = "Scheduled"

    db.commit()

    return plans