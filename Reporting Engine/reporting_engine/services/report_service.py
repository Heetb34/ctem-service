from collections import Counter
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from reporting_engine.models.report import Report
from reporting_engine.services.ctem_client import (
    get_exposures,
    get_validation_plans,
    get_remediations,
    get_exceptions,
    get_framework_mappings,
)


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _serialize_rows(rows, fields):
    return [
        {field: _json_value(row.get(field)) for field in fields}
        for row in rows
    ]


def _count_by(rows, field):
    values = [
        str(row.get(field) or "Unknown")
        for row in rows
    ]
    return dict(sorted(Counter(values).items()))


def _percentage(part, total):
    return round((part / total) * 100, 2) if total else 0.0


def _filter_values(value):
    if value is None or value == "":
        return []

    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [
        str(item).strip().lower()
        for item in values
        if str(item).strip()
    ]


def _parse_date_bound(value, end=False):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(
            value,
            time.max if end else time.min,
        )
    else:
        text = str(value).strip()

        if len(text) == 10:
            parsed_date = date.fromisoformat(text)
            parsed = datetime.combine(
                parsed_date,
                time.max if end else time.min,
            )
        else:
            parsed = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed


def _parse_row_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed


def _build_exposure_trend(exposures):
    monthly = {}

    for exposure in exposures:
        created_at = _parse_row_datetime(exposure.get("created_at"))

        if not created_at:
            continue

        month = created_at.strftime("%Y-%m")
        severity = str(exposure.get("severity") or "Unknown")
        monthly.setdefault(month, Counter())[severity] += 1

    return [
        {
            "month": month,
            "severity_counts": dict(sorted(counts.items())),
            "total": sum(counts.values()),
        }
        for month, counts in sorted(monthly.items())
    ]


def create_report(
    db: Session,
    cycle_id,
    report_name,
    report_type,
    generated_by,
    filters=None,
):
    filters = filters or {}

    # Retrieve CTEM records through the CTEM REST API.
    exposures = get_exposures(cycle_id)
    validations = get_validation_plans(cycle_id)
    remediations = get_remediations(cycle_id)
    exceptions = get_exceptions(cycle_id)
    mappings = get_framework_mappings(cycle_id)

    # Apply exposure filters.
    severity_values = _filter_values(filters.get("severity"))
    status_values = _filter_values(filters.get("status"))

    start_date = _parse_date_bound(filters.get("start_date"))
    end_date = _parse_date_bound(
        filters.get("end_date"),
        end=True,
    )

    filtered_exposures = []

    for exposure in exposures:
        severity = str(exposure.get("severity") or "").lower()
        status = str(exposure.get("status") or "").lower()

        if severity_values and severity not in severity_values:
            continue

        if status_values and status not in status_values:
            continue

        created_at = _parse_row_datetime(exposure.get("created_at"))

        if start_date and (not created_at or created_at < start_date):
            continue

        if end_date and (not created_at or created_at > end_date):
            continue

        filtered_exposures.append(exposure)

    exposures = filtered_exposures

    # Keep related records consistent with the filtered exposures.
    filters_active = any(
        bool(filters.get(key))
        for key in ("severity", "status", "start_date", "end_date")
    )

    if filters_active:
        exposure_ids = {
            item.get("id")
            for item in exposures
        }

        validations = [
            item for item in validations
            if item.get("exposure_id") in exposure_ids
        ]

        remediations = [
            item for item in remediations
            if item.get("exposure_id") in exposure_ids
        ]

        exceptions = [
            item for item in exceptions
            if item.get("exposure_id") in exposure_ids
        ]

    # Framework mappings remain cycle-wide.
    severity_counts = _count_by(exposures, "severity")
    validation_counts = _count_by(validations, "validation_status")
    remediation_counts = _count_by(remediations, "remediation_status")
    exception_counts = _count_by(exceptions, "exception_status")
    framework_counts = _count_by(mappings, "status")

    risk_scores = [
        item.get("risk_score")
        for item in exposures
        if item.get("risk_score") is not None
    ]

    average_risk_score = (
        round(sum(risk_scores) / len(risk_scores), 2)
        if risk_scores
        else None
    )

    distinct_assets = {
        item.get("asset_name")
        for item in exposures
        if item.get("asset_name")
    }

    exposure_details = _serialize_rows(
        exposures,
        [
            "id", "asset_name", "asset_id", "vulnerability",
            "severity", "risk_score", "status", "priority",
            "priority_score", "beta_risk_rating",
            "business_criticality", "created_at", "updated_at",
        ],
    )

    validation_details = _serialize_rows(
        validations,
        [
            "id", "exposure_id", "validation_type",
            "validation_status", "assigned_to", "planned_date", "remarks",
        ],
    )

    remediation_details = _serialize_rows(
        remediations,
        [
            "id", "exposure_id", "remediation_status",
            "assigned_to", "completion_date", "remediation_notes",
        ],
    )

    exception_details = _serialize_rows(
        exceptions,
        [
            "id", "exposure_id", "exception_reason",
            "approved_by", "exception_status", "expiry_date",
        ],
    )

    framework_details = _serialize_rows(
        mappings,
        ["id", "framework_name", "control_name", "status"],
    )

    report_data = {
        "metadata": {
            "cycle_id": cycle_id,
            "report_name": report_name,
            "report_type": report_type,
            "generated_by": generated_by,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": "CTEM REST API",
            "filters": filters,
        },
        "summary": {
            "total_exposures": len(exposures),
            "distinct_assets": len(distinct_assets),
            "average_risk_score": average_risk_score,
            "severity_breakdown": severity_counts,
            "total_validations": len(validations),
            "validation_status_breakdown": validation_counts,
            "total_remediations": len(remediations),
            "remediation_status_breakdown": remediation_counts,
            "total_exceptions": len(exceptions),
            "exception_status_breakdown": exception_counts,
            "total_framework_mappings": len(mappings),
            "framework_status_breakdown": framework_counts,
            "remediation_completion_percentage": _percentage(
                sum(
                    count
                    for status, count in remediation_counts.items()
                    if status.lower() == "completed"
                ),
                len(remediations),
            ),
        },
        "sections": {
            "exposures": exposure_details,
            "validations": validation_details,
            "remediations": remediation_details,
            "exceptions": exception_details,
            "framework_mappings": framework_details,
            "exposure_trend_by_month": _build_exposure_trend(exposures),
        },
    }

    new_report = Report(
        cycle_id=cycle_id,
        report_name=report_name,
        report_type=report_type,
        generated_by=generated_by,
        report_data=report_data,
    )

    try:
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        return new_report
    except Exception:
        db.rollback()
        raise
