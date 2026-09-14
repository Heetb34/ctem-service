from pydantic import BaseModel
from datetime import date


class ValidationPlanResponse(BaseModel):
    id: int
    cycle_id: int
    exposure_id: int
    validation_type: str
    validation_status: str
    assigned_to: str | None
    planned_date: date | None
    remarks: str | None

    class Config:
        from_attributes = True