from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.trend import TrendResponse
from app.services.trend_service import get_trend_analysis

router = APIRouter(
    prefix="/ctem",
    tags=["Trend Analysis"]
)


@router.get(
    "/cycles/{cycle_id}/trends",
    response_model=TrendResponse
)
def trend_analysis(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return get_trend_analysis(
        db=db,
        cycle_id=cycle_id
    )