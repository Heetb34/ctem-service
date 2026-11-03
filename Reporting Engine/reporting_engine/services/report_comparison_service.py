from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from reporting_engine.services.ctem_client import get_exposures


def _period_summary(
    exposures,
    start_date: date,
    end_date: date,
):
    start = datetime.combine(start_date, time.min)
    end_exclusive = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
    )

    period_exposures = []

    for item in exposures:
        created_at = item.get("created_at")

        if not created_at:
            continue

        if isinstance(created_at, datetime):
            parsed_date = created_at
        else:
            parsed_date = datetime.fromisoformat(
                str(created_at).replace("Z", "+00:00")
            )

        if parsed_date.tzinfo is not None:
            parsed_date = parsed_date.astimezone().replace(tzinfo=None)

        if start <= parsed_date < end_exclusive:
            period_exposures.append(item)

    severity_counts = Counter(
        str(item.get("severity") or "Unknown")
        for item in period_exposures
    )

    risk_scores = [
        float(item["risk_score"])
        for item in period_exposures
        if item.get("risk_score") is not None
    ]

    assets = {
        item.get("asset_id") or item.get("asset_name")
        for item in period_exposures
        if item.get("asset_id") or item.get("asset_name")
    }

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_exposures": len(period_exposures),
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
    if cycle_id is None:
        raise ValueError(
            "A cycle_id is required because the CTEM API currently "
            "provides cycle-scoped exposure retrieval."
        )

    exposures = get_exposures(cycle_id)

    period_a = _period_summary(
        exposures, period_a_start, period_a_end
    )
    period_b = _period_summary(
        exposures, period_b_start, period_b_end
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
