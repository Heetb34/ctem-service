from pydantic import BaseModel
from datetime import date


class RemediationRequest(BaseModel):
    assigned_to: str
    remediation_status: str
    completion_date: date | None = None
    remediation_notes: str | None = None


class RemediationResponse(BaseModel):
    id: int
    cycle_id: int
    exposure_id: int
    remediation_status: str
    assigned_to: str | None
    completion_date: date | None
    remediation_notes: str | None

    class Config:
        from_attributes = True