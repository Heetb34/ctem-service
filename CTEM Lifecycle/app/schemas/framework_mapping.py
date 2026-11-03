from datetime import datetime
from pydantic import BaseModel


class FrameworkMappingRequest(BaseModel):
    cycle_id: int
    framework_name: str
    control_name: str
    status: str


class FrameworkMappingResponse(BaseModel):
    id: int
    cycle_id: int
    framework_name: str
    control_name: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True