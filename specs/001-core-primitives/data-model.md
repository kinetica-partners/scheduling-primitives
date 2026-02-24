# Data Model: Core Scheduling Primitives

**Date**: 2026-02-24
**Source**: [spec.md](spec.md), [research.md](research.md)

## Entity Relationship Overview

```
WorkingCalendar ──from_calendar()──▶ OccupancyBitmap ──walk()──▶ AllocationRecord
       │                                    │
       │ rules + exceptions                 │ checkpoint/restore
       │                                    │ dynamic exceptions
       ▼                                    ▼
  [datetime domain]                  [integer domain]
       │                                    │
       └──────── TimeResolution ────────────┘
                 (boundary conversion)
```

## Entities

### WorkingCalendar

The horizon-free, datetime-based calendar definition. Answers time queries by lazy day-by-day walk.

| Field | Type | Description |
| ----- | ---- | ----------- |
| pattern_id | str | Unique identifier for this availability pattern |
| rules | dict[int, list[tuple[time, time]]] | Weekly rules keyed by Python weekday (0=Mon). Each value is a sorted list of (start_time, end_time) periods. end_time < start_time indicates overnight. |
| exceptions | dict[str, list[ExceptionEntry]] | Planned exceptions keyed by ISO date string. Each entry specifies is_working, start_time, end_time. |

**Identity**: `pattern_id` — multiple resources may share the same calendar pattern.

**Lifecycle**: Immutable after construction. Calendar definitions do not change during a scheduling run. Dynamic changes happen at the capacity layer, not the calendar layer.

**Methods** (FR-001 through FR-005, FR-009):
- `add_minutes(start, minutes) → datetime` — forward walk
- `subtract_minutes(end, minutes) → datetime` — backward walk
- `working_minutes_between(start, end) → int` — count working time
- `working_intervals_in_range(start, end) → Iterator[tuple[datetime, datetime]]` — enumerate intervals

**Validation rules**:
- Rules must have non-overlapping periods per day after overnight splitting
- Exception times must be valid HH:MM
- Exception dates must be valid ISO dates

### ExceptionEntry

A single planned exception for a specific date.

| Field | Type | Description |
| ----- | ---- | ----------- |
| is_working | bool | True = adds working time (overtime). False = removes working time (holiday). |
| start_time | time or None | Start of exception period. None only when is_working=False for full-day removal. |
| end_time | time or None | End of exception period. None only when is_working=False for full-day removal. |

### TimeResolution

The boundary conversion layer. Immutable.

| Field | Type | Description |
| ----- | ---- | ----------- |
| unit_seconds | int | Seconds per unit. 60=minute, 3600=hour, 300=5-min block. |
| label | str | Human-readable label for display ("minute", "hour", "5min"). |

**Methods** (FR-020, FR-034):
- `to_int(dt, epoch) → int` — convert datetime to integer units from epoch. Raises on misalignment.
- `to_datetime(t, epoch) → datetime` — convert integer units back to datetime.

**Predefined instances**: `MINUTE`, `HOUR`.

### OccupancyBitmap (Capacity State)

The integer-based, auto-extending capacity tracker for one resource.

| Field | Type | Description |
| ----- | ---- | ----------- |
| resource_id | str | Which resource this bitmap tracks. |
| horizon_begin | int | Integer units from epoch for the start of the bitmap. |
| bits | bytearray | `bits[i]=1` → free. `bits[i]=0` → occupied or non-working. |
| _calendar | WorkingCalendar | Retained reference for auto-extension. |
| _resolution | TimeResolution | Resolution used at materialisation. |
| _epoch | datetime | Epoch used at materialisation. |
| _allocations | list[AllocationRecord] | Index of committed allocations for conflict detection. |

**Identity**: `resource_id` — one bitmap per resource per scheduling run.

**Derived**:
- `horizon_end → int` = `horizon_begin + len(bits)`

**Lifecycle / State transitions**:
```
                    from_calendar()
  [not created] ────────────────────▶ [materialised]
                                           │
                               ┌───────────┼───────────┐
                               ▼           ▼           ▼
                          [allocated]  [snapshot]  [auto-extended]
                               │           │
                               ▼           ▼
                         [deallocated] [restored]
```

