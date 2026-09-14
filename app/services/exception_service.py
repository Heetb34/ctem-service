from sqlalchemy.orm import Session

from app.models.exception import ExceptionManagement


def get_exceptions(db: Session, cycle_id: int):

    exceptions = (
        db.query(ExceptionManagement)
        .filter(ExceptionManagement.cycle_id == cycle_id)
        .all()
    )

    return exceptions