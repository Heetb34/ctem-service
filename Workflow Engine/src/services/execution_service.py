from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from src.models import WorkflowExecution
from src.services.engine import WorkflowEngine
from src.schemas import ExecutionTrigger
from uuid import UUID
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
from src.config import get_settings

settings = get_settings()

class ExecutionService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis, kafka_producer: AIOKafkaProducer):
        self.db = db
        self.redis = redis_client
        self.kafka = kafka_producer
        self.engine = WorkflowEngine(db, redis_client, kafka_producer)

    async def execute(self, workflow_id: UUID, trigger: ExecutionTrigger) -> WorkflowExecution:
        execution = await self.engine.execute(
            workflow_id=workflow_id,
            trigger_data=trigger.input,
            tenant_id=trigger.tenant_id,
            initiated_by=trigger.initiated_by
        )
        return execution

    async def get_execution(self, execution_id: UUID) -> WorkflowExecution:
        return await self.db.get(WorkflowExecution, execution_id)

    async def pause_execution(self, execution_id: UUID):
        exec_obj = await self.db.get(WorkflowExecution, execution_id)
        if not exec_obj:
            raise ValueError("Execution not found")
        exec_obj.context["paused"] = True
        flag_modified(exec_obj, "context")
        await self.db.commit()

    async def resume_execution(self, execution_id: UUID):
        exec_obj = await self.db.get(WorkflowExecution, execution_id)
        if not exec_obj:
            raise ValueError("Execution not found")
        exec_obj.context["paused"] = False
        flag_modified(exec_obj, "context")
        await self.db.commit()

    async def resume_after_approval(self, execution_id: UUID) -> WorkflowExecution:
        """Continue a workflow that was waiting on an approval step."""
        return await self.engine.resume(execution_id)

    async def fail_after_rejection(self, execution_id: UUID, reason: str) -> WorkflowExecution:
        """Mark a workflow as failed because a gating approval was rejected."""
        exec_obj = await self.db.get(WorkflowExecution, execution_id)
        if not exec_obj:
            raise ValueError("Execution not found")
        exec_obj.status = "failed"
        exec_obj.error_message = reason
        await self.db.commit()
        return exec_obj
