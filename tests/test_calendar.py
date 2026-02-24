"""Tests for calendar time arithmetic: add_minutes, subtract_minutes,
working_minutes_between, working_intervals_in_range (T018-T021).

Test data loaded from: data/fixtures/scenarios/calendar_arithmetic.json
"""

from __future__ import annotations

from datetime import datetime

import pytest

from conftest import load_scenarios, make_calendar

_data = load_scenarios("calendar_arithmetic")


class TestForwardWalk:
    """T018: add_minutes — forward walk through working time."""

    @pytest.mark.parametrize("spec", _data["add_minutes"], ids=lambda s: s["id"])
    def test_add_minutes(self, spec):
        cal = make_calendar(spec["calendar"])
        start = datetime.fromisoformat(spec["start"])
        expected = datetime.fromisoformat(spec["expected"])
        result = cal.add_minutes(start, spec["minutes"])
        assert result == expected, spec["notes"]


class TestBackwardWalk:
    """T019: subtract_minutes — backward walk through working time."""

    @pytest.mark.parametrize("spec", _data["subtract_minutes"], ids=lambda s: s["id"])
    def test_subtract_minutes(self, spec):
        cal = make_calendar(spec["calendar"])
        start = datetime.fromisoformat(spec["start"])
        expected = datetime.fromisoformat(spec["expected"])
        result = cal.subtract_minutes(start, spec["minutes"])
        assert result == expected, spec["notes"]


class TestWorkingMinutesBetween:
    """T020: working_minutes_between — count working time."""

    @pytest.mark.parametrize(
        "spec", _data["working_minutes_between"], ids=lambda s: s["id"]
    )
    def test_working_minutes_between(self, spec):
        cal = make_calendar(spec["calendar"])
        start = datetime.fromisoformat(spec["start"])
        end = datetime.fromisoformat(spec["end"])
        result = cal.working_minutes_between(start, end)
        assert result == spec["expected"], spec["notes"]


class TestWorkingIntervalsInRange:
    """T020: working_intervals_in_range — enumerate intervals."""

    @pytest.mark.parametrize(
        "spec", _data["working_intervals_in_range"], ids=lambda s: s["id"]
    )
    def test_intervals(self, spec):
        cal = make_calendar(spec["calendar"])
        start = datetime.fromisoformat(spec["start"])
        end = datetime.fromisoformat(spec["end"])
        intervals = list(cal.working_intervals_in_range(start, end))
        expected = [
            (datetime.fromisoformat(pair[0]), datetime.fromisoformat(pair[1]))
            for pair in spec["expected"]
        ]
        assert intervals == expected, spec["notes"]


class TestRoundTripConsistency:
    """T021: add_minutes(subtract_minutes(dt, n), n) == dt."""

    @pytest.mark.parametrize("spec", _data["round_trips"], ids=lambda s: s["id"])
    def test_round_trip(self, spec):
        cal = make_calendar(spec["calendar"])
        dt = datetime.fromisoformat(spec["datetime"])
        n = spec["minutes"]
        if spec.get("direction") == "reverse":
            # subtract(add(dt, n), n) == dt
            assert cal.subtract_minutes(cal.add_minutes(dt, n), n) == dt
        else:
            # add(subtract(dt, n), n) == dt
            assert cal.add_minutes(cal.subtract_minutes(dt, n), n) == dt
