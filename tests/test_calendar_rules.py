"""Tests for calendar weekly rules and overnight splitting (T010, T011).

Test data loaded from: data/fixtures/scenarios/periods_for_date.json
"""

from __future__ import annotations

from datetime import date, time

import pytest

from conftest import load_scenarios, make_calendar, parse_time_pair

_scenarios = load_scenarios("periods_for_date")


def _get(scenario_id: str) -> dict:
    """Fetch a single scenario by id."""
    return next(s for s in _scenarios if s["id"] == scenario_id)


class TestBasicWeeklyRules:
    """T010: Single-period, multi-period, and non-working days."""

    @pytest.mark.parametrize(
        "spec",
        [s for s in _scenarios if s["id"] in (
            "single_period", "split_shift", "non_working_sat", "non_working_sun",
        )],
        ids=lambda s: s["id"],
    )
    def test_periods_for_date(self, spec):
        """periods_for_date returns expected time pairs."""
        cal = make_calendar(spec["calendar"])
        d = date.fromisoformat(spec["date"])
        periods = cal.periods_for_date(d)
        expected = [parse_time_pair(p) for p in spec["expected"]]
        assert periods == expected, spec["notes"]


class TestOvernightRules:
    """T011: Rules where end_time < start_time (crosses midnight)."""

    @pytest.mark.parametrize(
        "spec",
        [s for s in _scenarios if s["id"].startswith("overnight_")],
        ids=lambda s: s["id"],
    )
    def test_overnight_contains(self, spec):
        """Overnight rules produce expected period(s)."""
        cal = make_calendar(spec["calendar"])
        d = date.fromisoformat(spec["date"])
        periods = cal.periods_for_date(d)

        if "expected_contains" in spec:
            pair = parse_time_pair(spec["expected_contains"])
            assert pair in periods, f"{pair} not in {periods} — {spec['notes']}"

        if "expected_contains_all" in spec:
            for raw_pair in spec["expected_contains_all"]:
                pair = parse_time_pair(raw_pair)
                assert pair in periods, f"{pair} not in {periods} — {spec['notes']}"
