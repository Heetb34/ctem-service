
import calendar
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import engine
from app.models.report_schedule import ReportSchedule
from app.services.report_email_service import send_report_email
from app.services.report_export_service import (
    build_csv_report,
    build_excel_report,
    build_pdf_report,
)
from app.services.report_service import create_report


logger = logging.getLogger(__name__)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])

    return value.replace(year=year, month=month, day=day)


def _next_occurrence(
    scheduled_time: datetime,
    frequency: str,
    now: datetime,
):
    if frequency == "once":
        return None

    next_time = scheduled_time

    while next_time <= now:
        if frequency == "daily":
            next_time += timedelta(days=1)
        elif frequency == "weekly":
            next_time += timedelta(weeks=1)
        elif frequency == "monthly":
            next_time = _add_months(next_time, 1)
        elif frequency == "quarterly":
            next_time = _add_months(next_time, 3)
        else:
            raise ValueError(
                f"Unsupported schedule frequency: {frequency}"
            )

    return next_time


def _write_report_file(report, report_format: str) -> Path:
    exporters = {
        "pdf": build_pdf_report,
        "csv": build_csv_report,
        "xlsx": build_excel_report,
    }

    export_format = report_format.lower()
    exporter = exporters.get(export_format)

    if exporter is None:
        raise ValueError(
            f"Unsupported report format: {report_format}"
        )

    content = exporter(report.report_data or {})

    output_dir = (
        Path(__file__).resolve().parents[2] / "generated_reports"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"report-{report.id}.{export_format}"
    output_path.write_bytes(content)

    return output_path


def run_due_report_schedules():
    """Generate scheduled reports and email them to configured recipients."""
    now = datetime.now()

    with Session(bind=engine) as db:
        due_schedules = (
            db.query(ReportSchedule)
            .filter(
                ReportSchedule.enabled.is_(True),
                ReportSchedule.next_run_at.isnot(None),
                ReportSchedule.next_run_at <= now,
            )
            .all()
        )

        for schedule in due_schedules:
            scheduled_time = schedule.next_run_at

            try:
                report = create_report(
                    db=db,
                    cycle_id=schedule.cycle_id,
                    report_name=schedule.report_name,
                    report_type=schedule.report_type,
                    generated_by=schedule.created_by,
                )

                file_path = _write_report_file(
                    report,
                    schedule.report_format,
                )

                # Email delivery is attempted only when recipients exist.
                recipients = schedule.recipients or []

                if recipients:
                    try:
                        send_report_email(
                            recipients=recipients,
                            report_name=schedule.report_name,
                            file_path=file_path,
                        )
                        logger.info(
                            "Report %s emailed to %s",
                            report.id,
                            recipients,
                        )
                    except Exception:
                        # Keep the generated report and avoid repeatedly
                        # generating duplicates because email configuration
                        # or the email server is unavailable.
                        logger.exception(
                            "Report %s was generated, but email delivery "
                            "failed for schedule %s",
                            report.id,
                            schedule.id,
                        )

                schedule.last_run_at = now

                if schedule.frequency == "once":
                    schedule.enabled = False
                    schedule.next_run_at = None
                else:
                    schedule.next_run_at = _next_occurrence(
                        scheduled_time,
                        schedule.frequency,
                        now,
                    )

                db.commit()

                logger.info(
                    "Schedule %s generated report %s at %s",
                    schedule.id,
                    report.id,
                    file_path,
                )

            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to execute report schedule %s",
                    schedule.id,
                )
