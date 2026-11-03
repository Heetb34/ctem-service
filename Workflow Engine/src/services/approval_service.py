from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Approval
import uuid

class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_approval(self, execution_id, step_id, approvers, sla_hours):
        approval = Approval(
            execution_id=execution_id,
            step_id=step_id,
            approvers=approvers,
            sla_hours=sla_hours,
            status="pending"
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def decide(self, approval_id, decision, user_id, comment=None):
        approval = await self.db.get(Approval, approval_id)
        if not approval:
            raise ValueError("Approval not found")
        if approval.status != "pending":
            raise ValueError("Approval already decided")
        if str(user_id) not in [str(a) for a in approval.approvers]:
            raise ValueError("User not authorized")
        approval.status = "approved" if decision == "approve" else "rejected"
        approval.decision = decision
        approval.decision_by = user_id
        approval.comment = comment
        await self.db.commit()
        return approval
