from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.remediation import (
    RemediationRequest,
    RemediationResponse
)
from app.services.remediation_service import create_remediation

router = APIRouter(
    prefix="/ctem",
    tags=["Remediation Tracking"]
)


@router.post(
    "/cycles/{cycle_id}/remediation",
    response_model=list[RemediationResponse]
)
def remediation_tracking(
    cycle_id: int,
    request: RemediationRequest,
    db: Session = Depends(get_db)
):
    return create_remediation(
        db=db,
        cycle_id=cycle_id,
        assigned_to=request.assigned_to,
        remediation_status=request.remediation_status,
        completion_date=request.completion_date,
        remediation_notes=request.remediation_notes
    )