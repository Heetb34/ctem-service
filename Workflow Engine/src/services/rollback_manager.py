from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WorkflowStep
from src.services.step_executors import StepExecutor


class RollbackManager:
    """Run explicitly configured compensating actions in reverse order.

    Rollbacks are application-level compensations, not database transactions:
    external HTTP calls and other side effects cannot be atomically reversed.
    """

    def __init__(self, db: AsyncSession, executor: StepExecutor):
        self.db = db
        self.executor = executor

    async def rollback_step(
        self, step_def: dict, execution, previous_results: dict,
        step_definitions: dict | None = None,
    ):
        rollback_plan = []
        # The failed step may have partially completed before raising, so run
        # its compensation first, then unwind successful predecessors.
        if step_def.get("rollback"):
            rollback_plan.append((step_def.get("name", step_def["id"]), step_def.get("rollback") or []))
        if step_definitions:
            for step_id in reversed(list(previous_results)):
                result = previous_results[step_id]
                completed_def = step_definitions.get(step_id, {})
                if (
                    isinstance(result, dict)
                    and result.get("status") == "success"
                    and completed_def.get("rollback")
                ):
                    rollback_plan.append((
                        completed_def.get("name", step_id),
                        completed_def.get("rollback") or [],
                    ))
        if not rollback_plan:
            return []

        context = dict(execution.context or {})
        context["step_results"] = dict(previous_results)
        rollback_results = []
        for step_name, rollback_actions in rollback_plan:
            step_results = []
            # Actions within each compensation list also unwind in reverse.
            for action in reversed(rollback_actions):
                result = await self.executor.execute(
                    action, context, str(execution.execution_id)
                )
                if result.get("status") != "success":
                    raise RuntimeError(
                        f"Rollback action {action.get('id', action.get('action', 'unknown'))} failed: "
                        f"{result.get('error', result)}"
                    )
                step_results.append(result)
                rollback_results.append({"step": step_name, **result})

            stmt = (
                select(WorkflowStep)
                .where(
                    WorkflowStep.execution_id == execution.execution_id,
                    WorkflowStep.step_name == step_name,
                )
                .order_by(WorkflowStep.created_at.desc())
            )
            query_result = await self.db.execute(stmt)
            step = query_result.scalars().first()
            if step:
                step.status = "rolled_back"
                step.output = {
                    **(step.output or {}),
                    "rollback": "completed",
                    "rollback_actions": step_results,
                }
        await self.db.commit()
        return rollback_results
