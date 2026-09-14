from datetime import datetime
from pydantic import BaseModel


class ReportRequest(BaseModel):
    report_name: str
    report_type: str
    generated_by: str


class ReportResponse(BaseModel):
    id: int
    cycle_id: int
    report_name: str
    report_type: str
    generated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True