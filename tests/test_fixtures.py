"""Cross-platform test contract: fixture-driven parametric tests (T063-T065).

Each JSON fixture in data/fixtures/ is self-contained with calendar
definition, test scenarios, and expected results. Any implementation
in any language can run these same fixtures to prove correctness.

Test data loaded from: data/fixtures/*.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"

# Load all contract fixtures
_CONTRACT_FILES = ["simple", "multi_shift", "overnight", "resource_variety", "stress"]
_CONTRACTS: dict[str, dict] = {}
for _name in _CONTRACT_FILES:
    _path = FIXTURES_DIR / f"{_name}.json"
    with open(_path) as f:
        _CONTRACTS[_name] = json.load(f)


def _build_calendar(rules: dict, exceptions: dict):
    """Build a WorkingCalendar from rules/exceptions dicts."""
    from scheduling_primitives.calendar import WorkingCalendar

    int_rules = {int(k): v for k, v in rules.items()}
    return WorkingCalendar("contract", int_rules, exceptions)


def _build_bitmap(rules, exceptions, epoch_str, horizon):
    """Build an OccupancyBitmap from contract fixture data."""
    from scheduling_primitives.occupancy import OccupancyBitmap
    from scheduling_primitives.resolution import MINUTE

    cal = _build_calendar(rules, exceptions)
    epoch = datetime.fromisoformat(epoch_str)
    h_start = datetime.fromisoformat(horizon["start"])
    h_end = datetime.fromisoformat(horizon["end"])
    return OccupancyBitmap.from_calendar(cal, h_start, h_end, epoch, MINUTE)


# ---------------------------------------------------------------------------
# Single-calendar fixtures: simple, multi_shift, overnight
# ---------------------------------------------------------------------------
_SINGLE_CAL_IDS = ["simple", "multi_shift", "overnight"]


def _get_single_cal_forward_walk_cases():
    """Collect forward_walk test cases from single-calendar fixtures."""
    cases = []
    for fid in _SINGLE_CAL_IDS:
        fixture = _CONTRACTS[fid]
        for tc in fixture.get("tests", {}).get("forward_walk", []):
            cases.append(pytest.param(fixture, tc, id=f"{fid}_{tc['id']}"))
    return cases


def _get_single_cal_working_minutes_cases():
    cases = []
    for fid in _SINGLE_CAL_IDS:
        fixture = _CONTRACTS[fid]
        for tc in fixture.get("tests", {}).get("working_minutes", []):
            cases.append(pytest.param(fixture, tc, id=f"{fid}_{tc['id']}"))
    return cases


def _get_single_cal_allocation_cases():
    cases = []
    for fid in _SINGLE_CAL_IDS:
        fixture = _CONTRACTS[fid]
        for tc in fixture.get("tests", {}).get("allocations", []):
            cases.append(pytest.param(fixture, tc, id=f"{fid}_{tc['id']}"))
    return cases


class TestForwardWalk:
    """calendar.add_minutes matches expected finish across all fixtures."""

    @pytest.mark.parametrize("fixture, tc", _get_single_cal_forward_walk_cases())
    def test_forward_walk(self, fixture, tc):
        cal = _build_calendar(
            fixture["calendar"]["rules"],
            fixture["calendar"].get("exceptions", {}),
        )
        start = datetime.fromisoformat(tc["start"])
        expected = datetime.fromisoformat(tc["expected"])

        result = cal.add_minutes(start, tc["minutes"])
        assert result == expected, tc.get("notes", "")


class TestWorkingMinutes:
    """working_minutes_between matches expected across all fixtures."""

    @pytest.mark.parametrize("fixture, tc", _get_single_cal_working_minutes_cases())
    def test_working_minutes(self, fixture, tc):
        cal = _build_calendar(
            fixture["calendar"]["rules"],
            fixture["calendar"].get("exceptions", {}),
        )
        start = datetime.fromisoformat(tc["start"])
        end = datetime.fromisoformat(tc["end"])

        result = cal.working_minutes_between(start, end)
        assert result == tc["expected"], tc.get("notes", "")


class TestAllocations:
    """Allocations match expected start/finish/spans across all fixtures."""

    @pytest.mark.parametrize("fixture, tc", _get_single_cal_allocation_cases())
    def test_allocation(self, fixture, tc):
        from scheduling_primitives.occupancy import allocate

        bm = _build_bitmap(
            fixture["calendar"]["rules"],
            fixture["calendar"].get("exceptions", {}),
            fixture["epoch"],
            fixture["horizon"],
        )

        record = allocate(
            bm,
            tc["operation_id"],
            earliest_start=tc["earliest_start"],
            work_units=tc["work_units"],
            allow_split=tc.get("allow_split", False),
        )

        if "expected_start" in tc:
            assert record.start == tc["expected_start"]
        if "expected_finish" in tc:
            assert record.finish == tc["expected_finish"]
        if "expected_spans" in tc:
            assert record.spans == tuple(tuple(s) for s in tc["expected_spans"])
        if "expected_span_count" in tc:
            assert len(record.spans) == tc["expected_span_count"]
        if "expected_work_units" in tc:
            span_sum = sum(e - s for s, e in record.spans)
            assert span_sum == tc["expected_work_units"]


# ---------------------------------------------------------------------------
# Multi-resource fixture: resource_variety
# ---------------------------------------------------------------------------
class TestResourceVariety:
    """resource_variety: different calendar patterns produce correct results."""

    @pytest.mark.parametrize(
        "tc",
        _CONTRACTS["resource_variety"]["tests"]["working_minutes"],
        ids=lambda t: t["id"],
    )
    def test_working_minutes(self, tc):
        fixture = _CONTRACTS["resource_variety"]
        res_cfg = fixture["resources"][tc["resource_id"]]
        cal = _build_calendar(res_cfg["rules"], res_cfg.get("exceptions", {}))

        start = datetime.fromisoformat(tc["start"])
        end = datetime.fromisoformat(tc["end"])
        result = cal.working_minutes_between(start, end)
        assert result == tc["expected"], tc.get("notes", "")

    @pytest.mark.parametrize(
        "tc",
        _CONTRACTS["resource_variety"]["tests"]["allocations"],
        ids=lambda t: t["id"],
    )
    def test_allocation(self, tc):
        from scheduling_primitives.occupancy import allocate

        fixture = _CONTRACTS["resource_variety"]
        res_cfg = fixture["resources"][tc["resource_id"]]
        bm = _build_bitmap(
            res_cfg["rules"],
            res_cfg.get("exceptions", {}),
            fixture["epoch"],
            fixture["horizon"],
        )

        record = allocate(
            bm,
            tc["operation_id"],
            earliest_start=tc["earliest_start"],
            work_units=tc["work_units"],
            allow_split=tc.get("allow_split", False),
        )

        if "expected_start" in tc:
            assert record.start == tc["expected_start"]
        if "expected_finish" in tc:
            assert record.finish == tc["expected_finish"]
        if "expected_spans" in tc:
            assert record.spans == tuple(tuple(s) for s in tc["expected_spans"])


# ---------------------------------------------------------------------------
# Stress fixture: 20 operations, no overlaps, all scheduled
# ---------------------------------------------------------------------------
class TestStress:
    """stress: all operations scheduled without double-booking."""

    def test_all_scheduled_no_overlaps(self):
        from scheduling_primitives.occupancy import allocate

        fixture = _CONTRACTS["stress"]

        # Build resource bitmaps
        bitmaps = {}
        for rid, res_cfg in fixture["resources"].items():
            bitmaps[rid] = _build_bitmap(
                res_cfg["rules"],
                res_cfg.get("exceptions", {}),
                fixture["epoch"],
                fixture["horizon"],
            )

        # Schedule all operations
        results = []
        for tc in fixture["tests"]["allocations"]:
            record = allocate(
                bitmaps[tc["resource_id"]],
                tc["operation_id"],
                earliest_start=tc["earliest_start"],
                work_units=tc["work_units"],
                allow_split=tc.get("allow_split", False),
            )
            results.append(record)

        # Verify all scheduled
        assert len(results) == len(fixture["tests"]["allocations"])

        # Verify no overlaps per resource
        by_resource: dict[str, list] = {}
        for tc, record in zip(fixture["tests"]["allocations"], results):
            by_resource.setdefault(tc["resource_id"], []).append(record)

        for rid, allocs in by_resource.items():
            occupied: set[int] = set()
            for alloc in allocs:
                for begin, end in alloc.spans:
                    for t in range(begin, end):
                        assert t not in occupied, (
                            f"Double-booking at offset {t} on {rid} "
                            f"({alloc.operation_id})"
                        )
                        occupied.add(t)

        # Verify work_units match
        for tc, record in zip(fixture["tests"]["allocations"], results):
            span_sum = sum(e - s for s, e in record.spans)
            assert span_sum == tc["work_units"], (
                f"{tc['operation_id']}: expected {tc['work_units']} "
                f"work_units, got {span_sum}"
            )
