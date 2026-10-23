from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (  # noqa: F401  (imported so create_all builds every table)
    exception, exposure, framework_mapping, remediation,
    report, report_job, report_schedule, saved_report,
    schedule, validation_plan,
)
from app.models.report import Report
from app.models.report_schedule import ReportSchedule
import app.services.report_scheduler_runner as runner
from app.services.report_email_service import PartialEmailDeliveryError


@pytest.fixture()
def env(monkeypatch, tmp_path):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    sent = []
    state = {"fail": False}

    def fake_send(recipients, report_name, file_path):
        if state["fail"]:
            raise RuntimeError("SMTP down")
        sent.append(recipients)

    monkeypatch.setattr(runner, "engine", test_engine)
    monkeypatch.setattr(runner, "send_report_email", fake_send)
    monkeypatch.setattr(
        runner, "_write_report_file",
        lambda report, fmt: tmp_path / f"report-{report.id}.{fmt}",
    )
    return test_engine, sent, state


def make_schedule(engine, frequency="daily", recipients=("a@example.com",)):
    with Session(engine) as db:
        start = runner._utcnow() - timedelta(minutes=1)
        item = ReportSchedule(
            cycle_id=1, report_name="Test", report_type="cycle-summary",
            frequency=frequency, start_at=start, recipients=list(recipients),
            report_format="csv", enabled=True, created_by="tester",
            next_run_at=start,
        )
        db.add(item)
        db.commit()
        return item.id


def make_due(engine, schedule_id):
    with Session(engine) as db:
        db.get(ReportSchedule, schedule_id).next_run_at = (
            runner._utcnow() - timedelta(seconds=1)
        )
        db.commit()


def test_success_sends_email_and_advances(env):
    engine, sent, state = env
    sid = make_schedule(engine)

    runner.run_due_report_schedules()

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert len(sent) == 1
        assert item.attempts == 0 and item.last_error is None
        assert item.last_run_at is not None
        assert item.next_run_at > runner._utcnow()
        assert db.query(Report).count() == 1


def test_email_failure_retries_without_duplicate_report(env):
    engine, sent, state = env
    state["fail"] = True
    sid = make_schedule(engine)

    runner.run_due_report_schedules()

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.attempts == 1
        assert "SMTP down" in item.last_error
        assert item.last_report_id is not None
        assert item.next_run_at > runner._utcnow()
        assert db.query(Report).count() == 1

    make_due(engine, sid)
    state["fail"] = False
    runner.run_due_report_schedules()

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert len(sent) == 1
        assert item.attempts == 0 and item.last_error is None
        assert db.query(Report).count() == 1  # reused, not regenerated


def test_partial_email_delivery_retries_only_refused_recipients(env, monkeypatch):
    engine, sent, state = env
    recipients = ["a@example.com", "b@example.com"]
    sid = make_schedule(engine, recipients=recipients)
    calls = []

    def send_with_partial_refusal(recipients, report_name, file_path):
        calls.append(list(recipients))
        if len(calls) == 1:
            raise PartialEmailDeliveryError(
                accepted_recipients=["a@example.com"],
                refused_recipients=["b@example.com"],
            )
        sent.append(recipients)

    monkeypatch.setattr(runner, "send_report_email", send_with_partial_refusal)

    runner.run_due_report_schedules()
    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.delivered_recipients == ["a@example.com"]
        assert item.attempts == 1

    make_due(engine, sid)
    runner.run_due_report_schedules()

    assert calls == [recipients, ["b@example.com"]]
    assert sent == [["b@example.com"]]
    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.delivered_recipients == []
        assert item.attempts == 0


def test_gives_up_after_max_attempts(env):
    engine, sent, state = env
    state["fail"] = True
    sid = make_schedule(engine, frequency="once")

    for attempt in range(runner.MAX_ATTEMPTS):
        runner.run_due_report_schedules()
        if attempt < runner.MAX_ATTEMPTS - 1:
            make_due(engine, sid)

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.enabled is False
        assert item.next_run_at is None
        assert "SMTP down" in item.last_error
        assert item.attempts == runner.MAX_ATTEMPTS


def test_recurring_schedule_starts_fresh_retry_count_after_giving_up(env):
    engine, sent, state = env
    state["fail"] = True
    sid = make_schedule(engine, frequency="daily")

    for attempt in range(runner.MAX_ATTEMPTS):
        runner.run_due_report_schedules()
        if attempt < runner.MAX_ATTEMPTS - 1:
            make_due(engine, sid)

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.attempts == runner.MAX_ATTEMPTS
        assert item.last_error

    make_due(engine, sid)
    runner.run_due_report_schedules()

    with Session(engine) as db:
        item = db.get(ReportSchedule, sid)
        assert item.attempts == 1
        assert "SMTP down" in item.last_error
        assert db.query(Report).count() == 2


def test_empty_dataset_still_generates_report(env):
    engine, sent, state = env
    make_schedule(engine, recipients=())

    runner.run_due_report_schedules()

    with Session(engine) as db:
        report = db.query(Report).one()
        assert report.report_data["summary"]["total_exposures"] == 0
    assert sent == []


def test_disabled_schedule_is_not_run(env):
    engine, sent, state = env
    sid = make_schedule(engine)
    with Session(engine) as db:
        db.get(ReportSchedule, sid).enabled = False
        db.commit()

    runner.run_due_report_schedules()

    assert sent == []
    with Session(engine) as db:
        assert db.query(Report).count() == 0


def test_claim_lease_prevents_duplicate_and_recovers_after_restart(env):
    engine, sent, state = env
    sid = make_schedule(engine)
    claimed_at = runner._utcnow()

    with Session(engine) as db:
        claimed = runner._claim_next_due(db, claimed_at)
        assert claimed.id == sid

    # A second API worker cannot claim while the persisted lease is active.
    with Session(engine) as db:
        assert runner._claim_next_due(db, runner._utcnow()) is None

    # Simulate a process restart after its lease expires; the due row is claimable again.
    make_due(engine, sid)
    with Session(engine) as db:
        reclaimed = runner._claim_next_due(db, runner._utcnow())
        assert reclaimed.id == sid
