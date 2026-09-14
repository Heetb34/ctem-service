from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.prioritization_service import prioritize_cycle
from app.schemas.prioritize import PrioritizeResponse

router = APIRouter(
    prefix="/ctem",
    tags=["CTEM Prioritization"]
)

@router.post(
    "/cycles/{cycle_id}/prioritize",
    response_model=list[PrioritizeResponse]
)
def run_prioritization(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return prioritize_cycle(db, cycle_id)