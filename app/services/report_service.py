from sqlalchemy.orm import Session

from app.models.report import Report


def create_report(
    db: Session,
    cycle_id: int,
    report_name: str,
    report_type: str,
    generated_by: str,
):
    """
    Create and store a new report for a CTEM cycle.
    """

    new_report = Report(
        cycle_id=cycle_id,
        report_name=report_name,
        report_type=report_type,
        generated_by=generated_by,
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report