from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.report_schedule import ReportSchedule


def create_report_schedule(db: Session, schedule):
    start_at = schedule.start_at

    # Store the supplied start time as the first scheduled run.
    if start_at.tzinfo is not None:
        start_at = start_at.astimezone(timezone.utc).replace(tzinfo=None)

    new_schedule = ReportSchedule(
        cycle_id=schedule.cycle_id,
        report_name=schedule.report_name,
        report_type=schedule.report_type,
        frequency=schedule.frequency,
        start_at=start_at,
        recipients=schedule.recipients,
        delivered_recipients=[],
        report_format=schedule.report_format,
        enabled=schedule.enabled,
        created_by=schedule.created_by,
        next_run_at=start_at if schedule.enabled else None,
    )

    try:
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule
    except Exception:
        db.rollback()
        raise


def get_report_schedules(db: Session):
    return (
        db.query(ReportSchedule)
        .order_by(ReportSchedule.created_at.desc())
        .all()
    )


def get_report_schedule(db: Session, schedule_id: int):
    schedule = (
        db.query(ReportSchedule)
        .filter(ReportSchedule.id == schedule_id)
        .first()
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Report schedule not found",
        )

    return schedule


def update_report_schedule(db: Session, schedule_id: int, updates: dict):
    schedule = get_report_schedule(db, schedule_id)

    if "start_at" in updates and updates["start_at"] is not None:
        start_at = updates["start_at"]

        if start_at.tzinfo is not None:
            start_at = start_at.astimezone(timezone.utc).replace(tzinfo=None)

        updates["start_at"] = start_at

        # Reset the next run when the start time changes.
        updates["next_run_at"] = start_at if updates.get(
            "enabled", schedule.enabled
        ) else None

    if updates.get("enabled") is False:
        updates["next_run_at"] = None
    elif updates.get("enabled") is True and schedule.next_run_at is None:
        updates["next_run_at"] = updates.get("start_at", schedule.start_at)

    for field, value in updates.items():
        setattr(schedule, field, value)

    try:
        db.commit()
        db.refresh(schedule)
        return schedule
    except Exception:
        db.rollback()
        raise


def delete_report_schedule(db: Session, schedule_id: int):
    schedule = get_report_schedule(db, schedule_id)

    try:
        db.delete(schedule)
        db.commit()
    except Exception:
        db.rollback()
        raise
