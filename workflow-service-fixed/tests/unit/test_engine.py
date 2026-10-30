import pytest
import uuid
from unittest.mock import AsyncMock, Mock
import asyncio
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


@pytest.mark.asyncio
async def test_event_idempotency_survives_redis_cache_miss():
    db = AsyncMock()
    redis = AsyncMock()
    kafka = AsyncMock()
    workflow_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    existing_execution = WorkflowExecution(
        execution_id=uuid.uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        trigger_type="event",
        trigger_data={"event_id": "stable-event-id"},
        status="completed",
        dedup_key="durable-key",
    )
    db.get.return_value = Workflow(
        workflow_id=workflow_id,
        status="active",
        definition={"steps": []},
    )
    redis.get.return_value = None
    db.scalar.return_value = existing_execution

    result = await WorkflowEngine(db, redis, kafka).execute(
        workflow_id,
        {"type": "event", "event_id": "stable-event-id"},
        tenant_id,
    )

    assert result is existing_execution
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_step_retry_succeeds_after_transient_error(monkeypatch):
    engine = WorkflowEngine(AsyncMock(), AsyncMock(), AsyncMock())
    engine.executor.execute = AsyncMock(
        side_effect=[RuntimeError("temporary"), {"status": "success"}]
    )
    engine.retry_mgr.calculate_backoff = Mock(return_value=0)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    result = await engine._execute_step_with_retry_rollback(
        {"id": "retry-step", "retry": {"count": 2}},
        Mock(context={}, execution_id=uuid.uuid4()),
        {},
    )

    assert result == {"status": "success"}
    assert engine.executor.execute.await_count == 2


@pytest.mark.asyncio
async def test_failed_step_runs_rollback_after_retries(monkeypatch):
    engine = WorkflowEngine(AsyncMock(), AsyncMock(), AsyncMock())
    engine.executor.execute = AsyncMock(side_effect=RuntimeError("permanent"))
    engine.retry_mgr.calculate_backoff = Mock(return_value=0)
    engine.rollback_mgr.rollback_step = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    execution = Mock(context={}, execution_id=uuid.uuid4())
    step = {"id": "failed-step", "retry": {"count": 2}, "rollback": [{"action": "undo"}]}

    completed_results = {"prior": {"status": "success"}}
    definitions = {"prior": {"rollback": [{"id": "undo-prior"}]}}
    with pytest.raises(RuntimeError, match="permanent"):
        await engine._execute_step_with_retry_rollback(
            step, execution, completed_results, definitions
        )

    assert engine.executor.execute.await_count == 2
    engine.rollback_mgr.rollback_step.assert_awaited_once_with(
        step, execution, completed_results, definitions
    )


@pytest.mark.asyncio
async def test_rollback_runs_configured_compensations_in_reverse_order():
    from src.services.rollback_manager import RollbackManager

    db = AsyncMock()
    query_result = Mock()
    query_result.scalars.return_value.first.return_value = None
    db.execute.return_value = query_result
    executor = Mock()
    executor.execute = AsyncMock(side_effect=[
        {"status": "success", "action": "undo-b"},
        {"status": "success", "action": "undo-a"},
        {"status": "success", "action": "undo-prior"},
    ])
    manager = RollbackManager(db, executor)
    execution = Mock(execution_id=uuid.uuid4(), context={"trigger": {"x": 1}})

    results = await manager.rollback_step(
        {"id": "work", "rollback": [
            {"id": "undo-a", "type": "action", "action": "http"},
            {"id": "undo-b", "type": "action", "action": "http"},
        ]}, execution, {"prior": {"status": "success"}},
        {"prior": {"name": "previous", "rollback": [
            {"id": "undo-prior", "type": "action", "action": "http"}
        ]}}
    )

    assert [item["action"] for item in results] == ["undo-b", "undo-a", "undo-prior"]
    assert [call.args[0]["id"] for call in executor.execute.await_args_list] == [
        "undo-b", "undo-a", "undo-prior"
    ]
