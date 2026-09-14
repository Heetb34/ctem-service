from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.exception import ExceptionResponse
from app.services.exception_service import get_exceptions

router = APIRouter(
    prefix="/ctem",
    tags=["Exception Management"]
)


@router.get(
    "/cycles/{cycle_id}/exceptions",
    response_model=list[ExceptionResponse]
)
def exception_management(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return get_exceptions(db, cycle_id)