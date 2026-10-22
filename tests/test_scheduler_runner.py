from datetime import datetime

import pytest

from app.services.report_scheduler_runner import _add_months, _next_occurrence

NOW = datetime(2026, 10, 20, 12, 0)


def test_add_months_clamps_to_month_end():
    assert _add_months(datetime(2026, 1, 31), 1) == datetime(2026, 2, 28)


def test_add_months_crosses_year():
    assert _add_months(datetime(2026, 11, 15, 9, 0), 3) == datetime(2027, 2, 15, 9, 0)


def test_once_has_no_next_run():
    assert _next_occurrence(datetime(2026, 10, 1), "once", NOW) is None


def test_daily():
    assert _next_occurrence(datetime(2026, 10, 20, 9, 0), "daily", NOW) == datetime(2026, 10, 21, 9, 0)


def test_weekly():
    assert _next_occurrence(datetime(2026, 10, 1, 10, 0), "weekly", NOW) == datetime(2026, 10, 22, 10, 0)


def test_monthly():
    assert _next_occurrence(datetime(2026, 8, 15, 10, 0), "monthly", NOW) == datetime(2026, 11, 15, 10, 0)


def test_quarterly():
    assert _next_occurrence(datetime(2026, 1, 10, 8, 0), "quarterly", NOW) == datetime(2027, 1, 10, 8, 0)


def test_unsupported_frequency_raises():
    with pytest.raises(ValueError):
        _next_occurrence(datetime(2026, 10, 1), "hourly", NOW)


def test_monthly_keeps_month_end():
    # The original code drifts: Jan 31 becomes Mar 28 instead of Mar 31.
    assert _next_occurrence(datetime(2026, 1, 31), "monthly", datetime(2026, 3, 1)) == datetime(2026, 3, 31)