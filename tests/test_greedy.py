"""Tests for greedy reference scheduler (T054).

Test data loaded from: data/fixtures/scenarios/greedy.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios, make_bitmap

_data = load_scenarios("greedy")


def _build_resources(calendars: dict[str, str]):
    """Build resource bitmaps from calendar name mapping."""
    return {rid: make_bitmap(cal) for rid, cal in calendars.items()}


class TestGreedySchedule:
    """greedy_schedule() composes primitives into a simple scheduling pass."""

    def test_multi_resource(self):
        """All operations scheduled across multiple resources, no overlap."""
        from scheduling_primitives.greedy import Operation, greedy_schedule

        spec = next(s for s in _data["greedy_schedule"] if s["id"] == "multi_resource")
        resources = _build_resources(spec["calendars"])

        ops = [Operation(**o) for o in spec["operations"]]
        results = greedy_schedule(ops, resources)

        assert len(results) == spec["expected_count"]

        # Verify no overlapping spans on the same resource
        for rid in spec["calendars"]:
            res_allocs = [r for r in results if r.resource_id == rid]
            occupied: set[int] = set()
            for alloc in res_allocs:
                for begin, end in alloc.spans:
                    for t in range(begin, end):
                        assert t not in occupied, (
                            f"Double-booking at offset {t} on {rid}"
                        )
                        occupied.add(t)

    def test_splittable_mixed(self):
        """Splittable op splits across shift boundary when blocked."""
        from scheduling_primitives.greedy import Operation, greedy_schedule

        spec = next(s for s in _data["greedy_schedule"] if s["id"] == "splittable_mixed")
        resources = _build_resources(spec["calendars"])

        ops = [Operation(**o) for o in spec["operations"]]
        results = greedy_schedule(ops, resources)

        assert len(results) == spec["expected_count"]

        # OP-B should have 2 spans (split across overnight gap)
        op_b = next(r for r in results if r.operation_id == "OP-B")
        assert len(op_b.spans) == spec["expected_op_b_spans"], (
            f"OP-B should have {spec['expected_op_b_spans']} spans, got {len(op_b.spans)}"
        )
        assert op_b.allow_split is True

    def test_priority_order(self):
        """Operations are scheduled in input order (priority)."""
        from scheduling_primitives.greedy import Operation, greedy_schedule

        spec = next(s for s in _data["greedy_schedule"] if s["id"] == "priority_order")
        resources = _build_resources(spec["calendars"])

        ops = [Operation(**o) for o in spec["operations"]]
        results = greedy_schedule(ops, resources)

        assert len(results) == spec["expected_count"]

        for result, expected_start in zip(results, spec["expected_starts"]):
            assert result.start == expected_start, (
                f"{result.operation_id}: expected start={expected_start}, "
                f"got {result.start}"
            )

    def test_all_operations_complete(self):
        """Every returned record has work_units matching the request."""
        from scheduling_primitives.greedy import Operation, greedy_schedule

        spec = next(s for s in _data["greedy_schedule"] if s["id"] == "multi_resource")
        resources = _build_resources(spec["calendars"])

        ops = [Operation(**o) for o in spec["operations"]]
        results = greedy_schedule(ops, resources)

        for op, result in zip(ops, results):
            assert result.work_units == op.work_units
            span_total = sum(end - begin for begin, end in result.spans)
            assert span_total == op.work_units
