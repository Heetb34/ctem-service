import calendar
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import engine
from app.models.report import Report
from app.models.report_schedule import ReportSchedule
from app.services.report_email_service import send_report_email
from app.services.report_export_service import (
    build_csv_report,
    build_excel_report,
    build_pdf_report,
)
from app.services.report_service import create_report


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3              # tries per scheduled run before giving up
RETRY_BASE_SECONDS = 60       # backoff: 60s, then 120s
LEASE = timedelta(minutes=5)  # claim time, so other instances skip a schedule in progress
MAX_SCHEDULES_PER_TICK = 50


def _utcnow() -> datetime:
    """Naive UTC. Every stored schedule time is treated as UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])

    return value.replace(year=year, month=month, day=day)


def _occurrence(anchor: datetime, frequency: str, k: int) -> datetime:
    # Always computed from the original start, so month-end dates do not drift.
    if frequency == "daily":
        return anchor + timedelta(days=k)
    if frequency == "weekly":
        return anchor + timedelta(weeks=k)
    if frequency == "monthly":
        return _add_months(anchor, k)
    if frequency == "quarterly":
        return _add_months(anchor, 3 * k)
    raise ValueError(f"Unsupported schedule frequency: {frequency}")


def _next_occurrence(anchor: datetime, frequency: str, now: datetime):
    if frequency == "once":
        return None

    candidate = anchor
    k = 0

    while candidate <= now:
        k += 1
        candidate = _occurrence(anchor, frequency, k)

    return candidate


def _write_report_file(report, report_format: str) -> Path:
    exporters = {
        "pdf": build_pdf_report,
        "csv": build_csv_report,
        "xlsx": build_excel_report,
    }

    export_format = report_format.lower()
    exporter = exporters.get(export_format)

    if exporter is None:
        raise ValueError(f"Unsupported report format: {report_format}")

    content = exporter(report.report_data or {})

    output_dir = Path(__file__).resolve().parents[2] / "generated_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"report-{report.id}.{export_format}"
    output_path.write_bytes(content)

    return output_path


def _advance(schedule: ReportSchedule, now: datetime) -> None:
    if schedule.frequency == "once":
        schedule.enabled = False
        schedule.next_run_at = None
    else:
        schedule.next_run_at = _next_occurrence(
            schedule.start_at, schedule.frequency, now
        )


def _claim_next_due(db: Session, now: datetime):
    """Lock one due schedule and push its next_run_at forward (a lease).

    Another API instance then skips it, and a crash mid-run is retried
    automatically once the lease expires.
    """
    schedule = (
        db.query(ReportSchedule)
        .filter(
            ReportSchedule.enabled.is_(True),
            ReportSchedule.next_run_at.isnot(None),
            ReportSchedule.next_run_at <= now,
        )
        .order_by(ReportSchedule.next_run_at)
        .with_for_update(skip_locked=True)
        .first()
    )

    if schedule is None:
        return None

    schedule.next_run_at = now + LEASE
    db.commit()
    return schedule


def _record_failure(db: Session, schedule_id: int, exc: Exception, now: datetime):
    schedule = db.get(ReportSchedule, schedule_id)
    if schedule is None:
        return

    schedule.attempts = (schedule.attempts or 0) + 1
    schedule.last_error = f"{type(exc).__name__}: {exc}"[:1000]

    if schedule.attempts < MAX_ATTEMPTS:
        delay = RETRY_BASE_SECONDS * 2 ** (schedule.attempts - 1)
        schedule.next_run_at = now + timedelta(seconds=delay)
        logger.warning(
            "Schedule %s failed (attempt %s/%s), retrying in %ss: %s",
            schedule_id, schedule.attempts, MAX_ATTEMPTS, delay, exc,
        )
    else:
        logger.error(
            "Schedule %s gave up after %s attempts: %s",
            schedule_id, schedule.attempts, exc,
        )
        schedule.attempts = 0
        schedule.last_report_id = None
        _advance(schedule, now)

    db.commit()


def _record_success(db: Session, schedule_id: int, now: datetime):
    schedule = db.get(ReportSchedule, schedule_id)
    if schedule is None:
        return

    schedule.last_run_at = now
    schedule.attempts = 0
    schedule.last_error = None
    schedule.last_report_id = None
    _advance(schedule, now)
    db.commit()


def _process_schedule(db: Session, schedule: ReportSchedule, now: datetime):
    schedule_id = schedule.id

    try:
        report = None

        # A report from an earlier failed attempt is reused, not regenerated.
        if schedule.last_report_id:
            report = db.get(Report, schedule.last_report_id)

        if report is None:
            report = create_report(
                db=db,
                cycle_id=schedule.cycle_id,
                report_name=schedule.report_name,
                report_type=schedule.report_type,
                generated_by=schedule.created_by,
            )
            schedule.last_report_id = report.id
            db.commit()

        file_path = _write_report_file(report, schedule.report_format)

        recipients = schedule.recipients or []
        if recipients:
            send_report_email(
                recipients=recipients,
                report_name=schedule.report_name,
                file_path=file_path,
            )
            logger.info("Report %s emailed to %s", report.id, recipients)

    except Exception as exc:
        db.rollback()
        _record_failure(db, schedule_id, exc, now)
        return

    _record_success(db, schedule_id, now)
    logger.info("Schedule %s completed (report %s)", schedule_id, report.id)


def run_due_report_schedules():
    """Run every due schedule, one at a time, safely across instances."""
    now = _utcnow()

    for _ in range(MAX_SCHEDULES_PER_TICK):
        with Session(bind=engine) as db:
            schedule = _claim_next_due(db, now)

            if schedule is None:
                return

            try:
                _process_schedule(db, schedule, now)
            except Exception:
                db.rollback()
                logger.exception("Unexpected error in schedule runner")