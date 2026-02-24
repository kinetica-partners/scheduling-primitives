# scheduling-primitives — Design Specification v2

**Status**: Active  
**Replaces**: v1 (calendar query API only)  
**Added in v2**: unit parameter, allow_split, allocation layer (allocate/deallocate/checkpoint/restore), OccupancyBitmap, two-layer architecture, decision records

---

## 1. Overview

**scheduling-primitives** is an open source Python package providing the building blocks for finite capacity scheduling: working calendars, occupancy state, and time arithmetic.

The package is a cross-platform reference implementation. Parallel implementations in VBA and Power Query (for the Excel Computation Lab) share the same schema contract and test fixtures. All implementations validate against a single set of expected results.

### 1.1 Two-Layer Architecture

The package exposes two distinct layers with a clean seam between them.

**Layer 1 — WorkingCalendar (datetime-based, horizon-free)**

Answers questions about working time without knowing how that time will be used:

- **Forward:** Given a start datetime and a duration in working units, when does the job finish?
- **Backward:** Given an end datetime and a duration in working units, when must the job start?
- **Between:** How many working units exist between two datetimes?
- **Intervals:** What working periods exist within a datetime range?

**Layer 2 — OccupancyBitmap (integer-based, horizon-committed)**

Answers questions about available capacity given what has already been allocated:

- **Allocate:** Reserve working time for an operation, returning an immutable record of what was consumed.
- **Deallocate:** Release previously allocated time, restoring it to free.
- **Checkpoint:** Snapshot the current occupancy state for branch-and-bound backtracking.
- **Restore:** Return to a previous snapshot state.

The seam between layers is `OccupancyBitmap.from_calendar()`. After that call, datetime is sealed off. Everything in Layer 2 and above operates on integers.

### 1.2 What the Package Does Not Include

The package provides infrastructure — the building blocks every scheduling system needs. It explicitly excludes:

- Dispatching rules (which operation to schedule next)
- Resource selection logic (which machine to assign)
- Optimisation algorithms (B&B, metaheuristics)
- Simulation (Monte Carlo, discrete event)
- ERP integration

Those belong in the premium layer built on top of this foundation.

### 1.3 Package Identity

| Attribute | Value |
|---|---|
| PyPI name | `scheduling-primitives` |
| Import | `import scheduling_primitives` |
| Shorthand | `schedprim` |
| Licence | MIT |
| Python | ≥ 3.10 |
| Dependencies (v1) | None (stdlib only for core; pandas optional for data loading) |

### 1.4 Repository Structure

```
scheduling-primitives/
├── pyproject.toml
├── README.md
├── LICENSE
├── data/
│   ├── datapackage.json
│   └── examples/
│       ├── simple/
│       ├── multi_shift/
│       ├── overnight/
│       ├── resource_variety/
│       └── stress/
├── src/
│   └── scheduling_primitives/
│       ├── __init__.py
│       ├── calendar.py          ← WorkingCalendar (Layer 1)
│       ├── occupancy.py         ← OccupancyBitmap, AllocationRecord (Layer 2)
│       ├── resolution.py        ← TimeResolution (boundary conversion)
│       ├── schema.py            ← Pydantic models + validation
│       ├── loaders.py           ← CSV/DataFrame loading
│       └── excel.py             ← xlwings integration
├── tests/
│   ├── conftest.py
│   ├── test_time_utils.py
│   ├── test_period_operations.py
│   ├── test_day_resolution.py
│   ├── test_forward_walk.py
│   ├── test_backward_walk.py
│   ├── test_minutes_between.py
│   ├── test_intervals_in_range.py   ← new in v2
│   ├── test_occupancy_bitmap.py     ← new in v2
│   ├── test_allocate.py             ← new in v2
│   ├── test_deallocate.py           ← new in v2
│   ├── test_checkpoint_restore.py   ← new in v2
│   ├── test_continuity.py           ← new in v2
│   ├── test_edge_cases.py
│   ├── test_consistency.py
│   └── test_excel_interface.py
└── docs/
    ├── pq_schema_reader.m
    └── architecture-notes.md       ← platform portability, TypeScript context
```

### 1.5 Strategic Context

#### Open Source / Premium Boundary

| Layer | Contents | Licence |
|---|---|---|
| **scheduling-primitives** (open) | Calendars, occupancy, time arithmetic | MIT |
| **production-scheduling.com** (content) | Tutorials and methods using the primitives | Proprietary |
| **Excel Computation Lab** (mixed) | PQ/VBA/formula implementations, comparisons | Proprietary |
| **KINETICA / SoPlenty / Lorenz Effect** (premium) | Dispatching, optimisation, simulation, ERP | Proprietary |

