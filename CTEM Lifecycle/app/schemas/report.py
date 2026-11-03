
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ReportRequest(BaseModel):
    report_name: str
    report_type: str
    generated_by: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    report_name: str
    report_type: str
    generated_by: str
    report_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
