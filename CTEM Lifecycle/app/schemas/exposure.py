from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ExposureCreate(BaseModel):
    asset_name: str
    vulnerability: str
    severity: str
    risk_score: int
    tenant_id: UUID | None = None
    user_id: str | None = None


class ExposureResponse(BaseModel):
    id: int
    cycle_id: int
    asset_name: str
    vulnerability: str
    severity: str
    risk_score: int
    status: str
    priority: str | None = None
    priority_score: int | None = None
    asset_id: str | None = None
    beta_risk_rating: int | None = None
    business_criticality: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
