from pydantic import BaseModel
from uuid import UUID


class ExposureCreate(BaseModel):
    asset_name: str
    vulnerability: str
    severity: str
    risk_score: int
    # CTEM can emit tenant-scoped workflow events when the caller supplies
    # these integration fields. They are intentionally not stored on the
    # legacy exposure table.
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

    class Config:
        from_attributes = True
