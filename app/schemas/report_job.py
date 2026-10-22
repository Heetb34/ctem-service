from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportJobRequest(BaseModel):
    cycle_id: int
    report_name: str
    report_type: str
    report_format: Literal["pdf", "csv", "xlsx"] = "pdf"
    generated_by: str
    filters: dict[str, Any] = Field(default_factory=dict)


class ReportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    report_name: str
    report_type: str
    report_format: str
    generated_by: str
    filters: dict[str, Any] | None = None
    status: str
    report_id: int | None = None
    file_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None