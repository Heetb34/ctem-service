from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.database import get_db
from src.services.execution_service import ExecutionService
from src.schemas import ExecutionTrigger, ExecutionResponse
from src.api.dependencies import get_execution_service

router = APIRouter(prefix="/executions", tags=["executions"])

@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(
    workflow_id: UUID,
    trigger: ExecutionTrigger,
    service: ExecutionService = Depends(get_execution_service)
):
    try:
        execution = await service.execute(workflow_id, trigger)
        return execution
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: UUID,
    service: ExecutionService = Depends(get_execution_service)
):
    exec_data = await service.get_execution(execution_id)
    if not exec_data:
        raise HTTPException(404, "Execution not found")
    return exec_data

@router.post("/{execution_id}/pause")
async def pause_execution(
    execution_id: UUID,
    service: ExecutionService = Depends(get_execution_service)
):
    await service.pause_execution(execution_id)
    return {"status": "paused"}

@router.post("/{execution_id}/resume")
async def resume_execution(
    execution_id: UUID,
    service: ExecutionService = Depends(get_execution_service)
):
    await service.resume_execution(execution_id)
    return {"status": "resumed"}
