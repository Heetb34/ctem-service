from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report_schedule import (
    ReportScheduleRequest,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)
from app.services.report_schedule_service import (
    create_report_schedule,
    get_report_schedules,
    get_report_schedule,
    update_report_schedule,
    delete_report_schedule,
)

router = APIRouter(prefix="/ctem", tags=["Report Scheduler"])


@router.post(
    "/reports/schedules",
    response_model=ReportScheduleResponse,
    status_code=201,
)
def create_schedule(
    request: ReportScheduleRequest,
    db: Session = Depends(get_db),
):
    return create_report_schedule(db, request)


@router.get(
    "/reports/schedules",
    response_model=list[ReportScheduleResponse],
)
def list_schedules(db: Session = Depends(get_db)):
    return get_report_schedules(db)


@router.get(
    "/reports/schedules/{schedule_id}",
    response_model=ReportScheduleResponse,
)
def read_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    return get_report_schedule(db, schedule_id)


@router.patch(
    "/reports/schedules/{schedule_id}",
    response_model=ReportScheduleResponse,
)
def edit_schedule(
    schedule_id: int,
    request: ReportScheduleUpdate,
    db: Session = Depends(get_db),
):
    updates = request.model_dump(exclude_unset=True)
    return update_report_schedule(db, schedule_id, updates)


@router.delete("/reports/schedules/{schedule_id}", status_code=204)
def remove_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    delete_report_schedule(db, schedule_id)
    return Response(status_code=204)