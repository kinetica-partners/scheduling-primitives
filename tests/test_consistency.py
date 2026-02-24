"""Tests for cross-layer consistency (T050).

Verifies that Layer 1 (calendar.add_minutes) and Layer 2
(splittable allocate on bitmap) agree on finish datetimes.

Test data loaded from: data/fixtures/scenarios/consistency.json
"""

from __future__ import annotations

from datetime import datetime

import pytest

from conftest import EPOCH, load_scenarios, make_bitmap, make_calendar

_data = load_scenarios("consistency")


class TestCrossLayerConsistency:
    """Layer 1 add_minutes == Layer 2 splittable allocate finish."""

    @pytest.mark.parametrize("spec", _data["cross_layer"], ids=lambda s: s["id"])
    def test_minute_resolution(self, spec):
        """calendar.add_minutes matches allocate finish at minute grain."""
        from scheduling_primitives.occupancy import allocate
        from scheduling_primitives.resolution import MINUTE

        cal = make_calendar(spec["calendar"])
        bm = make_bitmap(spec["calendar"])

        start_dt = datetime.fromisoformat(spec["start_datetime"])
        expected = datetime.fromisoformat(spec["expected_finish"])

        # Layer 1: calendar arithmetic
        finish_layer1 = cal.add_minutes(start_dt, spec["work_units_minute"])

        # Layer 2: splittable allocation on fresh bitmap
        rec = allocate(
            bm, "OP-CONSIST",
            earliest_start=spec["start_offset_minute"],
            work_units=spec["work_units_minute"],
            allow_split=True,
        )
        finish_layer2 = MINUTE.to_datetime(rec.finish, EPOCH)

        assert finish_layer1 == expected, f"Layer 1: {finish_layer1} != {expected}"
        assert finish_layer2 == expected, f"Layer 2: {finish_layer2} != {expected}"

    @pytest.mark.parametrize("spec", _data["cross_layer"], ids=lambda s: s["id"])
    def test_hour_resolution(self, spec):
        """calendar.add_minutes matches allocate finish at hour grain."""
        from scheduling_primitives.occupancy import allocate
        from scheduling_primitives.resolution import HOUR

        cal = make_calendar(spec["calendar"])
        bm = make_bitmap(spec["calendar"], resolution="hour")

        start_dt = datetime.fromisoformat(spec["start_datetime"])
        expected = datetime.fromisoformat(spec["expected_finish"])

        # Layer 1: calendar arithmetic (always in minutes)
        finish_layer1 = cal.add_minutes(start_dt, spec["work_units_minute"])

        # Layer 2: splittable allocation at hour grain
        rec = allocate(
            bm, "OP-CONSIST-HR",
            earliest_start=spec["start_offset_hour"],
            work_units=spec["work_units_hour"],
            allow_split=True,
        )
        finish_layer2 = HOUR.to_datetime(rec.finish, EPOCH)

        assert finish_layer1 == expected, f"Layer 1: {finish_layer1} != {expected}"
        assert finish_layer2 == expected, f"Layer 2 (hour): {finish_layer2} != {expected}"
