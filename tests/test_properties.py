"""Hypothesis property-based tests (T066).

Properties that must hold for all valid inputs, verified by random generation.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from conftest import EPOCH, make_bitmap, make_calendar


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Working minutes within a single working day: 1 to 540
_work_minutes = st.integers(min_value=1, max_value=540)

# Start times on working days (Mon, Wed, Thu, Fri — skip Tue holiday in standard)
_working_day_offsets = st.sampled_from([
    480,   # Mon 08:00
    540,   # Mon 09:00
    600,   # Mon 10:00
    2880 + 480,  # Wed 08:00
    2880 + 540,  # Wed 09:00
    2 * 1440 + 480,  # Wed 08:00 (alt calc)
])

# Datetimes during working hours on Mon
_mon_working_dt = st.builds(
    lambda m: EPOCH + timedelta(minutes=480 + m),
    st.integers(min_value=0, max_value=539),
)


# ---------------------------------------------------------------------------
# Property: add_minutes / subtract_minutes round-trip
# ---------------------------------------------------------------------------
class TestCalendarRoundTrip:
    """add_minutes(subtract_minutes(dt, n), n) == dt for working datetimes."""

    @given(minutes=_work_minutes)
    @settings(max_examples=50)
    def test_add_subtract_inverse(self, minutes):
        """Forward walk then backward walk returns to start."""
        cal = make_calendar("standard")
        start = EPOCH + timedelta(minutes=480)  # Mon 08:00

        forward = cal.add_minutes(start, minutes)
        back = cal.subtract_minutes(forward, minutes)
        assert back == start

    @given(dt=_mon_working_dt, minutes=st.integers(min_value=1, max_value=120))
    @settings(max_examples=50)
    def test_add_subtract_from_random_start(self, dt, minutes):
        """Round-trip from arbitrary working time on Monday."""
        cal = make_calendar("standard")
        forward = cal.add_minutes(dt, minutes)
        back = cal.subtract_minutes(forward, minutes)
        assert back == dt


# ---------------------------------------------------------------------------
# Property: to_int / to_datetime round-trip
# ---------------------------------------------------------------------------
class TestResolutionRoundTrip:

    @given(offset=st.integers(min_value=0, max_value=10079))
    @settings(max_examples=50)
    def test_minute_round_trip(self, offset):
        """to_datetime(to_int(dt)) == dt for any valid offset."""
        from scheduling_primitives.resolution import MINUTE

        dt = MINUTE.to_datetime(offset, EPOCH)
        assert MINUTE.to_int(dt, EPOCH) == offset

    @given(offset=st.integers(min_value=0, max_value=167))
    @settings(max_examples=50)
    def test_hour_round_trip(self, offset):
        """to_datetime(to_int(dt)) == dt at hour resolution."""
        from scheduling_primitives.resolution import HOUR

        dt = HOUR.to_datetime(offset, EPOCH)
        assert HOUR.to_int(dt, EPOCH) == offset


# ---------------------------------------------------------------------------
# Property: allocate / deallocate inverse
# ---------------------------------------------------------------------------
class TestAllocateDeallocateInverse:

    @given(work_units=st.integers(min_value=1, max_value=540))
    @settings(max_examples=20)
    def test_deallocate_restores_bits(self, work_units):
        """Allocate then deallocate restores bitmap to original state."""
        from scheduling_primitives.occupancy import allocate, deallocate

        bm = make_bitmap("standard")
        bits_before = bytes(bm.bits)

        record = allocate(bm, "OP-PROP", earliest_start=480, work_units=work_units)
        assert bytes(bm.bits) != bits_before, "allocate should change bits"

        deallocate(bm, record)
        assert bytes(bm.bits) == bits_before, "deallocate should restore bits"


# ---------------------------------------------------------------------------
# Property: span sum == work_units
# ---------------------------------------------------------------------------
class TestSpanSumInvariant:

    @given(work_units=st.integers(min_value=1, max_value=540))
    @settings(max_examples=30)
    def test_non_splittable_span_sum(self, work_units):
        """Single span's length equals work_units."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap("standard")
        record = walk(bm, "OP-PROP", earliest_start=480, work_units=work_units)
        span_sum = sum(end - begin for begin, end in record.spans)
        assert span_sum == work_units
        assert len(record.spans) == 1

    @given(work_units=st.integers(min_value=1, max_value=1080))
    @settings(max_examples=30)
    def test_splittable_span_sum(self, work_units):
        """Sum of all spans equals work_units for splittable walk."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap("standard")
        record = walk(
            bm, "OP-PROP", earliest_start=480,
            work_units=work_units, allow_split=True,
        )
        span_sum = sum(end - begin for begin, end in record.spans)
        assert span_sum == work_units


# ---------------------------------------------------------------------------
# Property: walk monotonicity
# ---------------------------------------------------------------------------
class TestWalkMonotonicity:

    @given(
        wu1=st.integers(min_value=1, max_value=270),
        wu2=st.integers(min_value=1, max_value=270),
    )
    @settings(max_examples=30)
    def test_larger_job_finishes_later(self, wu1, wu2):
        """A larger job starting at the same time finishes no earlier."""
        from scheduling_primitives.occupancy import walk

        bm = make_bitmap("standard")
        r1 = walk(bm, "OP-1", earliest_start=480, work_units=wu1)
        r2 = walk(bm, "OP-2", earliest_start=480, work_units=wu2)

        if wu1 <= wu2:
            assert r1.finish <= r2.finish
        else:
            assert r1.finish >= r2.finish