The Python library served behind an API is the asset. Everything else — Office Scripts connectors, BC extensions, Power BI dataflows, Odoo modules — is a client of the scheduling primitives over HTTP. The TypeScript exploration confirmed the algorithms port cleanly to imperative platforms, but the implementation priority is Python first as reference implementation and production engine. Connectors follow demand; they are not built speculatively.

---

## 2. Decision Records

These are the foundational design decisions. They should not be revisited without explicit justification recorded here.

### DR-1: datetime core in WorkingCalendar is intentional

`WorkingCalendar` uses Python `datetime` objects internally. This is not a placeholder pending integer conversion — it is the correct design for a horizon-free lazy walk component.

The lazy walk iterates day-by-day on demand. It does not require a pre-specified planning horizon. A 10,000-minute job on a 30-minute-per-week sparse calendar spans 6.4 years; the lazy walk handles this by visiting only the days it needs, without allocating any upfront structure.

Integer conversion happens at the seam with `OccupancyBitmap`, not inside `WorkingCalendar`. Rebuilding `WorkingCalendar` to use integers would require a horizon at construction time, destroying the lazy walk and the ability to schedule arbitrarily long jobs without pre-specifying the planning window.

### DR-2: Integer time at Layer 2 and above

`OccupancyBitmap` and everything above it uses integers for all time values. The time unit is a parameter (default: one minute). Datetime appears only in the boundary conversion layer (`TimeResolution`) and never crosses into Layer 2.

**Rationale**: Discretisation error is bounded by one time unit. For any realistic scheduling input, this is smaller than the uncertainty in the input data — processing times, setup times, and transit times are estimates with natural granularity at or above the chosen unit. Integer arithmetic is exact, associative, and platform-independent. Float arithmetic accumulates error through scheduling chains and produces non-reproducible results across platforms, which is incompatible with the portability goals of this library.

**On the approximation**: The position is that it is explicit and chosen so that it is orders of magnitude smaller than the real-world error in the inputs. Deterministic optimisation will exhaust its computational budget before solution quality is limited by discretisation precision. A B&B search that cannot prove optimality at minute-grain will not benefit from second-grain. The discretisation error is noise below the optimality gap.

**When to revisit**: If a deployment context requires sub-minute timing and the input data genuinely supports that resolution, reduce `TimeResolution.unit_seconds` accordingly. The engine is unchanged.

### DR-3: Half-open intervals throughout

All intervals are `[begin, end)` — begin inclusive, end exclusive. This is consistent with Python's `range()`, `list[a:b]`, and `bisect` conventions. Length is always `end - begin` with no off-by-one correction. Adjacent intervals tile without overlap or gap.

### DR-4: unit parameter is a boundary concern, not an engine concern

The scheduling engine works in dimensionless integer units. The meaning of one unit (one minute, one hour, one five-minute block) is set once at the boundary via `TimeResolution` and never referenced inside the engine. This means resolution can be changed without touching any algorithm code.

### DR-5: allow_split is a job property, not a calendar property

Whether an operation can be split across non-contiguous working windows is a property of the operation, not of the calendar or resource. The walk algorithm respects this flag: non-splittable operations wait for a contiguous window long enough to fit; splittable operations consume whatever is available and continue in subsequent windows.

### DR-6: walk does not mutate — allocate commits

The `walk()` function is read-only. It finds an allocation but does not mark the bitmap. The caller decides whether to commit via `allocate()`. This separation allows inspection of a candidate allocation before branching in B&B without accidental state mutation.

### DR-7: Python first, connectors on demand

The Python implementation is the reference. TypeScript, VBA, and Power Query M implementations are connectors — they validate against the Python test fixtures and serve specific deployment contexts (Office Scripts, Excel Computation Lab). They are built when a concrete project requires them, not speculatively.

---

## 3. Schema Contract

*(Unchanged from v1 — reproduced here for completeness.)*

### 3.1 Design Principles

| Principle | Decision | Rationale |
|---|---|---|
| Case convention | snake_case throughout | Native to Python, clean in SQL/PQ |
| Dates | ISO 8601 YYYY-MM-DD | Locale-independent |
| Times | ISO 8601 HH:MM 24-hour | No AM/PM ambiguity |
| Day of week | ISO integer 1=Mon through 7=Sun | Language-neutral |
| Booleans | Integer 1/0 | Unambiguous across Excel, Python, SQL, VBA, PQ |
| Schema definition | Frictionless Data Package | Machine-readable, language-neutral |
| Domain validation | Pydantic models in Python | Business rule validation after loading |

