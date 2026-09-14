import asyncio
import networkx as nx
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from src.models import Workflow, WorkflowExecution, WorkflowStep
from src.services.step_executors import StepExecutor
from src.utils.idempotency import IdempotencyManager
from src.events.publisher import EventPublisher
from src.services.retry_manager import RetryManager
from src.services.rollback_manager import RollbackManager
from src.utils.dag_builder import build_dag
from src.config import get_settings
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer

settings = get_settings()

# Sentinel returned by _execute_dag to say "we stopped cleanly because a
# step is waiting on something external (an approval)", as opposed to
# finishing normally.
WAITING_APPROVAL = "waiting_approval"
DONE = "done"


class WorkflowEngine:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis, kafka_producer: AIOKafkaProducer):
        self.db = db
        self.idempotency = IdempotencyManager(redis_client)
        self.event_pub = EventPublisher(kafka_producer)
        self.retry_mgr = RetryManager()
        self.rollback_mgr = RollbackManager(db)
        self.executor = StepExecutor(db, redis_client, kafka_producer)

    async def execute(self, workflow_id: UUID, trigger_data: dict, tenant_id: UUID, initiated_by: UUID = None) -> WorkflowExecution:
        # Get workflow
        workflow = await self.db.get(Workflow, workflow_id)
        if not workflow or workflow.status != "active":
            raise ValueError("Workflow not found or inactive")

        # Idempotency
        dedup_key = self.idempotency.generate_key(workflow_id, trigger_data)
        existing = await self.idempotency.get_existing(dedup_key)
        if existing:
            # Return existing execution (we'll fetch from DB)
            exec_id = UUID(existing["execution_id"])
            return await self.db.get(WorkflowExecution, exec_id)

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            trigger_type=trigger_data.get("type", "manual"),
            trigger_data=trigger_data,
            status="pending",
            initiated_by=initiated_by,
            dedup_key=dedup_key,
            context={"step_results": {}},
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)

        # Publish event
        await self.event_pub.publish_workflow_started(execution)

        # Store idempotency result up front so concurrent duplicate triggers
        # land on this execution rather than racing to create their own.
        await self.idempotency.set_execution(dedup_key, {"execution_id": str(execution.execution_id), "status": execution.status})

        return await self._run_workflow(execution, workflow)

    async def resume(self, execution_id: UUID) -> WorkflowExecution:
        """Continue a workflow that stopped at an approval step, after the
        approval has been decided. Call this after an "approve" decision."""
        execution = await self.db.get(WorkflowExecution, execution_id)
        if not execution:
            raise ValueError("Execution not found")
        if execution.status != "waiting_approval":
            raise ValueError(f"Execution is not waiting on approval (status={execution.status})")
        workflow = await self.db.get(Workflow, execution.workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")

        execution.context.pop("waiting_step", None)
        flag_modified(execution, "context")
        await self.db.commit()

        return await self._run_workflow(execution, workflow)

    async def _run_workflow(self, execution: WorkflowExecution, workflow: Workflow) -> WorkflowExecution:
        dag = build_dag(workflow.definition)
        try:
            outcome = await self._execute_dag(dag, workflow.definition, execution)
            if outcome == WAITING_APPROVAL:
                execution.status = "waiting_approval"
            else:
                execution.status = "completed"
                execution.completed_at = datetime.utcnow()
                await self.event_pub.publish_workflow_completed(execution)
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            await self.event_pub.publish_workflow_failed(execution)
            raise
        finally:
            await self.db.commit()
            if execution.dedup_key:
                await self.idempotency.set_execution(
                    execution.dedup_key, {"execution_id": str(execution.execution_id), "status": execution.status}
                )
        return execution

    async def _execute_dag(self, dag: nx.DiGraph, definition: dict, execution: WorkflowExecution) -> str:
        steps_map = {s["id"]: s for s in definition["steps"]}

        # Resume support: steps already completed in a previous run (before
        # we hit an approval gate) are stored in execution.context so we
        # don't re-execute them.
        step_results = execution.context.setdefault("step_results", {})
        completed = set(step_results.keys())
        results = dict(step_results)

        pending = [n for n in dag.nodes if n not in completed]

        while pending:
            # The "paused" flag is set by a *separate* HTTP request/session
            # (POST /executions/{id}/pause), so re-read it from the DB each
            # loop iteration rather than trusting our in-memory copy, which
            # would never see the other request's change.
            await self.db.refresh(execution, attribute_names=["context"])
            if execution.context.get("paused"):
                await asyncio.sleep(2)
                continue

            ready = [
                node for node in pending
                if all(dep in completed for dep in dag.predecessors(node))
            ]
            if not ready:
                raise RuntimeError("Deadlock in DAG")

            tasks = [
                self._execute_step_with_retry_rollback(steps_map[node], execution, results)
                for node in ready
            ]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            hit_approval_gate = False
            for node, result in zip(ready, task_results):
                if isinstance(result, Exception):
                    raise result

                results[node] = result
                step_status = await self._save_step_result(execution, node, steps_map[node], result)

                if step_status == "pending_approval":
                    # Do NOT mark this node completed: its downstream
                    # dependents must stay blocked until a human decides.
                    execution.context["waiting_step"] = node
                    hit_approval_gate = True
                else:
                    completed.add(node)

            # Persist progress so a resume() after an approval can pick up
            # from here instead of re-running everything.
            execution.context["step_results"] = results
            flag_modified(execution, "context")
            await self.db.commit()

            if hit_approval_gate:
                return WAITING_APPROVAL

            pending = [n for n in dag.nodes if n not in completed]

        return DONE

    async def _execute_step_with_retry_rollback(self, step_def: dict, execution: WorkflowExecution, previous_results: dict):
        max_retries = step_def.get("retry", {}).get("count", settings.default_retry_count)
        backoff = step_def.get("retry", {}).get("backoff", settings.default_backoff)
        attempt = 0
        while attempt < max_retries:
            try:
                result = await self.executor.execute(step_def, execution.context, str(execution.execution_id))
                return result
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    if step_def.get("rollback"):
                        await self.rollback_mgr.rollback_step(step_def, execution, previous_results)
                    raise
                wait = self.retry_mgr.calculate_backoff(backoff, attempt)
                await asyncio.sleep(wait)

    async def _save_step_result(self, execution: WorkflowExecution, step_id: str, step_def: dict, result: dict) -> str:
        result_status = result.get("status")
        if result_status == "success":
            saved_status = "completed"
        elif result_status == "pending_approval":
            saved_status = "pending_approval"
        else:
            saved_status = "failed"

        step = WorkflowStep(
            execution_id=execution.execution_id,
            step_name=step_def.get("name", step_id),
            step_type=step_def.get("type", "unknown"),
            input=step_def.get("input"),
            output=result,
            status=saved_status,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_ms=0,
        )
        self.db.add(step)
        await self.db.commit()
        return saved_status
