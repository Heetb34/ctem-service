from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    definition: Dict[str, Any]
    triggers: Optional[List[Dict]] = []
    workspace_id: Optional[UUID] = None
    tenant_id: UUID
    created_by: UUID

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[Dict] = None
    triggers: Optional[List[Dict]] = None

class WorkflowResponse(BaseModel):
    workflow_id: UUID
    name: str
    version: int
    status: str
    definition: Dict
    triggers: List
    created_at: datetime

class ExecutionTrigger(BaseModel):
    trigger_type: str  # event, schedule, manual, webhook
    input: Optional[Dict] = {}
    initiated_by: Optional[UUID] = None
    tenant_id: UUID

class ExecutionResponse(BaseModel):
    execution_id: UUID
    workflow_id: UUID
    status: str
    trigger_type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    context: Dict

class ApprovalDecision(BaseModel):
    decision: str  # approve or reject
    comment: Optional[str] = None
    user_id: UUID
