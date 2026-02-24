"""Tests for TimeResolution (T006) and multi-resolution scaling (T048-T049).

Test data loaded from: data/fixtures/scenarios/resolution.json
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from conftest import EPOCH, load_scenarios, make_bitmap

_data = load_scenarios("resolution")
CONVERSIONS = _data["conversions"]
REJECTIONS = _data["rejections"]
PREDEFINED = _data["predefined"]
MULTI_RES = _data["multi_resolution"]


def _get_resolution(name: str):
    """Return the predefined TimeResolution by name."""
    from scheduling_primitives.resolution import HOUR, MINUTE
    return {"minute": MINUTE, "hour": HOUR}[name]


class TestTimeResolution:
    """TimeResolution conversion and predefined instances."""

    @pytest.mark.parametrize(
        "spec",
        [c for c in CONVERSIONS if "expected_int" in c],
        ids=lambda s: s["id"],
    )
    def test_to_int(self, spec):
        """Convert datetime to integer units from epoch."""
        res = _get_resolution(spec["resolution"])
        dt = datetime.fromisoformat(spec["datetime"])
        epoch = datetime.fromisoformat(spec["epoch"])
        assert res.to_int(dt, epoch) == spec["expected_int"]

    @pytest.mark.parametrize(
        "spec",
        [c for c in CONVERSIONS if "expected_datetime" in c],
        ids=lambda s: s["id"],
    )
    def test_to_datetime(self, spec):
        """Convert integer units back to datetime."""
        res = _get_resolution(spec["resolution"])
        epoch = datetime.fromisoformat(spec["epoch"])
        expected = datetime.fromisoformat(spec["expected_datetime"])
        assert res.to_datetime(spec["int_value"], epoch) == expected

    @pytest.mark.parametrize(
        "spec",
        [c for c in CONVERSIONS if c["id"].startswith("round_trip")],
        ids=lambda s: s["id"],
    )
    def test_round_trip(self, spec):
        """to_int then to_datetime is identity."""
        res = _get_resolution(spec["resolution"])
        dt = datetime.fromisoformat(spec["datetime"])
        epoch = datetime.fromisoformat(spec["epoch"])
        t = res.to_int(dt, epoch)
        assert res.to_datetime(t, epoch) == dt

    @pytest.mark.parametrize(
        "spec",
        [r for r in REJECTIONS if "align" in r.get("match", "")],
        ids=lambda s: s["id"],
    )
    def test_alignment_rejection(self, spec):
        """Non-aligned datetime raises ValueError."""
        res = _get_resolution(spec["resolution"])
        dt = datetime.fromisoformat(spec["datetime"])
        epoch = datetime.fromisoformat(spec["epoch"])
        with pytest.raises(ValueError, match="align"):
            res.to_int(dt, epoch)

    def test_aware_datetime_rejected(self):
        """Timezone-aware datetimes must be rejected (FR-035)."""
        spec = next(r for r in REJECTIONS if r["id"] == "aware_datetime")
        res = _get_resolution(spec["resolution"])
        epoch = datetime.fromisoformat(spec["epoch"])
        aware_dt = datetime.fromisoformat(spec["datetime"]).replace(
            tzinfo=timezone.utc
        )
        with pytest.raises((TypeError, ValueError)):
            res.to_int(aware_dt, epoch)

    def test_aware_epoch_rejected(self):
        """Timezone-aware epoch must be rejected."""
        spec = next(r for r in REJECTIONS if r["id"] == "aware_epoch")
        res = _get_resolution(spec["resolution"])
        dt = datetime.fromisoformat(spec["datetime"])
        aware_epoch = datetime.fromisoformat(spec["epoch"]).replace(
            tzinfo=timezone.utc
        )
        with pytest.raises((TypeError, ValueError)):
            res.to_int(dt, aware_epoch)

    @pytest.mark.parametrize("spec", PREDEFINED, ids=lambda s: s["id"])
    def test_predefined(self, spec):
        """Predefined resolution has correct unit_seconds and label."""
        res = _get_resolution(spec["id"])
        assert res.unit_seconds == spec["unit_seconds"]
        assert res.label == spec["label"]

    def test_frozen(self):
        """TimeResolution is immutable."""
        from scheduling_primitives.resolution import MINUTE

        with pytest.raises(AttributeError):
            MINUTE.unit_seconds = 120  # type: ignore[misc]


class TestMultiResolution:
    """T048: Verify bitmap behaviour at minute vs hour resolution."""

    def test_bitmap_size_ratio(self):
        """Minute-grain bitmap is 60x larger than hour-grain."""
        spec = next(s for s in MULTI_RES if s["id"] == "bitmap_size_ratio")
        bm_min = make_bitmap(spec["calendar"])
        bm_hr = make_bitmap(spec["calendar"], resolution="hour")

        assert len(bm_min.bits) == spec["minute_bits"]
        assert len(bm_hr.bits) == spec["hour_bits"]
        assert len(bm_min.bits) // len(bm_hr.bits) == spec["ratio"]

    def test_free_count_ratio(self):
        """Working-bit count scales proportionally with resolution."""
        spec = next(s for s in MULTI_RES if s["id"] == "free_count_ratio")
        bm_min = make_bitmap(spec["calendar"])
        bm_hr = make_bitmap(spec["calendar"], resolution="hour")

        assert sum(bm_min.bits) == spec["minute_free"]
        assert sum(bm_hr.bits) == spec["hour_free"]

    def test_allocation_agreement(self):
        """Same job at both resolutions finishes at the same datetime."""
        from scheduling_primitives.occupancy import allocate
        from scheduling_primitives.resolution import HOUR, MINUTE

        spec = next(s for s in MULTI_RES if s["id"] == "allocation_agreement")
        bm_min = make_bitmap(spec["calendar"])
        bm_hr = make_bitmap(spec["calendar"], resolution="hour")

        rec_min = allocate(
            bm_min, spec["operation_id"],
            earliest_start=spec["earliest_start_minute"],
            work_units=spec["work_units_minute"],
        )
        rec_hr = allocate(
            bm_hr, spec["operation_id"],
            earliest_start=spec["earliest_start_hour"],
            work_units=spec["work_units_hour"],
        )

        finish_min = MINUTE.to_datetime(rec_min.finish, EPOCH)
        finish_hr = HOUR.to_datetime(rec_hr.finish, EPOCH)
        expected = datetime.fromisoformat(spec["expected_finish_datetime"])

        assert finish_min == expected, spec["notes"]
        assert finish_hr == expected, spec["notes"]
