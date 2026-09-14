from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.exposure import ExposureCreate, ExposureResponse
from app.services.exposure_service import create_exposure

router = APIRouter(
    prefix="/ctem",
    tags=["CTEM"]
)

@router.post(
    "/cycles/{cycle_id}/exposures",
    response_model=ExposureResponse
)
def add_exposure(
    cycle_id: int,
    exposure: ExposureCreate,
    db: Session = Depends(get_db)
):
    return create_exposure(db, cycle_id, exposure)