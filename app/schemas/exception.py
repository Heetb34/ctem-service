from pydantic import BaseModel
from datetime import date


class ExceptionResponse(BaseModel):
    id: int
    cycle_id: int
    exposure_id: int
    exception_reason: str
    approved_by: str | None
    exception_status: str
    expiry_date: date | None

    class Config:
        from_attributes = True