### 3.2 Table: shift_rule

Recurring weekly template. Multiple rows per `(pattern_id, day_of_week)` define multi-period days. A day with no rows is non-working.

| Column | Type | Format | Constraints | Description |
|---|---|---|---|---|
| `pattern_id` | text | | required | Availability pattern identifier |
| `day_of_week` | integer | | required, 1–7 | ISO 8601 weekday |
| `start_time` | text | HH:MM | required | Period start, 24-hour |
| `end_time` | text | HH:MM | required | Period end. Earlier than start_time = overnight |

**Primary key**: `(pattern_id, day_of_week, start_time)`

### 3.3 Table: shift_exception

Date-specific overrides. `is_working=0` with empty times removes the entire day. `is_working=1` adds working time (overtime, weekend working).

| Column | Type | Format | Constraints | Description |
|---|---|---|---|---|
| `pattern_id` | text | | required | FK to shift_rule.pattern_id |
| `exception_date` | text | YYYY-MM-DD | required | The specific date |
| `is_working` | integer | | required, 0 or 1 | 1 = adds working time, 0 = removes |
| `start_time` | text | HH:MM | required if is_working=1 | |
| `end_time` | text | HH:MM | required if is_working=1 | |

**Primary key**: `(pattern_id, exception_date, is_working, start_time)`

### 3.4 Table: resource_calendar (outside the calendar engine)

Maps any resource to a pattern. Lives in the scheduling/dependency layer.

| Column | Type | Description |
|---|---|---|
| `resource_id` | text | Work centre, skill group, tool pool, etc. |
| `pattern_id` | text | FK to shift_rule.pattern_id |
| `effective_from` | text | When this assignment starts (nullable = always) |
| `effective_to` | text | When this assignment ends (nullable = ongoing) |

---

## 4. Layer 1 — WorkingCalendar API

### 4.1 Class

```python
class WorkingCalendar:
    """
    Encapsulates an availability pattern with rules and exceptions.
    Provides forward, backward, and counting queries over working time.
    
    Datetime-based internally. The lazy walk iterates day-by-day on demand
    with no pre-specified horizon. Cost is proportional to calendar days
    spanned — typically small for scheduling queries.
    
    Agnostic to what it represents: machine, operator, tool fitter, classroom.
    """

    def __init__(self, pattern_id: str, rules: dict, exceptions: dict):
        self.pattern_id = pattern_id
        self.weekly_pattern = rules.get(pattern_id, {})      # keyed by Python weekday 0-6
        self.exceptions = exceptions.get(pattern_id, {})     # keyed by date.isoformat()
        self.weekly_minutes = self._compute_weekly_minutes()
```

### 4.2 Public Methods

```python
def add_minutes(self, start: datetime, minutes: int) -> datetime:
    """Walk forward through working time from start."""

def subtract_minutes(self, end: datetime, minutes: int) -> datetime:
    """Walk backward through working time from end."""

def working_minutes_between(self, start: datetime, end: datetime) -> int:
    """Count working minutes between two datetimes."""

def working_intervals_in_range(
    self,
    start: datetime,
    end: datetime,
) -> Iterator[tuple[datetime, datetime]]:
    """
    Yield (interval_start, interval_end) pairs for all working periods
    within [start, end).
    
    This is the primitive that add_minutes is built on, exposed so that
    OccupancyBitmap.from_calendar() can consume it directly without going
    through the minute-counting interface.
    
    Added in v2. Required for Layer 2 integration.
    """
```

The `working_intervals_in_range` method is the only v2 addition to the Layer 1 API. All existing v1 method signatures are unchanged.

### 4.3 Forward Walk Algorithm

```
function add_minutes(start_dt, minutes_to_add):
    remaining = minutes_to_add
    current_date = start_dt.date()

    loop while remaining > 0:
        for each (period_start, period_end) in periods_for_date(current_date):
            interval_start = combine(current_date, period_start)
            interval_end   = combine(current_date, period_end)
            effective_start = max(start_dt, interval_start)
            if effective_start >= interval_end: continue
            available = (interval_end - effective_start) in minutes
            if remaining <= available:
                return effective_start + remaining minutes
            remaining -= available
        current_date += 1 day
```

### 4.4 Backward Walk Algorithm

