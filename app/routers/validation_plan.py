from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.validation_plan import ValidationPlanResponse
from app.services.validation_plan_service import create_validation_plan

router = APIRouter(
    prefix="/ctem",
    tags=["Validation Planning"]
)


@router.post(
    "/cycles/{cycle_id}/validation-plan",
    response_model=list[ValidationPlanResponse]
)
def generate_validation_plan(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return create_validation_plan(db, cycle_id)