**Methods** (FR-010 through FR-019, FR-027 through FR-029, FR-033):
- `from_calendar(cal, horizon_start, horizon_end, epoch, resolution) → OccupancyBitmap` — materialise
- `walk(operation_id, earliest_start, work_units, allow_split, min_split, deadline) → AllocationRecord` — read-only slot finding
- `allocate(operation_id, ...) → AllocationRecord` — walk + commit
- `deallocate(record) → None` — release allocation (exact inverse)
- `apply_exception(begin, end, is_working) → list[AllocationRecord]` — dynamic exception, returns affected allocations
- `checkpoint() → bytes` — snapshot state
- `restore(snap) → None` — restore to snapshot
- `copy() → OccupancyBitmap` — deep copy for branching

**Auto-extension**: When walk or apply_exception reaches beyond `horizon_end`, the bitmap extends by calling `_calendar.working_intervals_in_range()` for the additional window and appending to `bits`.

### AllocationRecord

Immutable record of a committed or candidate allocation.

| Field | Type | Description |
| ----- | ---- | ----------- |
| operation_id | str | Which operation this allocation is for. |
| resource_id | str | Which resource the allocation is on. |
| start | int | First occupied unit (absolute, from epoch). |
| finish | int | One past the last occupied unit (half-open). |
| work_units | int | Total working units consumed. |
| allow_split | bool | Whether this allocation spans non-contiguous runs. |
| spans | tuple[tuple[int, int], ...] | Contiguous free runs consumed. Each is (begin, end) half-open. |

**Identity**: `(operation_id, resource_id)` — one allocation per operation per resource.

**Derived**:
- `wall_time → int` = `finish - start` (includes non-working gaps)
- `is_complete(required) → bool` = `work_units >= required`

**Invariants**:
- `sum(end - begin for begin, end in spans) == work_units`
- All spans are within `[start, finish)`
- Spans are sorted by begin and non-overlapping

### InfeasibleError

Custom exception raised when work cannot be completed before deadline or horizon end (FR-017).

| Field | Type | Description |
| ----- | ---- | ----------- |
| operation_id | str | Which operation failed. |
| work_units_remaining | int | How much work could not be placed. |
| work_units_requested | int | Total work requested. |
| reason | str | "deadline" or "horizon" |

## Input Schema (Data Tables)

These define how calendar data is provided to the library. Based on the Frictionless Data Package format.

### Table: rules

Recurring weekly rules. Multiple rows per `(pattern_id, day_of_week)` define multi-period days.

| Column | Type | Constraints | Description |
| ------ | ---- | ----------- | ----------- |
| pattern_id | str | required | Calendar pattern identifier |
| day_of_week | int | required, 1–7 | ISO 8601 weekday (1=Mon, 7=Sun) |
| start_time | str | required, HH:MM | Period start |
| end_time | str | required, HH:MM | Period end. Earlier than start = overnight rule |

**Primary key**: `(pattern_id, day_of_week, start_time)`

### Table: exceptions

Date-specific overrides.

| Column | Type | Constraints | Description |
| ------ | ---- | ----------- | ----------- |
| pattern_id | str | required | FK to rules.pattern_id |
| exception_date | str | required, YYYY-MM-DD | The specific date |
| is_working | int | required, 0 or 1 | 1=adds working time, 0=removes |
| start_time | str | required if is_working=1, HH:MM | |
| end_time | str | required if is_working=1, HH:MM | |

**Primary key**: `(pattern_id, exception_date, is_working, start_time)`

### Table: resource_calendar

Maps resources to calendar patterns. Lives outside the core engine — used by the reference scheduler and callers.

| Column | Type | Description |
| ------ | ---- | ----------- |
| resource_id | str | Work centre, machine, operator, etc. |
| pattern_id | str | FK to rules.pattern_id |
| effective_from | str or None | When this assignment starts (None=always) |
| effective_to | str or None | When this assignment ends (None=ongoing) |