```
function subtract_minutes(end_dt, minutes_to_subtract):
    remaining = minutes_to_subtract
    current_date = end_dt.date()

    loop while remaining > 0:
        for each (period_start, period_end) in reversed(periods_for_date(current_date)):
            interval_start = combine(current_date, period_start)
            interval_end   = combine(current_date, period_end)
            effective_end = min(end_dt, interval_end)
            if effective_end <= interval_start: continue
            available = (effective_end - interval_start) in minutes
            if remaining <= available:
                return effective_end - remaining minutes
            remaining -= available
        current_date -= 1 day
```

### 4.5 Day Period Resolution

```
function periods_for_date(d):
    date_str = d.isoformat()
    if date_str not in exceptions:
        return weekly_pattern.get(d.weekday(), [])
    if any full-day non-working exception exists:
        return only the working exceptions for this date (if any)
    base_periods = weekly_pattern.get(d.weekday(), [])
    subtract non-working exception windows from base_periods
    add non-overlapping working exception windows
    sort by start_time
    return result
```

ISO weekday mapping on load: `python_weekday = iso_day_of_week - 1`

---

## 5. Boundary Layer — TimeResolution

```python
@dataclass(frozen=True)
class TimeResolution:
    """
    The fundamental time unit of this scheduler instance.
    All integer times are multiples of this unit.
    
    Lives outside the scheduling engine. Handles all datetime ↔ int conversion.
    The engine never sees a datetime, date, or time object.
    """
    unit_seconds: int    # 60 = minute (default), 3600 = hour, 300 = 5-min block
    label: str           # "minute", "hour", "5min" — for display only

    def to_int(self, dt: datetime, epoch: datetime) -> int:
        """Convert a datetime to an integer unit count from epoch."""
        delta_seconds = int((dt - epoch).total_seconds())
        remainder = delta_seconds % self.unit_seconds
        if remainder != 0:
            raise ValueError(
                f"{dt} does not align to {self.label} boundary "
                f"(off by {remainder}s)"
            )
        return delta_seconds // self.unit_seconds

    def to_datetime(self, t: int, epoch: datetime) -> datetime:
        return epoch + timedelta(seconds=t * self.unit_seconds)

MINUTE = TimeResolution(unit_seconds=60, label="minute")
HOUR   = TimeResolution(unit_seconds=3600, label="hour")
```

The validation in `to_int` is deliberate and strict: if an input datetime does not align to the resolution boundary, it raises rather than silently rounding. The calling layer is responsible for ensuring inputs align before passing to the engine.

---

## 6. Layer 2 — OccupancyBitmap

### 6.1 Core Data Structure

```python
@dataclass
class OccupancyBitmap:
    """
    Mutable free/occupied state for one resource over a fixed planning horizon.
    
    bits[i] = 1  →  time unit (horizon_begin + i) is free
    bits[i] = 0  →  time unit (horizon_begin + i) is occupied or non-working
    
    Non-working time is pre-occupied at construction. The walk never touches it.
    The unit (minute, hour, etc.) is fixed at construction via TimeResolution
    and not stored here — the bitmap is agnostic to what a unit means.
    
    One week at minute grain: 10,080 bits ≈ 1.25 KB per resource.
    Twenty resources for one week: ~25 KB — fits in L1 cache.
    """
    resource_id: str
    horizon_begin: int     # integer units from epoch
    bits: bytearray

    @property
    def horizon_end(self) -> int:
        return self.horizon_begin + len(self.bits)

    @classmethod
    def from_calendar(
        cls,
        cal: WorkingCalendar,
        horizon_start: datetime,
        horizon_end: datetime,
        epoch: datetime,
        resolution: TimeResolution = MINUTE,
    ) -> OccupancyBitmap:
        """
        Materialise a WorkingCalendar into a bitmap for the given horizon.
        This is the seam between Layer 1 and Layer 2.
        Called once per resource per planning run — not in the hot path.
        After this call, datetime is sealed off.
        """
        begin_int = resolution.to_int(horizon_start, epoch)
        end_int   = resolution.to_int(horizon_end,   epoch)
        n = end_int - begin_int
        bits = bytearray(n)   # all zero = occupied initially

        for iv_start, iv_end in cal.working_intervals_in_range(horizon_start, horizon_end):
            lo = resolution.to_int(iv_start, epoch) - begin_int
            hi = resolution.to_int(iv_end,   epoch) - begin_int
            for i in range(lo, hi):
                bits[i] = 1   # mark working time as free

        return cls(resource_id=cal.pattern_id, horizon_begin=begin_int, bits=bits)

    def copy(self) -> OccupancyBitmap:
        """O(N) copy for B&B branching. ~1.25 KB per resource-week at minute grain."""
        return OccupancyBitmap(self.resource_id, self.horizon_begin, bytearray(self.bits))

    def checkpoint(self) -> bytes:
        """Immutable snapshot. Used for B&B checkpoint/restore and incumbent storage."""
        return bytes(self.bits)

    def restore(self, snap: bytes) -> None:
        """Restore to a previously checkpointed state. Mutates in place."""
        if len(snap) != len(self.bits):
            raise ValueError("Snapshot length mismatch")
        self.bits[:] = snap
```

