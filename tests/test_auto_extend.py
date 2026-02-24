"""Tests for auto-extension of OccupancyBitmap (T036).

Test data loaded from: data/fixtures/scenarios/auto_extend.json
"""

from __future__ import annotations

import pytest

from conftest import EPOCH, load_scenarios, make_bitmap

_data = load_scenarios("auto_extend")


def _get(scenario_id: str) -> dict:
    return next(s for s in _data["auto_extend"] if s["id"] == scenario_id)


class TestAutoExtend:
    """Auto-extension when walk reaches beyond horizon."""

    def test_walk_beyond_horizon_triggers_extension(self):
        """Walk for work that doesn't fit in initial 2-day horizon extends bitmap."""
        from scheduling_primitives.occupancy import walk

        spec = _get("walk_triggers_extension")
        bm = make_bitmap(spec["calendar"], horizon_end=spec["horizon_end"])
        initial_len = len(bm.bits)
        assert initial_len == spec["initial_bits"]

        record = walk(bm, spec["operation_id"],
                       earliest_start=spec["earliest_start"],
                       work_units=spec["work_units"],
                       allow_split=spec["allow_split"])
        assert len(bm.bits) > initial_len
        assert record.work_units == spec["work_units"]

    def test_extended_bitmap_is_consistent(self):
        """Extended region has correct free/non-working bits from calendar."""
        from scheduling_primitives.occupancy import walk

        spec = _get("extended_consistency")
        bm = make_bitmap(spec["calendar"], horizon_end=spec["horizon_end"])

        walk(bm, spec["operation_id"],
             earliest_start=spec["earliest_start"],
             work_units=spec["work_units"],
             allow_split=spec["allow_split"])

        assert bm.horizon_end > spec["initial_bits"]
        check_bit = spec["check_free_bit"]
        if check_bit < len(bm.bits):
            assert bm.bits[check_bit] == 1, (
                f"bit {check_bit} should be free in extended region"
            )

    def test_allocate_beyond_horizon(self):
        """Allocate that requires extension works correctly."""
        from scheduling_primitives.occupancy import allocate

        spec = _get("allocate_three_days")
        bm = make_bitmap(spec["calendar"], horizon_end=spec["horizon_end"])

        for step in spec["sequence"]:
            r = allocate(bm, step["operation_id"],
                         earliest_start=step["earliest_start"],
                         work_units=step["work_units"])
            if "expected_start" in step:
                assert r.start == step["expected_start"], spec["notes"]
            if "expected_start_gte" in step:
                assert r.start >= step["expected_start_gte"], spec["notes"]
