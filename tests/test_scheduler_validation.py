from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.report_schedule import (
    ReportScheduleRequest,
    ReportScheduleUpdate,
)


def _request(**overrides):
    data = {
        "cycle_id": 1,
        "report_name": "Weekly report",
        "report_type": "cycle-summary",
        "frequency": "weekly",
        "start_at": datetime(2026, 10, 23, 12, 0),
        "recipients": ["ciso@example.com"],
        "report_format": "pdf",
        "created_by": "tester",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("recipient", ["", "invalid", "a@b", "a b@example.com"])
def test_create_rejects_invalid_recipients(recipient):
    with pytest.raises(ValidationError):
        ReportScheduleRequest(**_request(recipients=[recipient]))


def test_create_trims_and_deduplicates_recipients():
    schedule = ReportScheduleRequest(
        **_request(recipients=[" ciso@example.com ", "ciso@example.com"])
    )
    assert schedule.recipients == ["ciso@example.com"]


def test_update_rejects_invalid_recipients():
    with pytest.raises(ValidationError):
        ReportScheduleUpdate(recipients=["not-an-email"])


def test_timezone_offset_is_normalized_to_utc():
    from app.services.report_schedule_service import create_report_schedule
    from app.database import Base
    from app.models.report_schedule import ReportSchedule  # noqa: F401
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    test_engine = create_engine("sqlite://")
    Base.metadata.create_all(test_engine)
    supplied = datetime(2026, 10, 23, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    request = ReportScheduleRequest(**_request(start_at=supplied))

    with Session(test_engine) as db:
        result = create_report_schedule(db, request)
        assert result.start_at == datetime(2026, 10, 23, 12, 0)
        assert result.next_run_at == datetime(2026, 10, 23, 12, 0)