### 6.2 AllocationRecord

```python
@dataclass(frozen=True)
class AllocationRecord:
    """
    Immutable record of a committed (or candidate) allocation.
    Self-contained: the bitmap can be restored from this record alone,
    without reference to the original calendar.
    """
    operation_id: str
    resource_id: str
    start: int            # first occupied unit (absolute, from epoch)
    finish: int           # one past last occupied unit
    work_units: int       # total working units consumed
    allow_split: bool     # whether this allocation is a split segment
    spans: tuple[tuple[int, int], ...]   # contiguous free runs consumed, (begin, end) pairs

    @property
    def wall_time(self) -> int:
        """finish - start: elapsed integer units including non-working gaps."""
        return self.finish - self.start

    def is_complete(self, required_work_units: int) -> bool:
        return self.work_units >= required_work_units
```

### 6.3 Walk Function

```python
def walk(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,      # integer units from epoch
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,       # minimum quantum for a split segment
    deadline: int | None = None,
) -> AllocationRecord:
    """
    Find the earliest completion of work_units of work starting no earlier
    than earliest_start, using free bits from the bitmap.
    
    Does NOT modify the bitmap. Returns a record describing what to consume.
    Mutation is the caller's responsibility (allocate/deallocate).
    
    If allow_split=False: waits for a contiguous free run of length >= work_units.
    If allow_split=True: consumes available free runs greedily across gaps.
    
    Raises InfeasibleError if work cannot be completed before deadline (or horizon end).
    """
    bits = bitmap.bits
    base = bitmap.horizon_begin
    pos = max(0, earliest_start - base)
    n = len(bits)
    limit = (deadline - base) if deadline is not None else n

    remaining = work_units
    spans = []
    first_start = None

    while pos < limit and remaining > 0:
        # Skip occupied time (non-working or already allocated)
        while pos < limit and bits[pos] == 0:
            pos += 1
        if pos >= limit:
            break

        # Measure contiguous free run
        run_start = pos
        while pos < limit and bits[pos] == 1:
            pos += 1
        run_end = pos
        run_len = run_end - run_start

        if not allow_split and run_len < remaining:
            # Non-splittable: run is too short. Skip and look for a longer run.
            continue

        if allow_split and run_len < min_split:
            # Splittable but below minimum quantum. Skip this run.
            continue

        apply = min(run_len, remaining)
        abs_start = run_start + base
        spans.append((abs_start, abs_start + apply))
        if first_start is None:
            first_start = abs_start
        remaining -= apply

    if remaining > 0:
        raise InfeasibleError(
            f"op={operation_id}: {remaining} of {work_units} work units "
            f"unschedulable before {'deadline' if deadline else 'horizon end'}"
        )

    last_end = spans[-1][1]
    return AllocationRecord(
        operation_id=operation_id,
        resource_id=bitmap.resource_id,
        start=first_start,
        finish=last_end,
        work_units=work_units,
        allow_split=allow_split,
        spans=tuple(spans),
    )
```

### 6.4 Allocate and Deallocate

```python
def allocate(
    bitmap: OccupancyBitmap,
    operation_id: str,
    earliest_start: int,
    work_units: int,
    allow_split: bool = False,
    min_split: int = 1,
    deadline: int | None = None,
) -> AllocationRecord:
    """
    Walk the bitmap and commit the result. Returns the AllocationRecord.
    Raises InfeasibleError if the operation cannot be scheduled.
    """
    record = walk(
        bitmap, operation_id, earliest_start, work_units,
        allow_split, min_split, deadline
    )
    _mark_spans(bitmap.bits, bitmap.horizon_begin, record.spans, value=0)
    return record


def deallocate(bitmap: OccupancyBitmap, record: AllocationRecord) -> None:
    """
    Reverse a previously committed allocation. Restores all spans to free.
    Exact inverse of allocate — no floating-point residual drift.
    """
    _mark_spans(bitmap.bits, bitmap.horizon_begin, record.spans, value=1)


def _mark_spans(
    bits: bytearray,
    base: int,
    spans: tuple[tuple[int, int], ...],
    value: int,
) -> None:
    for span_begin, span_end in spans:
        lo = span_begin - base
        hi = span_end   - base
        bits[lo:hi] = bytes([value]) * (hi - lo)
```

