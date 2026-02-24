# Research: Core Scheduling Primitives

**Date**: 2026-02-24
**Status**: Complete — no unresolved unknowns

## R1: Auto-Extending Capacity State

**Decision**: The OccupancyBitmap starts with an initial horizon and extends by appending to the bytearray when a walk or dynamic exception reaches beyond it. The calendar reference is retained for lazy materialisation of additional time.

**Rationale**: The Working Calendar (Layer 1) is already horizon-free — it walks day-by-day on demand. Forcing Layer 2 to pre-commit to a fixed horizon creates an artificial constraint. Auto-extension means the bitmap grows proportionally to the time range actually touched, not a pre-specified maximum. This supports both short scheduling runs (small bitmap) and long simulations (grows as needed).

**Alternatives considered**:
- Fixed horizon with rejection at boundary: Simpler but forces callers to guess the horizon. Rejected because it adds an unnecessary usability burden and fails silently for long-running jobs.
- Linked chunks instead of contiguous bytearray: Would avoid reallocation cost but adds complexity for span arithmetic. Rejected — Python's bytearray growth amortisation is sufficient, and contiguous memory is better for the simple bit-scanning walk.

**Implementation note**: The bitmap retains a reference to its source calendar and resolution. When `walk()` or a dynamic exception reaches beyond `horizon_end`, the bitmap calls `calendar.working_intervals_in_range()` for the extension window, appends the new bits, and updates `horizon_end`. Extension is forward-only (appending). Backward extension is not needed because `earliest_start` is always >= `horizon_begin`.

## R2: Overnight Rule Resolution

**Decision**: An overnight rule (e.g. 22:00–06:00) is stored as a single rule with `start_time > end_time`. The day-period resolution splits it into two intervals: one on the defining day (22:00–midnight) and one on the next day (midnight–06:00). The next-day portion is generated when that day is visited by the walk.

**Rationale**: Storing overnight as a single rule matches how practitioners think about shifts ("the night shift is 10pm to 6am"). Splitting at midnight internally is a mechanical concern handled by `periods_for_date()`. The half-open interval convention makes midnight unambiguous: `[22:00, 00:00)` on day D means 22:00 to midnight, and `[00:00, 06:00)` on day D+1 means midnight to 06:00.

**Alternatives considered**:
- Require callers to split overnight rules into two per-day rules: Burdens the user and is error-prone. Rejected.
- Store time as minutes-from-midnight allowing values > 1440: Works but breaks the day-by-day walk model and the lazy evaluation pattern. Rejected.

## R3: Dynamic Exception Conflict Detection

**Decision**: Dynamic exceptions that remove capacity check for conflicts with existing allocations by scanning the affected span for occupied bits. If occupied bits are found that correspond to committed allocations, the library returns a list of affected allocation record identifiers. The library does not resolve the conflict.

**Rationale**: The bitmap alone can detect that bits in the affected span are occupied (value=0 when they should be free). However, the bitmap does not inherently know *which* allocation occupies each bit. Conflict detection requires maintaining a mapping from allocated spans to allocation records. This is a lightweight index — a sorted list of (span_begin, span_end, operation_id) tuples that can be binary-searched.

**Alternatives considered**:
- Per-bit ownership tracking (each bit stores an operation ID): Memory-intensive (1 byte per bit → 8x the bitmap). Rejected for the common case where conflict detection is rare.
- No conflict detection (caller is responsible for all bookkeeping): Violates FR-033 which requires the library to detect and report. Rejected.
- Full allocation registry as a separate data structure: Considered. The allocation index (sorted span list) is a lightweight version of this. The full registry might be needed in future but the span index is sufficient for FR-033.

**Implementation note**: OccupancyBitmap maintains an internal `_allocations` list of AllocationRecord references. When a dynamic exception removes capacity, it searches this list for overlapping spans and returns the affected records. The list is append-only during normal allocation and is only searched during dynamic exception application — not in the hot path.

## R4: Property-Based Test Strategy

**Decision**: Hypothesis property-based tests target the following functions (per constitution §5): `walk()`, `allocate()`, `deallocate()`, `TimeResolution.to_int()`, `TimeResolution.to_datetime()`, and `WorkingCalendar.add_minutes()` / `subtract_minutes()`.

**Properties to test**:
- Round-trip: `add_minutes(subtract_minutes(dt, n), n) == dt` for any valid dt and n
- Round-trip: `deallocate(allocate(bitmap, ...)) ≡ original bitmap`
- Consistency: `to_datetime(to_int(dt)) == dt` for aligned datetimes
- Monotonicity: `walk(bitmap, ..., work_units=n)` finish time is monotonically increasing in n
- Span sum: `sum(span_end - span_begin for span in record.spans) == record.work_units`
- Greedy optimality (splittable): splittable walk produces earliest possible finish given available free runs

**Rationale**: These properties catch classes of bugs that hand-picked test cases miss — particularly around boundary conditions and large/unusual inputs. Hypothesis generates edge cases (zero-length, maximum values, sparse calendars) that would be tedious to enumerate manually.

## R5: Schema Input Format

**Decision**: Calendar input data uses the Frictionless Data Package format with JSON as the primary fixture format. CSV is supported for human authoring. Pydantic models validate business rules after loading.

**Rationale**: JSON is unambiguous across platforms (the portability contract). CSV is friendlier for practitioners. The schema tables (rules, exceptions, resource_calendar) use snake_case, ISO 8601 dates/times, ISO weekday integers (1=Mon through 7=Sun), and integer booleans (0/1).

**Alternatives considered**:
- YAML: More human-readable than JSON but introduces a dependency (PyYAML) or requires custom parsing. Rejected — violates zero-dependency constraint.
- TOML: Python 3.11+ has stdlib `tomllib`. Possible future addition but JSON is the primary contract format.
