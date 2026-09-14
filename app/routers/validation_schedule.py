from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.validation_schedule import (
    ValidationScheduleRequest,
    ValidationScheduleResponse,
)
from app.services.validation_schedule_service import schedule_validation

router = APIRouter(
    prefix="/ctem",
    tags=["Validation Scheduling"]
)


@router.post(
    "/cycles/{cycle_id}/validation-schedule",
    response_model=list[ValidationScheduleResponse]
)
def validation_schedule(
    cycle_id: int,
    request: ValidationScheduleRequest,
    db: Session = Depends(get_db)
):
    return schedule_validation(
        db=db,
        cycle_id=cycle_id,
        assigned_to=request.assigned_to,
        planned_date=request.planned_date
    )