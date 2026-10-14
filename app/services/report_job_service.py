
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import engine
from app.models.report_job import ReportJob
from app.services.report_export_service import (
    build_csv_report,
    build_excel_report,
    build_pdf_report,
)
from app.services.report_service import create_report


logger = logging.getLogger(__name__)


def create_report_job(db: Session, request):
    """Create and save a pending report job."""
    job = ReportJob(
        cycle_id=request.cycle_id,
        report_name=request.report_name,
        report_type=request.report_type,
        report_format=request.report_format,
        generated_by=request.generated_by,
        filters=request.filters or {},
        status="pending",
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        raise


def process_report_job(job_id: int):
    """Generate a report, export the file, and update job status."""
    with Session(bind=engine) as db:
        job = (
            db.query(ReportJob)
            .filter(ReportJob.id == job_id)
            .first()
        )

        if job is None:
            logger.error("Report job %s was not found", job_id)
            return

        try:
            job.status = "running"
            job.started_at = datetime.now()
            db.commit()

            report = create_report(
                db=db,
                cycle_id=job.cycle_id,
                report_name=job.report_name,
                report_type=job.report_type,
                generated_by=job.generated_by,
                filters=job.filters or {},
            )

            exporters = {
                "pdf": build_pdf_report,
                "csv": build_csv_report,
                "xlsx": build_excel_report,
            }

            export_format = job.report_format.lower()
            exporter = exporters.get(export_format)

            if exporter is None:
                raise ValueError(
                    f"Unsupported report format: {job.report_format}"
                )

            content = exporter(report.report_data or {})

            output_dir = (
                Path(__file__).resolve().parents[2]
                / "generated_reports"
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = (
                output_dir / f"report-{report.id}.{export_format}"
            )
            output_path.write_bytes(content)

            job.report_id = report.id
            job.file_path = str(output_path)
            job.status = "completed"
            job.error_message = None
            job.completed_at = datetime.now()

            db.commit()

            logger.info(
                "Report job %s completed; report ID %s",
                job.id,
                report.id,
            )
            logger.info("Report file saved to %s", output_path)

        except Exception as exc:
            db.rollback()

            job = (
                db.query(ReportJob)
                .filter(ReportJob.id == job_id)
                .first()
            )

            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)[:4000]
                job.completed_at = datetime.now()
                db.commit()

            logger.exception(
                "Report job %s failed",
                job_id,
            )


def get_report_job(db: Session, job_id: int):
    """Retrieve a report job by its ID."""
    return (
        db.query(ReportJob)
        .filter(ReportJob.id == job_id)
        .first()
    )
