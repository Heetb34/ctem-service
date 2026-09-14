from pydantic import BaseModel
from datetime import date


class ValidationScheduleRequest(BaseModel):
    assigned_to: str
    planned_date: date


class ValidationScheduleResponse(BaseModel):
    id: int
    cycle_id: int
    exposure_id: int
    validation_type: str
    validation_status: str
    assigned_to: str
    planned_date: date | None

    class Config:
        from_attributes = True