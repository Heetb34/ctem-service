
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report
from app.schemas.report import ReportRequest, ReportResponse
from app.schemas.report_job import ReportJobRequest, ReportJobResponse
from app.services.report_export_service import (
    build_csv_report,
    build_excel_report,
    build_pdf_report,
)
from app.services.report_job_service import (
    create_report_job,
    get_report_job,
    process_report_job,
)
from datetime import date
from app.services.report_comparison_service import compare_exposure_periods
from app.services.report_service import create_report
from app.services.report_template_service import (
    get_report_templates,
    get_report_template,
)


router = APIRouter(
    prefix="/ctem",
    tags=["Reports"],
)


@router.post(
    "/cycles/{cycle_id}/report",
    response_model=ReportResponse,
    status_code=201,
)
def generate_report(
    cycle_id: int,
    request: ReportRequest,
    db: Session = Depends(get_db),
):
    try:
        return create_report(
            db=db,
            cycle_id=cycle_id,
            report_name=request.report_name,
            report_type=request.report_type,
            generated_by=request.generated_by,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}",
        ) from exc


# Report templates
@router.get("/reports/templates")
def list_report_templates():
    return get_report_templates()


@router.get("/reports/templates/{template_id}")
def read_report_template(template_id: str):
    template = get_report_template(template_id)

    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Report template not found",
        )

    return template


# Asynchronous report generation
@router.post(
    "/reports",
    response_model=ReportJobResponse,
    status_code=202,
)
def generate_report_async(
    request: ReportJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = create_report_job(db, request)
    background_tasks.add_task(process_report_job, job.id)
    return job


@router.get(
    "/reports/jobs/{job_id}",
    response_model=ReportJobResponse,
)
def read_report_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = get_report_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Report job not found",
        )

    return job


@router.get("/reports/jobs/{job_id}/download")
def download_report_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = get_report_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Report job not found",
        )

    if job.status != "completed" or not job.file_path:
        raise HTTPException(
            status_code=409,
            detail="Report job is not completed",
        )

    output_dir = (
        Path(__file__).resolve().parents[2]
        / "generated_reports"
    ).resolve()

    file_path = Path(job.file_path).resolve()

    if not file_path.is_relative_to(output_dir):
        raise HTTPException(
            status_code=400,
            detail="Invalid generated report path",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Generated report file not found",
        )

    media_types = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "xlsx": (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    }

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_types.get(
            job.report_format,
            "application/octet-stream",
        ),
    )


# List reports
@router.get(
    "/reports",
    response_model=list[ReportResponse],
)
def list_reports(
    cycle_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Report)

    if cycle_id is not None:
        query = query.filter(Report.cycle_id == cycle_id)

    return query.order_by(Report.created_at.desc()).all()


# IMPORTANT: History must be registered before /reports/{report_id}.
@router.get(
    "/reports/history",
    response_model=list[ReportResponse],
)
def get_report_history(
    cycle_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    query = db.query(Report)

    if cycle_id is not None:
        query = query.filter(Report.cycle_id == cycle_id)

    return (
        query.order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )
@router.get("/reports/compare")
def compare_reports(
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
    cycle_id: int | None = None,
    db: Session = Depends(get_db),
):
    if period_a_end < period_a_start:
        raise HTTPException(
            status_code=400,
            detail="Period A end date must not precede its start date",
        )

    if period_b_end < period_b_start:
        raise HTTPException(
            status_code=400,
            detail="Period B end date must not precede its start date",
        )

    return compare_exposure_periods(
        db=db,
        cycle_id=cycle_id,
        period_a_start=period_a_start,
        period_a_end=period_a_end,
        period_b_start=period_b_start,
        period_b_end=period_b_end,
    )

# Export reports
@router.get("/reports/{report_id}/export")
def export_report(
    report_id: int,
    format: str = "csv",
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    report_data = report.report_data or {}
    export_format = format.lower()

    if export_format == "csv":
        content = build_csv_report(report_data)
        media_type = "text/csv"
        filename = f"report-{report_id}.csv"

    elif export_format in ("xlsx", "excel"):
        content = build_excel_report(report_data)
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
        filename = f"report-{report_id}.xlsx"

    elif export_format == "pdf":
        content = build_pdf_report(report_data)
        media_type = "application/pdf"
        filename = f"report-{report_id}.pdf"

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use pdf, csv, or xlsx.",
        )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# Retrieve one report
@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


# Delete one report
@router.delete(
    "/reports/{report_id}",
    status_code=204,
)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id)
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    db.delete(report)
    db.commit()

    return Response(status_code=204)