### 6.5 Splittable vs Non-Splittable

**Non-splittable** (`allow_split=False`): The operation must fit entirely within a single contiguous free run. If the current free run is too short, the walk skips forward looking for a longer one. The operation waits for the next shift window large enough to contain it.

*Use case*: Machining operations that cannot be interrupted mid-cut; batch processes requiring continuous resource occupancy.

**Splittable** (`allow_split=True`): The operation consumes whatever free time is available in each run, continues across gaps (shift ends, weekends), and accumulates work until complete. The `AllocationRecord.spans` contains multiple `(begin, end)` pairs.

*Use case*: Labour-intensive tasks that can be picked up and set down; operations that span shift boundaries by design.

**min_split**: For splittable operations, the minimum working time that must be available in a run for it to be worth starting. Prevents unrealistically small job fragments. Default is 1 unit (no constraint). Set to, for example, 30 for "must have at least 30 minutes available before starting a segment".

### 6.6 Checkpoint / Restore for Branch and Bound

```python
# Typical B&B pattern
snap = bitmap.checkpoint()     # O(N) copy, ~1.25 KB per resource-week at minute grain

try:
    record = allocate(bitmap, op_id, earliest_start, work_units, allow_split)
    # ... recurse into next B&B decision ...
    branch_and_bound(remaining_ops, bitmaps, depth + 1)
finally:
    bitmap.restore(snap)       # unconditionally undo — whether branch succeeded or not
```

Alternatively, `deallocate` can be used when the allocation record is available:

```python
record = allocate(bitmap, ...)
try:
    branch_and_bound(...)
finally:
    deallocate(bitmap, record)
```

Both are correct. `checkpoint/restore` is more general (handles multiple operations or partial state changes); `deallocate` is more explicit and self-documenting when undoing a single known allocation.

**Checkpoint cost**: `bytes(bytearray)` — O(N), approximately 1.25 KB per resource-week at minute grain. For 20 resources across a 4-week horizon this is 100 KB per checkpoint. In a B&B tree at depth 40, that is 4 MB of snapshot data — acceptable for in-memory search.

**For deeper trees or many resources**: pass the `AllocationRecord` and use `deallocate` rather than checkpointing the full bitmap. The record is O(k) where k is the number of spans (typically 1–5), not O(N).

---

## 7. Dynamic Capacity Modification

Frozen calendars are shared across all B&B branches without copying. Dynamic capacity changes — overtime authorisation, equipment breakdowns — are handled by producing new calendar variants before materialising a bitmap, not by mutating a live bitmap.

### 7.1 Breakdowns → Allocation Approach

A breakdown removes capacity that was previously available. Model it as an allocation with no productive work:

```python
# Mark the breakdown window as occupied before scheduling operations
breakdown_record = AllocationRecord(
    operation_id="__breakdown__",
    resource_id=resource_id,
    start=breakdown_start,
    finish=breakdown_end,
    work_units=0,
    allow_split=False,
    spans=((breakdown_start, breakdown_end),),
)
deallocate is never called on this — the window stays occupied for the planning run.
```

The walk algorithm naturally routes around it. Works for both planned maintenance and unplanned stoppages. Works inside B&B without special treatment.

### 7.2 Overtime → Calendar Variant Approach

Overtime adds capacity that did not exist in the base calendar. It cannot be represented as an allocation because there is no bitmap slot to occupy. Instead, produce a new bitmap with the overtime window included:

```python
def bitmap_with_overtime(
    base_bitmap: OccupancyBitmap,
    overtime_begin: int,
    overtime_end: int,
) -> OccupancyBitmap:
    """Return a new bitmap with an overtime window marked free."""
    new_bits = bytearray(base_bitmap.bits)
    lo = overtime_begin - base_bitmap.horizon_begin
    hi = overtime_end   - base_bitmap.horizon_begin
    for i in range(lo, hi):
        new_bits[i] = 1
    return OccupancyBitmap(base_bitmap.resource_id, base_bitmap.horizon_begin, new_bits)
```

