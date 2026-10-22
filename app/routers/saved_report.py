
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.saved_report import (
    SavedReportRequest,
    SavedReportUpdate,
    SavedReportResponse,
)
from app.schemas.report_job import (
    ReportJobRequest,
    ReportJobResponse,
)
from app.services.saved_report_service import (
    create_saved_report,
    list_saved_reports,
    get_saved_report,
    update_saved_report,
    delete_saved_report,
)
from app.services.report_job_service import (
    create_report_job,
    process_report_job,
)
from app.services.report_template_service import get_report_template


router = APIRouter(
    prefix="/ctem",
    tags=["Saved Reports"],
)


@router.post(
    "/reports/saved",
    response_model=SavedReportResponse,
    status_code=201,
)
def create_saved_report_endpoint(
    request: SavedReportRequest,
    db: Session = Depends(get_db),
):
    return create_saved_report(db, request)


@router.get(
    "/reports/saved",
    response_model=list[SavedReportResponse],
)
def list_saved_reports_endpoint(
    db: Session = Depends(get_db),
):
    return list_saved_reports(db)


@router.get(
    "/reports/saved/{saved_report_id}",
    response_model=SavedReportResponse,
)
def get_saved_report_endpoint(
    saved_report_id: int,
    db: Session = Depends(get_db),
):
    return get_saved_report(db, saved_report_id)


@router.patch(
    "/reports/saved/{saved_report_id}",
    response_model=SavedReportResponse,
)
def update_saved_report_endpoint(
    saved_report_id: int,
    request: SavedReportUpdate,
    db: Session = Depends(get_db),
):
    updates = request.model_dump(exclude_unset=True)
    return update_saved_report(db, saved_report_id, updates)


@router.delete(
    "/reports/saved/{saved_report_id}",
    status_code=204,
)
def delete_saved_report_endpoint(
    saved_report_id: int,
    db: Session = Depends(get_db),
):
    delete_saved_report(db, saved_report_id)
    return Response(status_code=204)


@router.post(
    "/reports/saved/{saved_report_id}/run",
    response_model=ReportJobResponse,
    status_code=202,
)
def run_saved_report(
    saved_report_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    saved = get_saved_report(db, saved_report_id)
    parameters = saved.parameters or {}

    cycle_id = parameters.get("cycle_id")

    if cycle_id is None:
        raise HTTPException(
            status_code=400,
            detail="The saved report must include cycle_id in its parameters",
        )

    try:
        cycle_id = int(cycle_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="cycle_id must be an integer",
        ) from exc

    template = None

    if saved.template_id:
        template = get_report_template(saved.template_id)

        if template is None:
            raise HTTPException(
                status_code=400,
                detail="The saved report references an unknown template",
            )

    report_format = parameters.get(
        "report_format",
        parameters.get("format", "pdf"),
    )

    if report_format not in {"pdf", "csv", "xlsx"}:
        raise HTTPException(
            status_code=400,
            detail="report_format must be pdf, csv, or xlsx",
        )

    raw_filters = parameters.get("filters") or {}

    if not isinstance(raw_filters, dict):
        raise HTTPException(
            status_code=400,
            detail="Saved report filters must be an object",
        )

    filters = dict(raw_filters)

    for key in ("severity", "status", "start_date", "end_date"):
        if key in parameters:
            filters[key] = parameters[key]

    request = ReportJobRequest(
        cycle_id=cycle_id,
        report_name=saved.name,
        report_type=(
            template["category"].lower()
            if template
            else "custom"
        ),
        report_format=report_format,
        generated_by=saved.created_by,
        filters=filters,
    )

    job = create_report_job(db, request)
    background_tasks.add_task(process_report_job, job.id)

    return job
