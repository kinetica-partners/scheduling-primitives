"""Layer 2: OccupancyBitmap — integer-based capacity tracking.

Provides walk (read-only slot finding), allocate (commit), deallocate (release),
and auto-extending bitmap that grows on demand from the calendar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from scheduling_primitives.types import AllocationRecord, InfeasibleError

if TYPE_CHECKING:
    from scheduling_primitives.calendar import WorkingCalendar
    from scheduling_primitives.resolution import TimeResolution


# Default extension: 7 days worth of minutes
_DEFAULT_EXTEND_DAYS = 7


@dataclass
class OccupancyBitmap:
    """Mutable capacity state for one resource. Auto-extends on demand.

    bits[i] = 1 → free (available working time)
    bits[i] = 0 → occupied or non-working
    """

    resource_id: str
    horizon_begin: int
    bits: bytearray
    _calendar: WorkingCalendar
    _resolution: TimeResolution
    _epoch: datetime
    _allocations: list[AllocationRecord] = field(default_factory=list)

    @property
    def horizon_end(self) -> int:
        """One past the last bit index."""
        return self.horizon_begin + len(self.bits)

    @classmethod
    def from_calendar(
        cls,
        cal: WorkingCalendar,
        horizon_start: datetime,
        horizon_end: datetime,
        epoch: datetime,
        resolution: TimeResolution | None = None,
    ) -> OccupancyBitmap:
        """Materialise calendar into capacity state. The datetime boundary.

        FR-010: Materialise a working calendar into a capacity representation.
        """
        if resolution is None:
            from scheduling_primitives.resolution import MINUTE
            resolution = MINUTE

        begin_int = resolution.to_int(horizon_start, epoch)
        end_int = resolution.to_int(horizon_end, epoch)
        size = end_int - begin_int

        bits = bytearray(size)  # All zeros (non-working/occupied)

        # Fill in working periods from calendar
        _fill_bits_from_calendar(bits, begin_int, cal, resolution, epoch)

        return cls(
            resource_id=cal.pattern_id,
            horizon_begin=begin_int,
            bits=bits,
            _calendar=cal,
            _resolution=resolution,
            _epoch=epoch,
        )

    def _extend_to(self, needed_end: int) -> None:
        """Auto-extend bitmap to cover at least `needed_end`.

        Materialises additional calendar time in chunks.
        """
        if needed_end <= self.horizon_end:
            return

        # Extend in chunks of at least 7 days
        min_extend = _DEFAULT_EXTEND_DAYS * 24 * 60 * 60 // self._resolution.unit_seconds
        new_end = max(needed_end, self.horizon_end + min_extend)

        old_end = self.horizon_end
        extend_size = new_end - old_end
        new_bits = bytearray(extend_size)

        # Fill the new region from calendar
        _fill_bits_from_calendar(
            new_bits, old_end, self._calendar, self._resolution, self._epoch
        )

        self.bits.extend(new_bits)

    def copy(self) -> OccupancyBitmap:
        """Deep copy for branching."""
        return OccupancyBitmap(
            resource_id=self.resource_id,
            horizon_begin=self.horizon_begin,
            bits=bytearray(self.bits),
            _calendar=self._calendar,
            _resolution=self._resolution,
            _epoch=self._epoch,
            _allocations=list(self._allocations),
        )

    def checkpoint(self) -> bytes:
        """Immutable snapshot for backtracking."""
        import pickle
        return pickle.dumps((bytes(self.bits), list(self._allocations)))

    def restore(self, snap: bytes) -> None:
        """Restore to snapshot. Mutates in place."""
        import pickle
        bits_data, allocations = pickle.loads(snap)
        self.bits[:] = bits_data
        # If snapshot was from a shorter bitmap, truncate
        if len(bits_data) < len(self.bits):
            del self.bits[len(bits_data):]
        self._allocations = allocations


def _fill_bits_from_calendar(
    bits: bytearray,
    bits_offset: int,
    cal: WorkingCalendar,
    resolution: TimeResolution,
    epoch: datetime,
) -> None:
    """Fill a bytearray with 1s for working periods from the calendar."""
    # Convert bit range to datetime range
    dt_start = resolution.to_datetime(bits_offset, epoch)
    dt_end = resolution.to_datetime(bits_offset + len(bits), epoch)

    for iv_start, iv_end in cal.working_intervals_in_range(dt_start, dt_end):
        start_int = resolution.to_int(iv_start, epoch) - bits_offset
        end_int = resolution.to_int(iv_end, epoch) - bits_offset
        for i in range(max(0, start_int), min(len(bits), end_int)):
            bits[i] = 1


def walk(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,
    deadline: int | None = None,
) -> AllocationRecord:
    """Read-only: find earliest slot. Does NOT mutate bitmap.

    FR-022: Walk is read-only.
    FR-011: Find earliest position where work fits.
    FR-012/013/014: Non-splittable vs splittable with min_split.
    FR-017: Deadline support.
    """
    if allow_split:
        return _walk_splittable(
            bitmap, operation_id, earliest_start, work_units, min_split, deadline
        )
    else:
        return _walk_non_splittable(
            bitmap, operation_id, earliest_start, work_units, deadline
        )


def _walk_non_splittable(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    deadline: int | None,
) -> AllocationRecord:
    """Find earliest contiguous free run >= work_units."""
    pos = max(earliest_start, bitmap.horizon_begin)
    effective_deadline = deadline

    while True:
        # Auto-extend if needed
        if pos + work_units > bitmap.horizon_end:
            if effective_deadline is not None and pos >= effective_deadline:
                raise InfeasibleError(
                    operation_id=operation_id,
                    work_units_remaining=work_units,
                    work_units_requested=work_units,
                    reason="deadline",
                )
            bitmap._extend_to(pos + work_units + 1440)  # Extend with buffer

        # Scan for contiguous free run
        run_start = None
        run_length = 0

        scan_end = min(
            bitmap.horizon_end,
            effective_deadline if effective_deadline is not None else bitmap.horizon_end,
        )

        i = pos - bitmap.horizon_begin
        while i < scan_end - bitmap.horizon_begin:
            abs_pos = i + bitmap.horizon_begin

            if bitmap.bits[i] == 1:
                if run_start is None:
                    run_start = abs_pos
                    run_length = 1
                else:
                    run_length += 1

                if run_length >= work_units:
                    return AllocationRecord(
                        operation_id=operation_id,
                        resource_id=bitmap.resource_id,
                        start=run_start,
                        finish=run_start + work_units,
                        work_units=work_units,
                        allow_split=False,
                        spans=((run_start, run_start + work_units),),
                    )
            else:
                run_start = None
                run_length = 0

            i += 1

        # If we scanned up to deadline and didn't find a fit
        if effective_deadline is not None and scan_end >= effective_deadline:
            raise InfeasibleError(
                operation_id=operation_id,
                work_units_remaining=work_units,
                work_units_requested=work_units,
                reason="deadline",
            )

        # Need to extend further
        if pos + work_units > bitmap.horizon_end:
            bitmap._extend_to(bitmap.horizon_end + _DEFAULT_EXTEND_DAYS * 1440)
        pos = scan_end


def _walk_splittable(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    min_split: int,
    deadline: int | None,
) -> AllocationRecord:
    """Greedy consumption across gaps, respecting min_split threshold."""
    remaining = work_units
    spans: list[tuple[int, int]] = []
    pos = max(earliest_start, bitmap.horizon_begin)
    first_start: int | None = None

    while remaining > 0:
        # Auto-extend if needed
        if pos >= bitmap.horizon_end:
            if deadline is not None and pos >= deadline:
                raise InfeasibleError(
                    operation_id=operation_id,
                    work_units_remaining=remaining,
                    work_units_requested=work_units,
                    reason="deadline",
                )
            bitmap._extend_to(pos + _DEFAULT_EXTEND_DAYS * 1440)

        effective_end = min(
            bitmap.horizon_end,
            deadline if deadline is not None else bitmap.horizon_end,
        )

        # Find next free run
        i = pos - bitmap.horizon_begin
        while i < effective_end - bitmap.horizon_begin:
            if bitmap.bits[i] == 1:
                # Found start of free run
                run_start = i + bitmap.horizon_begin
                run_end = run_start
                while (
                    run_end - bitmap.horizon_begin < effective_end - bitmap.horizon_begin
                    and bitmap.bits[run_end - bitmap.horizon_begin] == 1
                ):
                    run_end += 1

                run_length = run_end - run_start

                # Check min_split threshold
                if run_length < min_split:
                    i = run_end - bitmap.horizon_begin
                    continue

                # Consume what we need
                consume = min(run_length, remaining)
                spans.append((run_start, run_start + consume))
                if first_start is None:
                    first_start = run_start
                remaining -= consume
                i = run_end - bitmap.horizon_begin

                if remaining <= 0:
                    break
            else:
                i += 1

        if remaining > 0:
            if deadline is not None and effective_end >= deadline:
                raise InfeasibleError(
                    operation_id=operation_id,
                    work_units_remaining=remaining,
                    work_units_requested=work_units,
                    reason="deadline",
                )
            # Extend and continue
            pos = effective_end
            if pos >= bitmap.horizon_end:
                bitmap._extend_to(pos + _DEFAULT_EXTEND_DAYS * 1440)

    last_end = spans[-1][1]
    return AllocationRecord(
        operation_id=operation_id,
        resource_id=bitmap.resource_id,
        start=first_start,  # type: ignore[arg-type]
        finish=last_end,
        work_units=work_units,
        allow_split=True,
        spans=tuple(spans),
    )


def _mark_spans(
    bitmap: OccupancyBitmap,
    spans: tuple[tuple[int, int], ...],
    value: int,
) -> None:
    """Set bits for all spans to the given value (0=occupied, 1=free)."""
    for begin, end in spans:
        offset = begin - bitmap.horizon_begin
        for i in range(offset, offset + (end - begin)):
            bitmap.bits[i] = value


def allocate(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,
    deadline: int | None = None,
) -> AllocationRecord:
    """Walk + commit. Returns allocation record. Raises InfeasibleError.

    FR-015: Commit an allocation.
    """
    record = walk(
        bitmap, operation_id, earliest_start, work_units,
        allow_split, min_split, deadline,
    )
    _mark_spans(bitmap, record.spans, 0)
    bitmap._allocations.append(record)
    return record


def apply_dynamic_exception(
    bitmap: OccupancyBitmap,
    start_offset: int,
    end_offset: int,
    is_working: bool,
) -> list[AllocationRecord]:
    """Apply a dynamic exception to a materialised bitmap.

    FR-009: Dynamic exceptions modify capacity mid-run.

    is_working=False — capacity removal (breakdown, closure).
        Sets bits to 0 and returns any allocations whose spans overlap
        the affected range (conflict detection).

    is_working=True — capacity addition (overtime, extra shift).
        Sets bits to 1. Returns empty list (no conflicts possible).
    """
    offset_begin = start_offset - bitmap.horizon_begin
    offset_end = end_offset - bitmap.horizon_begin

    if is_working:
        for i in range(max(0, offset_begin), min(len(bitmap.bits), offset_end)):
            bitmap.bits[i] = 1
        return []

    # Capacity removal: detect conflicts first, then set bits
    conflicts: list[AllocationRecord] = []
    for record in bitmap._allocations:
        for span_start, span_end in record.spans:
            if span_start < end_offset and start_offset < span_end:
                conflicts.append(record)
                break

    for i in range(max(0, offset_begin), min(len(bitmap.bits), offset_end)):
        bitmap.bits[i] = 0

    return conflicts


def deallocate(bitmap: OccupancyBitmap, record: AllocationRecord) -> None:
    """Release allocation. Exact inverse of allocate — restores bits to free.

    FR-016: Release must be exact inverse.
    """
    _mark_spans(bitmap, record.spans, 1)
    bitmap._allocations = [a for a in bitmap._allocations if a is not record]
