from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import WorkflowStep

class RollbackManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def rollback_step(self, step_def: dict, execution, previous_results: dict):
        rollback_actions = step_def.get("rollback")
        if not rollback_actions:
            return
        # step_def["id"] is the *definition* id (e.g. "step1"), not the DB
        # primary key (a generated UUID), so db.get() would never find a row.
        # Look the row up by execution_id + step_name instead.
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
            step.output = {"rollback": "performed"}
            await self.db.commit()
