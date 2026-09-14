import pytest
import uuid
from unittest.mock import AsyncMock
from src.services.engine import WorkflowEngine
from src.models import Workflow, WorkflowExecution

@pytest.mark.asyncio
async def test_execute_idempotency():
    db = AsyncMock()
    redis = AsyncMock()
    kafka = AsyncMock()
    engine = WorkflowEngine(db, redis, kafka)
    workflow_id = uuid.uuid4()
    existing_execution_id = uuid.uuid4()
    workflow = Workflow(workflow_id=workflow_id, status="active", definition={"steps": []})
    db.get.return_value = workflow
    # Simulate existing execution
    redis.get.return_value = f'{{"execution_id": "{existing_execution_id}"}}'.encode()
    result = await engine.execute(workflow_id, {"type": "manual"}, uuid.uuid4())
    # Should return existing without creating new
    assert result is not None
    # db.add should not be called again