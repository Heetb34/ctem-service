from aiokafka import AIOKafkaProducer
import json
from src.models import WorkflowExecution, Approval
from datetime import datetime

class EventPublisher:
    def __init__(self, producer: AIOKafkaProducer):
        self.producer = producer

    async def publish_workflow_started(self, execution: WorkflowExecution):
        event = {
            "event_type": "WorkflowStarted",
            "execution_id": str(execution.execution_id),
            "workflow_id": str(execution.workflow_id),
            "trigger_type": execution.trigger_type,
            "timestamp": execution.created_at.isoformat(),
            "initiated_by": str(execution.initiated_by) if execution.initiated_by else None
        }
        await self.producer.send("workflow-events", value=event)

    async def publish_workflow_completed(self, execution: WorkflowExecution):
        event = {
            "event_type": "WorkflowCompleted",
            "execution_id": str(execution.execution_id),
            "workflow_id": str(execution.workflow_id),
            "status": execution.status,
            "completed_at": execution.completed_at.isoformat()
        }
        await self.producer.send("workflow-events", value=event)

    async def publish_workflow_failed(self, execution: WorkflowExecution):
        event = {
            "event_type": "WorkflowFailed",
            "execution_id": str(execution.execution_id),
            "workflow_id": str(execution.workflow_id),
            "error": execution.error_message,
            "failed_at": datetime.utcnow().isoformat()
        }
        await self.producer.send("workflow-events", value=event)

    async def publish_approval_requested(self, approval: Approval):
        event = {
            "event_type": "ApprovalRequested",
            "approval_id": str(approval.approval_id),
            "execution_id": str(approval.execution_id),
            "approvers": approval.approvers,
            "sla_hours": approval.sla_hours,
            "timestamp": approval.created_at.isoformat()
        }
        await self.producer.send("workflow-events", value=event)
