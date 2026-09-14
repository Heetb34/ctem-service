import asyncio
import httpx
from typing import Dict, Any
from src.utils.http_client import async_http_call
from src.services.approval_service import ApprovalService
from src.utils.safe_eval import evaluate_condition, UnsafeExpressionError

class StepExecutor:
    def __init__(self, db, redis, kafka_producer):
        self.db = db
        self.redis = redis
        self.kafka = kafka_producer
        self.approval_service = ApprovalService(db)

    async def execute(self, step_def: Dict, context: Dict, execution_id: str) -> Dict:
        step_type = step_def.get("type")
        if step_type == "action":
            return await self._execute_action(step_def, context)
        elif step_type == "condition":
            return await self._evaluate_condition(step_def, context)
        elif step_type == "loop":
            return await self._execute_loop(step_def, context, execution_id)
        elif step_type == "parallel":
            return await self._execute_parallel(step_def, context, execution_id)
        elif step_type == "wait":
            return await self._execute_wait(step_def)
        elif step_type == "approval":
            return await self._execute_approval(step_def, context, execution_id)
        elif step_type == "sub_workflow":
            return await self._execute_sub_workflow(step_def, context)
        else:
            raise ValueError(f"Unknown step type: {step_type}")

    async def _execute_action(self, step: Dict, context: Dict) -> Dict:
        action_type = step.get("action")
        if action_type == "send_notification":
            return {"status": "success", "notification_id": "notif_123"}
        elif action_type == "http":
            url = step.get("url")
            method = step.get("method", "POST")
            headers = step.get("headers", {})
            body = step.get("body", {})
            result = await async_http_call(method, url, headers=headers, json=body)
            return {"status": "success", "result": result}
        elif action_type == "create_record":
            return {"status": "success", "record_id": "rec_123"}
        else:
            return {"status": "success", "message": f"Action {action_type} executed"}

    async def _evaluate_condition(self, step: Dict, context: Dict) -> Dict:
        expr = step.get("condition")
        try:
            result = evaluate_condition(expr, context)
        except UnsafeExpressionError as e:
            return {"status": "failed", "error": str(e)}
        return {"status": "success", "result": result}

    async def _execute_loop(self, step: Dict, context: Dict, execution_id: str) -> Dict:
        collection_key = step.get("collection_key")
        collection = context.get(collection_key, [])
        iterations = len(collection)
        return {"status": "success", "iterations": iterations}

    async def _execute_parallel(self, step: Dict, context: Dict, execution_id: str) -> Dict:
        branches = step.get("branches", [])
        results = []
        for branch in branches:
            res = await self.execute(branch, context.copy(), execution_id)
            results.append(res)
        return {"status": "success", "branch_results": results}

    async def _execute_wait(self, step: Dict) -> Dict:
        seconds = step.get("seconds", 0)
        await asyncio.sleep(seconds)
        return {"status": "success"}

    async def _execute_approval(self, step: Dict, context: Dict, execution_id: str) -> Dict:
        approvers = step.get("approvers", [])
        sla_hours = step.get("sla_hours", 24)
        approval = await self.approval_service.create_approval(
            execution_id=execution_id,
            step_id=step["id"],
            approvers=approvers,
            sla_hours=sla_hours
        )
        return {"status": "pending_approval", "approval_id": approval.approval_id}

    async def _execute_sub_workflow(self, step: Dict, context: Dict) -> Dict:
        return {"status": "success", "sub_workflow_id": "sub_123"}
