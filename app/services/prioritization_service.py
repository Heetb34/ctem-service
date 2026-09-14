from sqlalchemy.orm import Session

from app.models.exposure import Exposure


def calculate_priority(severity, risk_score):
    """
    Calculate priority based on severity and risk score.
    """

    severity = severity.lower()

    if severity == "critical":
        score = 100
    elif severity == "high":
        score = 80
    elif severity == "medium":
        score = 60
    else:
        score = 40

    score += risk_score

    if score >= 170:
        priority = "Critical"
    elif score >= 140:
        priority = "High"
    elif score >= 100:
        priority = "Medium"
    else:
        priority = "Low"

    return priority, score


def prioritize_cycle(db: Session, cycle_id: int):

    exposures = (
        db.query(Exposure)
        .filter(Exposure.cycle_id == cycle_id)
        .all()
    )

    if not exposures:
        return []

    for exposure in exposures:

        priority, score = calculate_priority(
            exposure.severity,
            exposure.risk_score
        )

        exposure.priority = priority
        exposure.priority_score = score

    db.commit()

    return exposures