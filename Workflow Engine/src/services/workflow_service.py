from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Workflow
from src.schemas import WorkflowCreate, WorkflowUpdate
from src.utils.dag_builder import build_dag
from uuid import UUID
from datetime import datetime

class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(self, data: WorkflowCreate) -> Workflow:
        # Validate DAG
        build_dag(data.definition)
        workflow = Workflow(
            tenant_id=data.tenant_id,
            workspace_id=data.workspace_id,
            name=data.name,
            description=data.description,
            definition=data.definition,
            triggers=data.triggers or [],
            created_by=data.created_by,
            version=1,
            status="active"
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def get_workflow(self, workflow_id: UUID) -> Workflow:
        stmt = select(Workflow).where(Workflow.workflow_id == workflow_id, Workflow.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_workflow(self, workflow_id: UUID, data: WorkflowUpdate) -> Workflow:
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return None
        # Create new version
        new_version = Workflow(
            tenant_id=workflow.tenant_id,
            workspace_id=workflow.workspace_id,
            name=data.name or workflow.name,
            description=data.description or workflow.description,
            definition=data.definition or workflow.definition,
            triggers=data.triggers or workflow.triggers,
            created_by=workflow.created_by,
            version=workflow.version + 1,
            status="active"
        )
        # Validate new definition
        if data.definition:
            build_dag(data.definition)
        # Optionally mark old as inactive
        workflow.status = "inactive"
        self.db.add(new_version)
        await self.db.commit()
        await self.db.refresh(new_version)
        return new_version

    async def delete_workflow(self, workflow_id: UUID) -> bool:
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return False
        workflow.deleted_at = datetime.utcnow()
        await self.db.commit()
        return True
