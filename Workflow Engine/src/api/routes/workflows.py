from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.database import get_db
from src.services.workflow_service import WorkflowService
from src.schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse
from src.api.dependencies import get_workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service)
):
    workflow = await service.create_workflow(data)
    return workflow

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service)
):
    workflow = await service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    service: WorkflowService = Depends(get_workflow_service)
):
    workflow = await service.update_workflow(workflow_id, data)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    service: WorkflowService = Depends(get_workflow_service)
):
    deleted = await service.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
