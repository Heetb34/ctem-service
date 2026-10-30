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

    async def rollback_step(self, step_def: dict, execution, previous_results: dict):
        rollback_actions = step_def.get("rollback") or []
        if not rollback_actions:
            return []

        context = dict(execution.context or {})
        context["step_results"] = dict(previous_results)
        rollback_results = []
        # Compensating operations should unwind in the opposite order from
        # their declaration/execution.
        for action in reversed(rollback_actions):
            result = await self.executor.execute(
                action, context, str(execution.execution_id)
            )
            if result.get("status") != "success":
                raise RuntimeError(
                    f"Rollback action {action.get('id', action.get('action', 'unknown'))} failed: "
                    f"{result.get('error', result)}"
                )
            rollback_results.append(result)

        step_name = step_def.get("name", step_def["id"])
        stmt = (
            select(WorkflowStep)
            .where(
                WorkflowStep.execution_id == execution.execution_id,
                WorkflowStep.step_name == step_name,
            )
            .order_by(WorkflowStep.created_at.desc())
        )
        result = await self.db.execute(stmt)
        step = result.scalars().first()
        if step:
            step.status = "rolled_back"
            step.output = {"rollback": "completed", "actions": rollback_results}
            await self.db.commit()
        return rollback_results
