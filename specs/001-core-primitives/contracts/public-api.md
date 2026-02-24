# Public API Contract: scheduling-primitives

**Date**: 2026-02-24
**Package**: `scheduling_primitives`

This defines the public interface — what callers can depend on. Internal implementation details (bytearray layout, walk algorithm, extension strategy) are not part of this contract.

## Layer 1: Calendar Time Arithmetic

```python
class WorkingCalendar:
    """Horizon-free calendar. Answers time queries by lazy day-by-day walk."""

    def __init__(self, pattern_id: str, rules: dict, exceptions: dict): ...

    def add_minutes(self, start: datetime, minutes: int) -> datetime:
        """Forward walk: start + minutes of working time → finish datetime."""

    def subtract_minutes(self, end: datetime, minutes: int) -> datetime:
        """Backward walk: end - minutes of working time → start datetime."""

    def working_minutes_between(self, start: datetime, end: datetime) -> int:
        """Count working minutes in [start, end)."""

    def working_intervals_in_range(
        self, start: datetime, end: datetime
    ) -> Iterator[tuple[datetime, datetime]]:
        """Yield (interval_start, interval_end) for working periods in [start, end)."""
```

## Boundary: Time Resolution

```python
@dataclass(frozen=True)
class TimeResolution:
    """Converts between datetime and integer time. Immutable."""
    unit_seconds: int
    label: str

    def to_int(self, dt: datetime, epoch: datetime) -> int:
        """datetime → integer units from epoch. Raises ValueError on misalignment."""

    def to_datetime(self, t: int, epoch: datetime) -> datetime:
        """Integer units from epoch → datetime."""

MINUTE: TimeResolution  # unit_seconds=60
HOUR: TimeResolution    # unit_seconds=3600
```

## Layer 2: Capacity Tracking

```python
@dataclass
class OccupancyBitmap:
    """Mutable capacity state for one resource. Auto-extends on demand."""
    resource_id: str
    horizon_begin: int

    @property
    def horizon_end(self) -> int: ...

    @classmethod
    def from_calendar(
        cls,
        cal: WorkingCalendar,
        horizon_start: datetime,
        horizon_end: datetime,
        epoch: datetime,
        resolution: TimeResolution = MINUTE,
    ) -> OccupancyBitmap:
        """Materialise calendar into capacity state. The datetime boundary."""

    def copy(self) -> OccupancyBitmap:
        """Deep copy for branching."""

    def checkpoint(self) -> bytes:
        """Immutable snapshot for backtracking."""

    def restore(self, snap: bytes) -> None:
        """Restore to snapshot. Mutates in place."""


def walk(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,
    deadline: int | None = None,
) -> AllocationRecord:
    """Read-only: find earliest slot. Does NOT mutate bitmap."""


def allocate(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,
    deadline: int | None = None,
) -> AllocationRecord:
    """Walk + commit. Returns allocation record. Raises InfeasibleError."""


def deallocate(bitmap: OccupancyBitmap, record: AllocationRecord) -> None:
    """Release allocation. Exact inverse of allocate — restores bits to free."""


def apply_dynamic_exception(
    bitmap: OccupancyBitmap,
    begin: int,
    end: int,
    is_working: bool,
) -> list[AllocationRecord]:
    """
    Apply a dynamic exception mid-run.
    is_working=False: remove capacity (breakdown). Returns affected allocations.
    is_working=True: add capacity (overtime). Returns empty list.
    """
```

## Records and Errors

```python
@dataclass(frozen=True)
class AllocationRecord:
    """Immutable record of a committed or candidate allocation."""
    operation_id: str
    resource_id: str
    start: int
    finish: int
    work_units: int
    allow_split: bool
    spans: tuple[tuple[int, int], ...]

    @property
    def wall_time(self) -> int: ...

    def is_complete(self, required_work_units: int) -> bool: ...


class InfeasibleError(Exception):
    """Raised when work cannot be scheduled before deadline or horizon end."""
    operation_id: str
    work_units_remaining: int
    work_units_requested: int
    reason: str  # "deadline" or "horizon"
```

## Reference Scheduler

```python
def greedy_schedule(
    calendars: dict[str, WorkingCalendar],
    operations: list[dict],
    epoch: datetime,
    horizon_start: datetime,
    horizon_end: datetime,
    resolution: TimeResolution = MINUTE,
) -> list[AllocationRecord]:
    """
    Simple greedy scheduler demonstrating correct use of the primitives.
    Schedules operations in order, each to the earliest available slot.
    Reference implementation — not production.
    """
```

## Visual Verification (dev-only)

```python
# In scheduling_primitives/debug.py — never imported by production code

def show_calendar(cal: WorkingCalendar, start: datetime, end: datetime) -> None:
    """Print ASCII calendar view to stdout."""

def show_bitmap(bitmap: OccupancyBitmap, resolution: TimeResolution, epoch: datetime) -> None:
    """Print ASCII bitmap view with allocations to stdout."""

def show_multi_resource(bitmaps: list[OccupancyBitmap], ...) -> None:
    """Print ASCII multi-resource view to stdout."""
```

## Contract Guarantees

1. **Round-trip consistency**: `add_minutes(subtract_minutes(dt, n), n) == dt`
2. **Allocate/deallocate inverse**: bitmap state after deallocate is bit-identical to state before allocate
3. **Cross-layer consistency**: `resolution.to_datetime(record.finish, epoch) == calendar.add_minutes(start, work_units)` for matched inputs
4. **Span sum**: `sum(end - begin for begin, end in record.spans) == record.work_units`
5. **No mixed resolution**: all operations on a bitmap use the resolution it was materialised with
6. **Walk is read-only**: calling `walk()` does not change bitmap state
