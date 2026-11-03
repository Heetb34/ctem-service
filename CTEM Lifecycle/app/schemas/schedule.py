from datetime import date, datetime
from pydantic import BaseModel


class ScheduleRequest(BaseModel):
    cycle_name: str
    frequency: str
    start_date: date
    status: str


class ScheduleResponse(BaseModel):
    id: int
    cycle_name: str
    frequency: str
    start_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True