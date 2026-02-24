"""Tests for allocate/deallocate (T030).

Test data loaded from: data/fixtures/scenarios/allocate.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("allocate")


def _get(scenario_id: str, section: str = "allocate") -> dict:
    return next(s for s in _data[section] if s["id"] == scenario_id)


class TestAllocate:
    """allocate() — walk + commit."""

    def test_bits_marked_after_allocate(self):
        """Allocated bits should be 0 (occupied)."""
        from scheduling_primitives.occupancy import allocate

        spec = _get("bits_marked")
        bm = make_bitmap(spec["calendar"])
        record = allocate(bm, spec["operation_id"],
                          earliest_start=spec["earliest_start"],
                          work_units=spec["work_units"])

        assert record.start == spec["expected_start"]
        assert record.finish == spec["expected_finish"]
        expected_spans = tuple(tuple(s) for s in spec["expected_spans"])
        assert record.spans == expected_spans

        lo, hi = spec["check_bits_zero_range"]
        for i in range(lo, hi):
            assert bm.bits[i] == 0, f"bit {i} should be occupied after allocate"

    def test_allocate_returns_correct_record(self):
        """Returned AllocationRecord has correct fields."""
        from scheduling_primitives.occupancy import allocate

        spec = _get("bits_marked")
        bm = make_bitmap(spec["calendar"])
        record = allocate(bm, spec["operation_id"],
                          earliest_start=spec["earliest_start"],
                          work_units=spec["work_units"])
        assert record.operation_id == spec["operation_id"]
        assert record.resource_id == bm.resource_id
        assert record.start == spec["expected_start"]
        assert record.finish == spec["expected_finish"]
        assert record.work_units == spec["work_units"]
        assert record.allow_split is False

    def test_sequential_allocates(self):
        """Two sequential allocates: second starts after first."""
        from scheduling_primitives.occupancy import allocate

        spec = _get("sequential")
        bm = make_bitmap(spec["calendar"])
        for step in spec["sequence"]:
            r = allocate(bm, step["operation_id"],
                         earliest_start=step["earliest_start"],
                         work_units=step["work_units"])
            assert r.start == step["expected_start"], spec["notes"]
            assert r.finish == step["expected_finish"], spec["notes"]


class TestDeallocate:
    """deallocate() — exact inverse of allocate."""

    def test_bits_restored_after_deallocate(self):
        """Deallocate restores bits to free (1)."""
        from scheduling_primitives.occupancy import allocate, deallocate

        spec = _get("restore_single", "deallocate")
        bm = make_bitmap(spec["calendar"])
        bits_before = bytes(bm.bits)
        record = allocate(bm, spec["operation_id"],
                          earliest_start=spec["earliest_start"],
                          work_units=spec["work_units"])
        deallocate(bm, record)
        assert bytes(bm.bits) == bits_before

    def test_deallocate_exact_inverse(self):
        """State after deallocate is bit-identical to state before allocate."""
        from scheduling_primitives.occupancy import allocate, deallocate

        spec = _get("restore_multiple_reverse", "deallocate")
        bm = make_bitmap(spec["calendar"])
        snap = bytes(bm.bits)
        records = []
        for step in spec["sequence"]:
            r = allocate(bm, step["operation_id"],
                         earliest_start=step["earliest_start"],
                         work_units=step["work_units"])
            records.append(r)
        # Deallocate in reverse order
        for r in reversed(records):
            deallocate(bm, r)
        assert bytes(bm.bits) == snap

    def test_splittable_deallocate(self):
        """Deallocate a splittable allocation restores all spans."""
        from scheduling_primitives.occupancy import allocate, deallocate

        spec = _get("splittable_restore", "deallocate")
        bm = make_bitmap(spec["calendar"])
        snap = bytes(bm.bits)
        record = allocate(bm, spec["operation_id"],
                          earliest_start=spec["earliest_start"],
                          work_units=spec["work_units"],
                          allow_split=spec.get("allow_split", False))
        assert len(record.spans) == spec["expected_span_count"]
        deallocate(bm, record)
        assert bytes(bm.bits) == snap
