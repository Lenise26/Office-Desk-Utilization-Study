from __future__ import annotations

from app.analytics import PERIODS, _period_for_hour, _rate


def test_period_boundaries():
    assert _period_for_hour(8) == "morning"
    assert _period_for_hour(11) == "midday"
    assert _period_for_hour(14) == "afternoon"
    assert _period_for_hour(17) == "late"
    assert _period_for_hour(20) == "other"


def test_periods_do_not_overlap():
    covered = []
    for start, end in PERIODS.values():
        covered.extend(range(start, end))
    assert len(covered) == len(set(covered))


def test_rate_handles_empty_total():
    assert _rate(0, 0) == 0.0
    assert _rate(1, 4) == 25.0
