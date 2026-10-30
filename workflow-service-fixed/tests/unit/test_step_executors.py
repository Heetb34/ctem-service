from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from src.services.step_executors import StepExecutor


@pytest.mark.asyncio
async def test_approval_step_returns_json_serializable_approval_id():
    approval_id = uuid.uuid4()
    executor = StepExecutor(AsyncMock(), AsyncMock(), AsyncMock())
    executor.approval_service.create_approval = AsyncMock(
        return_value=SimpleNamespace(approval_id=approval_id)
    )

    result = await executor.execute(
        {
            "id": "approval-gate",
            "type": "approval",
            "approvers": [str(uuid.uuid4())],
            "sla_hours": 1,
        },
        {},
        str(uuid.uuid4()),
    )

    assert result == {
        "status": "pending_approval",
        "approval_id": str(approval_id),
    }