In B&B, overtime decisions are branch points: one branch uses the base bitmap, another uses the overtime variant. The cost of the overtime (premium rate × hours) enters the objective function. B&B explores whether overtime is worth authorising.

### 7.3 Rolling Horizon and Policy Evaluation

For medium and long-range simulation where overtime is triggered by queue state rather than a fixed decision:

1. Schedule one period (day, week) using the base bitmap.
2. At the period boundary, evaluate the overtime policy against the current schedule state.
3. If overtime is authorised, produce a new bitmap for the next period with the overtime window.
4. Materialise from `WorkingCalendar` for the next period; the policy adds its extensions before materialisation.

This keeps both layers clean: `WorkingCalendar` handles shift patterns; the policy layer adds extensions as integer-unit windows before calling `from_calendar`.

---

## 8. Test Specification

### 8.1 Datasets

All test data uses the finalised schema (snake_case, ISO weekdays, integer booleans, HH:MM times). Five datasets as per v1: `simple`, `multi_shift`, `overnight`, `resource_variety`, `stress`. See v1 specification for full CSV content.

### 8.2 Layer 1 Tests (unchanged from v1)

All tests from v1 sections 7.1–7.8 are retained unchanged. The parametric consistency tests (7.8) are the most important: forward then backward must return to exact start; `working_minutes_between` must agree with `add_minutes`.

### 8.3 New: working_intervals_in_range

| # | Pattern | Start | End | Expected intervals |
|---|---|---|---|---|
| I1 | simple | Mon 09:00 | Mon 17:00 | [(09:00, 17:00)] |
| I2 | simple | Mon 09:00 | Wed 12:00 | [(Mon 09:00, 17:00), (Wed 09:00, 12:00)] — Tue is holiday |
| I3 | split_day | Mon 06:00 | Mon 18:00 | [(Mon 06:00, 10:00), (Mon 14:00, 18:00)] |
| I4 | simple | Mon 12:00 | Mon 14:00 | [(Mon 12:00, 14:00)] — within a single period |
| I5 | simple | Sat 00:00 | Sun 00:00 | [(Sat 10:00, 14:00)] — exception only |

### 8.4 New: OccupancyBitmap Construction

| # | Test | Expected |
|---|---|---|
| B1 | from_calendar, simple, Mon–Fri | bits=1 for 09:00–17:00 each day, bits=0 all other times |
| B2 | from_calendar, holiday Tue | all bits=0 for Tuesday |
| B3 | from_calendar, split_day | bits=1 for 06:00–10:00 and 14:00–18:00, bits=0 for 10:00–14:00 gap |
| B4 | horizon_end - horizon_begin | equals resolution units in planning horizon |
| B5 | total free bits | equals total_capacity from WorkingCalendar for same range |

### 8.5 New: Walk (non-splittable)

Using `simple` pattern, standard week, minute resolution:

| # | earliest_start | work_units | allow_split | Expected start | Expected finish |
|---|---|---|---|---|---|
| W1 | Mon 09:00 | 60 | False | Mon 09:00 | Mon 10:00 |
| W2 | Mon 09:00 | 480 | False | Mon 09:00 | Mon 17:00 |
| W3 | Mon 16:30 | 60 | False | Wed 09:00 | Wed 10:00 — 30min left Mon, must wait for full 60 |
| W4 | Mon 09:00 | 181 | False | Wed 09:00 | Wed 12:01 — Wed half-day only has 180 min, waits for Thu |
| W5 | Mon 09:00 | 480 deadline=Mon 17:00 | False | Mon 09:00 | Mon 17:00 |
| W6 | Mon 09:00 | 481 deadline=Mon 17:00 | False | raises InfeasibleError | |

### 8.6 New: Walk (splittable)

| # | earliest_start | work_units | allow_split | min_split | Expected spans |
|---|---|---|---|---|---|
| S1 | Mon 16:30 | 60 | True | 1 | [(Mon 16:30, 17:00), (Wed 09:00, 09:30)] |
| S2 | Mon 16:00 | 120 | True | 1 | [(Mon 16:00, 17:00), (Wed 09:00, 10:00)] |
| S3 | Mon 16:45 | 60 | True | 30 | [(Wed 09:00, 10:00)] — 15min Mon < min_split, skip to Wed |
| S4 | Mon 09:00 | 480 | True | 1 | [(Mon 09:00, 17:00)] — fits in single span |

### 8.7 New: Allocate and Deallocate

