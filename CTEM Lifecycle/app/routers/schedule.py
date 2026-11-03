from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schedule import ScheduleRequest, ScheduleResponse
from app.services.schedule_service import (
    create_schedule,
    get_schedules
)

router = APIRouter(
    prefix="/ctem",
    tags=["Schedule"]
)


@router.post(
    "/schedule",
    response_model=ScheduleResponse
)
def schedule_cycle(
    request: ScheduleRequest,
    db: Session = Depends(get_db)
):
    return create_schedule(
        db=db,
        schedule=request
    )


@router.get(
    "/schedule",
    response_model=list[ScheduleResponse]
)
def list_schedules(
    db: Session = Depends(get_db)
):
    return get_schedules(db)