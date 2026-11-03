
from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.exposure import Exposure


def _period_summary(
    db: Session,
    cycle_id: int | None,
    start_date: date,
    end_date: date,
):
    start = datetime.combine(start_date, time.min)
    end_exclusive = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
    )

    query = db.query(Exposure).filter(
        Exposure.created_at >= start,
        Exposure.created_at < end_exclusive,
    )

    if cycle_id is not None:
        query = query.filter(Exposure.cycle_id == cycle_id)

    exposures = query.all()

    severity_counts = Counter(
        str(item.severity or "Unknown")
        for item in exposures
    )

    risk_scores = [
        float(item.risk_score)
        for item in exposures
        if item.risk_score is not None
    ]

    assets = {
        item.asset_id or item.asset_name
        for item in exposures
        if item.asset_id or item.asset_name
    }

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_exposures": len(exposures),
        "distinct_assets": len(assets),
        "average_risk_score": (
            round(sum(risk_scores) / len(risk_scores), 2)
            if risk_scores
            else None
        ),
        "severity_breakdown": dict(sorted(severity_counts.items())),
    }


def _percentage_change(previous, current):
    if previous == 0:
        return 0.0 if current == 0 else None

    return round(((current - previous) / previous) * 100, 2)


def compare_exposure_periods(
    db: Session,
    cycle_id: int | None,
    period_a_start: date,
    period_a_end: date,
    period_b_start: date,
    period_b_end: date,
):
    period_a = _period_summary(
        db, cycle_id, period_a_start, period_a_end
    )
    period_b = _period_summary(
        db, cycle_id, period_b_start, period_b_end
    )

    a_total = period_a["total_exposures"]
    b_total = period_b["total_exposures"]

    a_risk = period_a["average_risk_score"]
    b_risk = period_b["average_risk_score"]

    severities = sorted(
        set(period_a["severity_breakdown"])
        | set(period_b["severity_breakdown"])
    )

    severity_comparison = {}

    for severity in severities:
        a_count = period_a["severity_breakdown"].get(severity, 0)
        b_count = period_b["severity_breakdown"].get(severity, 0)

        severity_comparison[severity] = {
            "period_a": a_count,
            "period_b": b_count,
            "delta": b_count - a_count,
            "change_percent": _percentage_change(a_count, b_count),
        }

    return {
        "cycle_id": cycle_id,
        "period_a": period_a,
        "period_b": period_b,
        "comparison": {
            "exposure_count_delta": b_total - a_total,
            "exposure_count_change_percent": _percentage_change(
                a_total, b_total
            ),
            "average_risk_score_delta": (
                round(b_risk - a_risk, 2)
                if a_risk is not None and b_risk is not None
                else None
            ),
            "severity_comparison": severity_comparison,
        },
    }
