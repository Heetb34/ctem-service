from sqlalchemy.orm import Session

from app.models.schedule import Schedule


def create_schedule(
    db: Session,
    schedule
):
    new_schedule = Schedule(
        cycle_name=schedule.cycle_name,
        frequency=schedule.frequency,
        start_date=schedule.start_date,
        status=schedule.status
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return new_schedule


def get_schedules(
    db: Session
):
    return db.query(Schedule).all()