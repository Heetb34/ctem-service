from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.saved_report import SavedReport


def create_saved_report(db: Session, request):
    saved_report = SavedReport(
        name=request.name,
        description=request.description,
        template_id=request.template_id,
        parameters=request.parameters,
        created_by=request.created_by,
    )

    try:
        db.add(saved_report)
        db.commit()
        db.refresh(saved_report)
        return saved_report
    except Exception:
        db.rollback()
        raise


def list_saved_reports(db: Session):
    return (
        db.query(SavedReport)
        .order_by(SavedReport.created_at.desc())
        .all()
    )


def get_saved_report(db: Session, saved_report_id: int):
    saved_report = (
        db.query(SavedReport)
        .filter(SavedReport.id == saved_report_id)
        .first()
    )

    if saved_report is None:
        raise HTTPException(
            status_code=404,
            detail="Saved report not found",
        )

    return saved_report


def update_saved_report(
    db: Session,
    saved_report_id: int,
    updates: dict,
):
    saved_report = get_saved_report(db, saved_report_id)

    for field, value in updates.items():
        setattr(saved_report, field, value)

    try:
        db.commit()
        db.refresh(saved_report)
        return saved_report
    except Exception:
        db.rollback()
        raise


def delete_saved_report(db: Session, saved_report_id: int):
    saved_report = get_saved_report(db, saved_report_id)

    try:
        db.delete(saved_report)
        db.commit()
    except Exception:
        db.rollback()
        raise