"""Tests for walk() — non-splittable and splittable (T028, T029).

Test data loaded from: data/fixtures/scenarios/walk.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("walk")


class TestNonSplittableWalk:
    """T028: Non-splittable walk — contiguous free run required."""

    @pytest.mark.parametrize("spec", _data["non_splittable"], ids=lambda s: s["id"])
    def test_walk(self, spec):
        """Walk finds contiguous free run matching expectations."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap(spec["calendar"])
        record = walk(bm, spec["operation_id"],
                       earliest_start=spec["earliest_start"],
                       work_units=spec["work_units"])
        assert record.start == spec["expected_start"], spec["notes"]
        assert record.finish == spec["expected_finish"], spec["notes"]
        expected_spans = tuple(tuple(s) for s in spec["expected_spans"])
        assert record.spans == expected_spans, spec["notes"]
        assert record.work_units == spec["work_units"]
        assert record.allow_split is False

    @pytest.mark.parametrize(
        "spec", _data["non_splittable_deadline"], ids=lambda s: s["id"]
    )
    def test_deadline_exceeded(self, spec):
        """Work that can't fit before deadline raises InfeasibleError."""
        from scheduling_primitives.occupancy import walk
        from scheduling_primitives.types import InfeasibleError

        bm = make_bitmap(spec["calendar"])
        with pytest.raises(InfeasibleError) as exc_info:
            walk(bm, spec["operation_id"],
                 earliest_start=spec["earliest_start"],
                 work_units=spec["work_units"],
                 deadline=spec["deadline"])
        assert exc_info.value.operation_id == spec["operation_id"]
        assert exc_info.value.reason == spec["expected_error"]

    def test_walk_is_read_only(self):
        """Walk does NOT mutate the bitmap (FR-022)."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap("standard")
        spec = _data["non_splittable"][0]
        bits_before = bytes(bm.bits)
        walk(bm, spec["operation_id"],
             earliest_start=spec["earliest_start"],
             work_units=spec["work_units"])
        assert bytes(bm.bits) == bits_before


class TestSplittableWalk:
    """T029: Splittable walk — greedy consumption across gaps."""

    @pytest.mark.parametrize("spec", _data["splittable"], ids=lambda s: s["id"])
    def test_splittable_walk(self, spec):
        """Splittable walk produces expected spans."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap(spec["calendar"])
        record = walk(bm, spec["operation_id"],
                       earliest_start=spec["earliest_start"],
                       work_units=spec["work_units"],
                       allow_split=True)
        assert record.start == spec["expected_start"], spec["notes"]
        assert record.finish == spec["expected_finish"], spec["notes"]
        expected_spans = tuple(tuple(s) for s in spec["expected_spans"])
        assert record.spans == expected_spans, spec["notes"]
        assert record.work_units == spec["work_units"]
        assert record.allow_split is True

    @pytest.mark.parametrize("spec", _data["min_split"], ids=lambda s: s["id"])
    def test_min_split_skips_small_fragments(self, spec):
        """Fragments below min_split threshold are skipped."""
        from scheduling_primitives.occupancy import allocate, walk

        bm = make_bitmap(spec["calendar"])
        pre = spec["pre_allocate"]
        allocate(bm, pre["operation_id"],
                 earliest_start=pre["earliest_start"],
                 work_units=pre["work_units"])
        record = walk(bm, spec["operation_id"],
                       earliest_start=spec["earliest_start"],
                       work_units=spec["work_units"],
                       allow_split=True,
                       min_split=spec["min_split"])
        assert record.spans[0][0] >= spec["expected_first_span_start_gte"], spec["notes"]

    @pytest.mark.parametrize(
        "spec", _data["splittable_deadline"], ids=lambda s: s["id"]
    )
    def test_splittable_deadline_exceeded(self, spec):
        """Splittable work that can't finish before deadline."""
        from scheduling_primitives.occupancy import walk
        from scheduling_primitives.types import InfeasibleError

        bm = make_bitmap(spec["calendar"])
        with pytest.raises(InfeasibleError):
            walk(bm, spec["operation_id"],
                 earliest_start=spec["earliest_start"],
                 work_units=spec["work_units"],
                 allow_split=True,
                 deadline=spec["deadline"])