| # | Test | Expected |
|---|---|---|
| A1 | allocate, then check bits | spans marked 0 (occupied) |
| A2 | allocate then deallocate | bits restored exactly to pre-allocate state |
| A3 | two sequential allocates same resource | second starts at finish of first |
| A4 | allocate with deadline exceeded | raises InfeasibleError, bitmap unchanged |
| A5 | deallocate record from different resource | raises ValueError |

### 8.8 New: Checkpoint and Restore

| # | Test | Expected |
|---|---|---|
| C1 | checkpoint, allocate, restore | bitmap identical to pre-allocate state |
| C2 | checkpoint, allocate × 3, restore | all three allocations undone |
| C3 | two checkpoints, restore first | restores to first snapshot, not second |
| C4 | restore after successful branch | bitmap returns to branch point |

### 8.9 New: Continuity (parametric)

These are the v2 equivalent of the v1 consistency tests — proving that Layer 2 is consistent with Layer 1.

```python
@pytest.mark.parametrize("work_units", [1, 30, 60, 480, 1000])
@pytest.mark.parametrize("allow_split", [False, True])
def test_allocation_work_units_correct(bitmap, start_int, work_units, allow_split):
    """Allocated work_units matches requested work_units."""
    record = allocate(bitmap, "op1", start_int, work_units, allow_split)
    assert record.work_units == work_units

@pytest.mark.parametrize("work_units", [1, 30, 60, 480, 1000])
def test_allocate_deallocate_exact_inverse(bitmap, start_int, work_units):
    """Deallocate returns bitmap to exactly pre-allocate state."""
    snap_before = bitmap.checkpoint()
    record = allocate(bitmap, "op1", start_int, work_units)
    deallocate(bitmap, record)
    assert bitmap.bits == bytearray(snap_before)

@pytest.mark.parametrize("work_units", [1, 30, 60, 480, 1000])
def test_layer1_layer2_consistency(calendar, bitmap, epoch, resolution, 
                                    horizon_start, work_units):
    """Layer 2 finish time must equal Layer 1 add_minutes result."""
    record = allocate(bitmap, "op1",
                      resolution.to_int(horizon_start, epoch), work_units)
    layer1_finish = calendar.add_minutes(horizon_start, work_units)
    assert resolution.to_datetime(record.finish, epoch) == layer1_finish
```

The last test is the key cross-layer consistency assertion: the bitmap walk and the datetime walk must produce identical finish times for the same inputs.

---

## 9. Code to Remove

Unchanged from v1. The following are eliminated by the redesign:

| Function | Reason |
|---|---|
| `calculate_dynamic_buffer_days` | Eliminated by lazy walk |
| `build_working_intervals` | Replaced by lazy walk; retained optionally as PrecomputedIntervals for batch |
| `add_working_minutes` (current) | Replaced by `WorkingCalendar.add_minutes` |
| `WEEKDAY_MAP` | Replaced by ISO integer mapping |

---

## 10. Migration Checklist

Steps 1–14 from v1 are unchanged. New steps for v2:

15. Implement `working_intervals_in_range` on `WorkingCalendar`
16. Implement `TimeResolution` in `resolution.py`
17. Implement `OccupancyBitmap` with `from_calendar`, `copy`, `checkpoint`, `restore`
18. Implement `AllocationRecord` dataclass
19. Implement `walk`, `allocate`, `deallocate`, `_mark_spans` in `occupancy.py`
20. Write Layer 2 test suite (sections 8.4–8.9)
21. Verify cross-layer consistency test passes (8.9 final parametric test)
22. Update `__init__.py` to export Layer 2 public API
23. Create `docs/architecture-notes.md` for platform portability context

---

## 11. Platform Portability Summary

*(Full discussion in `docs/architecture-notes.md`)*

The integer core (Layer 2) ports cleanly to TypeScript because integer arithmetic is identical across Python and TypeScript/JavaScript for values within the safe integer range (up to 2^53). A one-week minute-resolution bitmap contains 10,080 units — well within safe integer arithmetic on any platform.

**TypeScript port** is the connector target for Office Scripts and browser-side scheduling. The implementation strategy is: develop and test as a standard Node.js ES2020 module with Jest, then adapt for Office Scripts by flattening to a single-file namespace. Develops outside Office Scripts first, validated against the Python test fixtures.

**Power Query M** validates the algorithm's expressibility in a purely functional style. `ImmutableLog` (the append-only variant of the allocation log) maps directly to M's `List.Accumulate` accumulator pattern. It is a validation layer for the Excel Computation Lab, not a production target.

**Implementation priority**: Python first. TypeScript and M connectors are built when concrete project requirements demand them, not speculatively.
