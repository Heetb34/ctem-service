from sqlalchemy import Column, String, Integer, JSON, DateTime, UUID, Text, ForeignKey
from sqlalchemy.sql import func
from src.database import Base
import uuid

class Workflow(Base):
    __tablename__ = "workflows"
    workflow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(20), default="active")
    triggers = Column(JSON, default=list)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.workflow_id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    trigger_type = Column(String(50), nullable=False)
    trigger_data = Column(JSON)
    status = Column(String(30), default="pending")
    context = Column(JSON, default={})
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    initiated_by = Column(UUID(as_uuid=True), nullable=True)
    dedup_key = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    step_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.execution_id"), nullable=False)
    step_name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)
    input = Column(JSON)
    output = Column(JSON)
    status = Column(String(30), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Approval(Base):
    __tablename__ = "approvals"
    approval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.execution_id"), nullable=False)
    # This is the workflow *definition* step id (e.g. "approval-1"), not a
    # database row's UUID primary key, so it must be a string column.
    step_id = Column(String(255), nullable=False)
    approvers = Column(JSON, nullable=False)
    status = Column(String(20), default="pending")
    decision = Column(String(20), nullable=True)
    decision_by = Column(UUID(as_uuid=True), nullable=True)
    comment = Column(Text)
    sla_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
