from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.report import ReportRequest, ReportResponse
from app.services.report_service import create_report


router = APIRouter(
    prefix="/ctem",
    tags=["Reports"]
)


@router.post(
    "/cycles/{cycle_id}/report",
    response_model=ReportResponse
)
def generate_report(
    cycle_id: int,
    request: ReportRequest,
    db: Session = Depends(get_db)
):
    return create_report(
        db=db,
        cycle_id=cycle_id,
        report_name=request.report_name,
        report_type=request.report_type,
        generated_by=request.generated_by
    )