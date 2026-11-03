from pydantic import BaseModel


class TrendResponse(BaseModel):
    cycle_id: int
    total_exposures: int
    critical: int
    high: int
    medium: int
    low: int
    average_risk_score: float