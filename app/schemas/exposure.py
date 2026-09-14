from pydantic import BaseModel


class ExposureCreate(BaseModel):
    asset_name: str
    vulnerability: str
    severity: str
    risk_score: int


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