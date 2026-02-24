"""Tests for planned exceptions (T012).

Test data loaded from: data/fixtures/scenarios/periods_for_date.json
"""

from __future__ import annotations

from datetime import date

import pytest

from conftest import load_scenarios, make_calendar, parse_time_pair

_scenarios = load_scenarios("periods_for_date")

# Exception-related scenarios
_EXCEPTION_IDS = (
    "holiday_full_day",
    "overtime_non_working",
    "normal_unaffected",
    "partial_day",
    "multi_exception",
    "holiday_on_non_working",
)


class TestPlannedExceptions:
    """Planned exceptions: holidays, overtime, partial days."""

    @pytest.mark.parametrize(
        "spec",
        [s for s in _scenarios if s["id"] in _EXCEPTION_IDS],
        ids=lambda s: s["id"],
    )
    def test_exception_periods(self, spec):
        """periods_for_date with exceptions returns expected time pairs."""
        cal = make_calendar(spec["calendar"])
        d = date.fromisoformat(spec["date"])
        periods = cal.periods_for_date(d)
        expected = [parse_time_pair(p) for p in spec["expected"]]
        assert periods == expected, spec["notes"]
