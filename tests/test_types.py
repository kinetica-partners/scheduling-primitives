"""Tests for AllocationRecord and InfeasibleError (T005).

Test data loaded from: data/fixtures/scenarios/types.json
"""

from __future__ import annotations

import pytest

from conftest import load_scenarios

_data = load_scenarios("types")
RECORDS = _data["records"]
ERRORS = _data["errors"]


def _build_record(spec: dict):
    """Build an AllocationRecord from a scenario spec dict."""
    from scheduling_primitives.types import AllocationRecord

    return AllocationRecord(
        operation_id=spec["operation_id"],
        resource_id=spec["resource_id"],
        start=spec["start"],
        finish=spec["finish"],
        work_units=spec["work_units"],
        allow_split=spec["allow_split"],
        spans=tuple(tuple(s) for s in spec["spans"]),
    )


# ---------------------------------------------------------------------------
# AllocationRecord
# ---------------------------------------------------------------------------
class TestAllocationRecord:
    """AllocationRecord invariants and behaviour."""

    @pytest.mark.parametrize("spec", RECORDS, ids=lambda s: s["id"])
    def test_span_sum_equals_work_units(self, spec):
        """Sum of span lengths must equal work_units."""
        record = _build_record(spec)
        span_sum = sum(end - begin for begin, end in record.spans)
        assert span_sum == spec["expected_span_sum"]
        assert span_sum == record.work_units

    @pytest.mark.parametrize("spec", RECORDS, ids=lambda s: s["id"])
    def test_wall_time(self, spec):
        """wall_time = finish - start (includes non-working gaps)."""
        record = _build_record(spec)
        assert record.wall_time == spec["expected_wall_time"]

    @pytest.mark.parametrize(
        "spec",
        [r for r in RECORDS if "is_complete_at" in r],
        ids=lambda s: s["id"],
    )
    def test_is_complete(self, spec):
        """is_complete returns True/False based on required work_units."""
        record = _build_record(spec)
        for threshold in spec["is_complete_at"]:
            assert record.is_complete(threshold) is True, (
                f"expected complete at {threshold}"
            )
        for threshold in spec["is_incomplete_at"]:
            assert record.is_complete(threshold) is False, (
                f"expected incomplete at {threshold}"
            )

    def test_frozen_dataclass(self):
        """AllocationRecord is immutable (frozen dataclass)."""
        record = _build_record(RECORDS[0])
        with pytest.raises(AttributeError):
            record.start = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# InfeasibleError
# ---------------------------------------------------------------------------
class TestInfeasibleError:
    """InfeasibleError construction and attributes."""

    @pytest.mark.parametrize("spec", ERRORS, ids=lambda s: s["id"])
    def test_error_attributes(self, spec):
        """InfeasibleError stores all fields correctly."""
        from scheduling_primitives.types import InfeasibleError

        err = InfeasibleError(
            operation_id=spec["operation_id"],
            work_units_remaining=spec["work_units_remaining"],
            work_units_requested=spec["work_units_requested"],
            reason=spec["reason"],
        )
        assert err.operation_id == spec["operation_id"]
        assert err.work_units_remaining == spec["work_units_remaining"]
        assert err.work_units_requested == spec["work_units_requested"]
        assert err.reason == spec["reason"]

    def test_is_exception(self):
        """InfeasibleError is a proper Exception subclass."""
        from scheduling_primitives.types import InfeasibleError

        spec = ERRORS[0]
        err = InfeasibleError(
            operation_id=spec["operation_id"],
            work_units_remaining=spec["work_units_remaining"],
            work_units_requested=spec["work_units_requested"],
            reason=spec["reason"],
        )
        assert isinstance(err, Exception)
        assert spec["operation_id"] in str(err)

    def test_raise_and_catch(self):
        """Can be raised and caught."""
        from scheduling_primitives.types import InfeasibleError

        spec = ERRORS[0]
        with pytest.raises(InfeasibleError) as exc_info:
            raise InfeasibleError(
                operation_id=spec["operation_id"],
                work_units_remaining=spec["work_units_remaining"],
                work_units_requested=spec["work_units_requested"],
                reason=spec["reason"],
            )
        assert exc_info.value.operation_id == spec["operation_id"]
