from pydantic import BaseModel


class PrioritizeResponse(BaseModel):
    id: int
    asset_name: str
    severity: str
    risk_score: int
    priority: str
    priority_score: int

    class Config:
        from_attributes = True