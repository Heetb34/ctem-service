from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SavedReportRequest(BaseModel):
    name: str
    description: str | None = None
    template_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_by: str


class SavedReportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    template_id: str | None = None
    parameters: dict[str, Any] | None = None


class SavedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    template_id: str | None = None
    parameters: dict[str, Any] | None = None
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None