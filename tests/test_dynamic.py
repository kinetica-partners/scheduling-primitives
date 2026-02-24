"""Tests for dynamic exceptions — apply_dynamic_exception (T043-T047).

Test data loaded from: data/fixtures/scenarios/dynamic.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("dynamic")


class TestCapacityRemoval:
    """Dynamic capacity removal (is_working=False): machine breakdowns, closures."""

    def test_breakdown_free_time(self):
        """Removing free working time sets bits to 0, no conflicts."""
        from scheduling_primitives.occupancy import apply_dynamic_exception

        spec = _data["capacity_removal"][0]
        bm = make_bitmap(spec["calendar"])

        # Verify bits are free before removal
        for i in range(spec["start_offset"], spec["end_offset"]):
            assert bm.bits[i] == 1

        conflicts = apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=False
        )

        # Bits should now be 0
        for i in range(spec["start_offset"], spec["end_offset"]):
            assert bm.bits[i] == 0, f"bit {i} should be non-working"

        assert conflicts == [], spec["notes"]

    def test_breakdown_overlapping_allocation(self):
        """Removing time that overlaps an allocation detects conflicts."""
        from scheduling_primitives.occupancy import allocate, apply_dynamic_exception

        spec = _data["capacity_removal"][1]
        bm = make_bitmap(spec["calendar"])

        pre = spec["pre_allocate"]
        allocate(bm, pre["operation_id"],
                 earliest_start=pre["earliest_start"],
                 work_units=pre["work_units"])

        conflicts = apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=False
        )

        assert len(conflicts) > 0, "should detect conflict with OP-1"
        assert conflicts[0].operation_id == pre["operation_id"]

    def test_breakdown_non_working(self):
        """Removing already non-working time has no effect."""
        from scheduling_primitives.occupancy import apply_dynamic_exception

        spec = _data["capacity_removal"][2]
        bm = make_bitmap(spec["calendar"])
        bits_before = bytes(bm.bits)

        conflicts = apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=False
        )

        assert bytes(bm.bits) == bits_before, spec["notes"]
        assert conflicts == []


class TestCapacityAddition:
    """Dynamic capacity addition (is_working=True): overtime, extra shifts."""

    def test_overtime_non_working(self):
        """Adding working time to non-working period sets bits to 1."""
        from scheduling_primitives.occupancy import apply_dynamic_exception

        spec = _data["capacity_addition"][0]
        bm = make_bitmap(spec["calendar"])

        # Verify bits are non-working before
        for i in range(spec["start_offset"], spec["end_offset"]):
            assert bm.bits[i] == 0

        apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=True
        )

        # Bits should now be free
        for i in range(spec["start_offset"], spec["end_offset"]):
            assert bm.bits[i] == 1, f"bit {i} should be free (overtime)"

    def test_overtime_already_working(self):
        """Adding working time to already-working period is a no-op."""
        from scheduling_primitives.occupancy import apply_dynamic_exception

        spec = _data["capacity_addition"][1]
        bm = make_bitmap(spec["calendar"])
        bits_before = bytes(bm.bits)

        apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=True
        )

        assert bytes(bm.bits) == bits_before, spec["notes"]

    def test_overtime_partial_overlap(self):
        """Adding time that partially extends past working hours."""
        from scheduling_primitives.occupancy import apply_dynamic_exception

        spec = _data["capacity_addition"][2]
        bm = make_bitmap(spec["calendar"])

        # Mon 17:00-20:00 (offsets 1020-1200) should be non-working before
        for i in range(1020, 1200):
            assert bm.bits[i] == 0, f"bit {i} should be non-working before"

        apply_dynamic_exception(
            bm, spec["start_offset"], spec["end_offset"], is_working=True
        )

        # Now 17:00-20:00 should be free
        for i in range(1020, 1200):
            assert bm.bits[i] == 1, f"bit {i} should be free after overtime"
