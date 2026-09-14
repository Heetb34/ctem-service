from sqlalchemy.orm import Session

from app.models.exposure import Exposure


def get_trend_analysis(
    db: Session,
    cycle_id: int
):
    exposures = (
        db.query(Exposure)
        .filter(Exposure.cycle_id == cycle_id)
        .all()
    )

    total = len(exposures)

    critical = sum(
        1 for exposure in exposures
        if exposure.severity.lower() == "critical"
    )

    high = sum(
        1 for exposure in exposures
        if exposure.severity.lower() == "high"
    )

    medium = sum(
        1 for exposure in exposures
        if exposure.severity.lower() == "medium"
    )

    low = sum(
        1 for exposure in exposures
        if exposure.severity.lower() == "low"
    )

    average_risk_score = (
        sum(exposure.risk_score for exposure in exposures) / total
        if total > 0
        else 0
    )

    return {
        "cycle_id": cycle_id,
        "total_exposures": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "average_risk_score": round(average_risk_score, 2)
    }