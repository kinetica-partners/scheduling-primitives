"""Tests for OccupancyBitmap.from_calendar() (T027).

Test data loaded from: data/fixtures/scenarios/occupancy.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("occupancy")


class TestFromCalendar:
    """OccupancyBitmap.from_calendar materialisation."""

    @pytest.mark.parametrize(
        "spec", _data["bitmap_construction"], ids=lambda s: s["id"]
    )
    def test_bitmap_size_and_properties(self, spec):
        """Bitmap dimensions and free-bit totals match expectations."""
        bm = make_bitmap(
            spec["calendar"],
            horizon_start=spec["horizon_start"],
            horizon_end=spec["horizon_end"],
        )
        assert len(bm.bits) == spec["expected_total_bits"], "total bits"
        assert sum(bm.bits) == spec["expected_free_bits"], "free bits"
        assert bm.horizon_begin == spec["expected_horizon_begin"], "horizon_begin"
        assert bm.horizon_end == spec["expected_horizon_end"], "horizon_end"

    @pytest.mark.parametrize("spec", _data["bit_ranges"], ids=lambda s: s["id"])
    def test_bit_range_values(self, spec):
        """Specific bit ranges match expected values (0 or 1)."""
        calendar_name = spec.get("calendar", "standard")
        bm = make_bitmap(calendar_name)
        expected = spec["expected_value"]
        for i in range(spec["range_start"], spec["range_end"]):
            assert bm.bits[i] == expected, (
                f"bit {i}: expected {expected} — {spec['notes']}"
            )
