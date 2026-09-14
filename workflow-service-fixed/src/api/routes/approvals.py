from fastapi import APIRouter, Depends, HTTPException
from src.services.approval_service import ApprovalService
from src.services.execution_service import ExecutionService
from src.schemas import ApprovalDecision
from src.api.dependencies import get_approval_service, get_execution_service
from uuid import UUID

router = APIRouter(prefix="/approvals", tags=["approvals"])

@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    approval_service: ApprovalService = Depends(get_approval_service),
    execution_service: ExecutionService = Depends(get_execution_service),
):
    try:
        approval = await approval_service.decide(approval_id, decision.decision, decision.user_id, decision.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # An approval gates a specific workflow execution: approving it resumes
    # the paused DAG, rejecting it fails the execution outright.
    try:
        if approval.status == "approved":
            await execution_service.resume_after_approval(approval.execution_id)
        elif approval.status == "rejected":
            await execution_service.fail_after_rejection(
                approval.execution_id,
                f"Approval {approval.approval_id} was rejected"
                + (f": {decision.comment}" if decision.comment else ""),
            )
    except ValueError as e:
        # Decision itself succeeded; surface the follow-on failure distinctly.
        raise HTTPException(status_code=409, detail=f"Approval recorded, but execution could not be updated: {e}")

    return {"status": approval.status, "decision": approval.decision}
