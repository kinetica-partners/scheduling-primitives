# Architecture: scheduling-primitives

**Version**: 1.0.0
**Status**: Draft
**Governs**: Structural decisions, abstraction boundaries, engine interface

This document sits between the constitution (principles) and the spec (requirements). It defines the core abstractions, their responsibilities, and the tradeoffs between implementation strategies. Any port of this library to another language must preserve these abstractions and the engine interface.

---

## 1. Terminology

These terms are used precisely throughout all project documents.

**Calendar** -- The rules and planned exceptions that define recurring availability for a resource. Weekly shift patterns, public holidays, planned maintenance, pre-approved overtime. Immutable once compiled. Shared across all branches in a search. This is configuration, not state.

**Capacity state** -- The working representation of what time is free on one resource. Produced by compiling a calendar. Mutable during a run via allocations and dynamic exceptions. Branch-local in branch-and-bound. Two implementations: bitmap (dense) and interval list (sparse).

**Compiler** -- The process that transforms a calendar (rules + planned exceptions) into initial capacity state at a given resolution. Runs once per resource per scheduling run. This is the datetime boundary -- everything it produces is integer.

**Engine** -- The operations on capacity state. Pure integer. Knows nothing about datetimes, shift patterns, or calendars. Two implementations (bitmap and interval list) behind one interface. This is the foundation of the library.

**Resolution** -- Defines what one integer unit means (60 seconds = minute, 3600 = hour). Set once per scheduling run. Used by the compiler and the API layer. Never referenced inside the engine.

**Allocation** -- A committed claim on capacity. Tracked by record. Reversible by release or by snapshot restore. Has an operation_id because it represents productive work.

**Dynamic exception** -- A capacity mutation during a run. Adding capacity (overtime authorization) or removing it (breakdown, emergency maintenance). Not tracked by allocation record. Reversible only by snapshot restore. Represents a decision, not productive work.

**Lazy walk** -- Answering time arithmetic questions without capacity state. Uses the compiler to get integer intervals one day at a time, scans forward or backward through them. No materialization, no contention tracking. For routing and calendar queries where an engine is not needed.

**Scheduling API** -- The user-facing layer. Datetimes in, datetimes out. Owns the lifecycle: register resources, schedule operations, return results. Users never see integers or capacity state directly.

---

## 2. Core Abstractions

### 2.1 Abstraction Stack

```
Scheduling API           datetime in/out, user-facing
    |
    |  uses
    v
Engine                   pure integer, the foundation
    |                    find_slot, commit, release
    |                    set_available, set_unavailable
    |                    snapshot, restore
    |
    |  populated by
    v
Compiler                 calendar -> integer intervals
    |                    the datetime boundary
    |
    |  reads
    v
Calendar                 rules + planned exceptions
                         immutable configuration
```

The direction is bottom-up: the engine is the foundation. The calendar is input. The compiler bridges them. The API wraps everything for users.

### 2.2 What Each Abstraction Knows

| Abstraction | Knows | Does Not Know |
|---|---|---|
| Calendar | Shift patterns, weekday rules, overnight periods, planned exceptions, date arithmetic | Integers, resolution, capacity, allocations |
| Compiler | How to convert datetime periods to integer intervals at a given resolution | Capacity state, allocations, engine internals |
| Engine | Integer intervals, free/occupied state, slot-finding, allocation tracking | Datetimes, calendars, shift patterns, what a "minute" means |
| Resolution | Unit size (seconds per unit), datetime-to-int conversion | Everything else -- it is a pure conversion utility |
| Scheduling API | Datetimes, resource registration, result formatting | Engine internals, bitmap vs interval list |

### 2.3 The Boundary Rule (refined)

The constitution states: "A layer's responsibility ends where a different kind of knowledge begins."

Concretely:

- **The datetime boundary** sits at the compiler. Above it: datetimes, dates, shift patterns, weekday rules. Below it: integers. After compilation, no datetime crosses into the engine.

- **The primitives boundary** sits at the engine interface. Below it: mechanical slot-finding and state management. Above it: policy decisions (which operation next, which resource to prefer, whether to authorize overtime). The engine answers "does this fit, and where?" It does not answer "should we do this?"

---

## 3. The Engine Interface

This is the core abstraction of the library. Both implementations (bitmap and interval list) satisfy this interface.

```
Engine Interface:

    # Construction
    from_intervals(resource_id, intervals, horizon_begin) -> Engine
        Initialize capacity state from sorted integer interval pairs.

    # Slot finding (read-only)
    find_slot(operation_id, earliest_start, work_units,
              allow_split=False, min_split=1, deadline=None) -> Record
        Find earliest position where work fits. Does NOT mutate state.

    # Allocation (tracked, reversible by record)
    commit(record) -> CommittedRecord
        Mark record's spans as occupied. Track the allocation.

    release(record)
        Restore record's spans to free. Exact inverse of commit.

    # Capacity mutation (direct state change)
    set_available(begin, end)
        Mark a range as free. Used for dynamic overtime.

    set_unavailable(begin, end) -> list[Record]
        Mark a range as occupied. Returns any allocation records
        whose spans overlap the affected range (conflict detection).
        Used for dynamic breakdowns.

    # State management
    snapshot() -> opaque
        Immutable snapshot of all state (capacity + allocation tracking).

    restore(snapshot)
        Return to a previous snapshot. Undoes all mutations since.

    # Inspection
    free_count() -> int
        Total free units in the current state.

    horizon_begin -> int
    horizon_end -> int
```

The `find_slot` + `commit` separation (DR-6 from the constitution) is what enables speculative exploration. B&B calls `find_slot` to evaluate a candidate, then decides whether to `commit`.

---

## 4. Two Engine Implementations

### 4.1 Bitmap Engine

Dense representation. One byte per time unit. `bits[i] = 1` means free, `bits[i] = 0` means not-free.

**Characteristics:**
- Memory: O(horizon x resolution) -- 10 KB per resource-week at minute grain
- find_slot: O(n) linear scan through bits
- commit/release: O(k) flip bits, where k = span length
- snapshot: O(n) copy bytes
- restore: O(n) overwrite bytes
- Cache behavior: Sequential access, prefetcher-friendly

**Best for:** Greedy scheduling, branch-and-bound. Sequential scan is fast when the working set fits in CPU cache. Checkpoint/restore is a byte copy -- the cheapest possible branching mechanism.

**Cache analysis:**

| Scenario | Memory | Fits in |
|---|---|---|
| 1 resource, 1 week, minute | 10 KB | L1 (32-64 KB) |
| 20 resources, 1 week, minute | 200 KB | L2 (256 KB - 1 MB) |
| 20 resources, 4 weeks, minute | 800 KB | L3 (8-32 MB) |
| 20 resources, 4 weeks, hour | 13 KB | L1 |
| 1 resource, 1 year, minute | 512 KB | L2/L3 |

**Limitation:** Cost scales with horizon regardless of utilization. A year-long horizon at minute grain costs 512 KB per resource even if the resource is mostly idle. For long horizons, either use coarser resolution or the interval list engine.

### 4.2 Interval List Engine

Sparse representation. Sorted list of `(begin, end)` integer pairs representing free intervals.

**Characteristics:**
- Memory: O(m) where m = number of intervals -- typically a few KB regardless of horizon
- find_slot: O(log m) binary search to find starting interval, then scan forward
- commit: O(k) split/merge intervals
- release: O(k) merge intervals back together
- snapshot: O(m) copy list
- restore: O(m) replace list
- Cache behavior: Pointer-based, less cache-friendly than bitmap for linear scans

**Best for:** Constraint solvers, long-horizon simulation. Natural representation for bound propagation. Memory does not scale with horizon length -- a year-long schedule costs the same as a one-week schedule if they have the same number of intervals.

**Resolution independence:** The interval list's storage cost depends on the number of intervals, not on resolution. A year at minute resolution and a year at hour resolution produce the same number of intervals from the same calendar. This eliminates the need for time fences or multi-resolution schemes for long-horizon scheduling.

### 4.3 Tradeoff Summary

| Dimension | Bitmap | Interval List |
|---|---|---|
| Memory | O(horizon x resolution) | O(num_intervals) |
| find_slot | O(n) scan | O(log m) search |
| commit/release | O(k) bit flips | O(k) interval split/merge |
| snapshot/restore | O(n) byte copy | O(m) list copy |
| Cache behavior | Sequential, prefetcher-friendly | Pointer chasing |
| Best strategy | Greedy, B&B (scan + backtrack) | Constraint solver (bound propagation) |
| Horizon scaling | Linear in horizon x resolution | Independent of horizon |
| Long horizon | Needs coarse resolution or time fences | Native support, no adaptation needed |

The engine interface is identical. Code above the engine (compiler, API, scheduling strategies) works with either implementation without modification.

---

## 5. Calendar Compiler

The compiler transforms a calendar into initial capacity state. It is the only component that crosses the datetime boundary.

```
Input:  Calendar (rules + planned exceptions)
        Resolution (what one integer unit means)
        Date range to compile

Output: List of (begin, end) integer interval pairs
        representing free (working) time

Process:
    for each date in range:
        periods = calendar.periods_for_date(date)
        for (start_time, end_time) in periods:
            begin = resolution.to_int(combine(date, start_time), epoch)
            end   = resolution.to_int(combine(date, end_time), epoch)
            emit (begin, end)
```

The compiler's output feeds directly into either engine:
- Bitmap: iterate intervals, set `bits[begin..end] = 1`
- Interval list: the output IS the initial state (sorted intervals)

**Planned exceptions** are resolved during compilation. A holiday removes a day's periods. Overtime adds a period. The compiler resolves these by calling `calendar.periods_for_date()`, which already handles exception logic. The engine never sees exceptions -- it just sees integer intervals.

---

## 6. Lazy Walk

The lazy walk answers datetime time-arithmetic questions without an engine instance. It uses the compiler's per-day output but never materializes full capacity state.

```
walk_forward(compiler, resolution, start_dt, work_units):
    remaining = work_units
    current_date = start_dt.date()
    pos = offset_within_day(start_dt, resolution)

    while remaining > 0:
        intervals = compiler.intervals_for_date(current_date, resolution)
        for (begin, end) in intervals:
            if end <= pos: continue
            effective_start = max(begin, pos)
            available = end - effective_start
            if remaining <= available:
                return to_datetime(current_date, effective_start + remaining)
            remaining -= available
        current_date = next_day(current_date)
        pos = 0
```

This is the same scan-forward pattern as the engine's `find_slot`, but without state. No bitmap, no interval list, no capacity object. Just the compiler producing integer intervals one day at a time and a local scan consuming them.

**When to use the lazy walk vs the engine:**
- Lazy walk: calendar arithmetic, routing (FS chains), questions about time without contention
- Engine: allocation with contention, B&B, any scenario where multiple operations compete for capacity

The lazy walk exists because sometimes you genuinely don't need capacity tracking. A routing calculation that chains operations across different resources just needs to know "when does step 1 finish so step 2 can start?" No bitmap needed.

---

## 7. Dynamic Exceptions and Branch-and-Bound

### 7.1 Two Moments

**Before the run:** Rules + planned exceptions compile into initial capacity state. This is immutable. Every branch starts from this base.

**During the run:** Dynamic exceptions arise as decisions. The engine's `set_available` and `set_unavailable` apply them. `snapshot`/`restore` manages branching.

### 7.2 How Dynamic Exceptions Interact with B&B

```
base_state = compiler.compile(calendar, resolution, horizon)
engine = BitmapEngine.from_intervals("MAZAK-1", base_state)

def explore(engine, remaining_ops, overtime_options):
    snap = engine.snapshot()

    # Branch A: schedule without overtime
    try:
        for op in remaining_ops:
            record = engine.find_slot(op.id, op.earliest, op.work)
            engine.commit(record)
        evaluate(engine)
    finally:
        engine.restore(snap)

    # Branch B: authorize Saturday overtime, then schedule
    try:
        engine.set_available(sat_08_00, sat_17_00)
        for op in remaining_ops:
            record = engine.find_slot(op.id, op.earliest, op.work)
            engine.commit(record)
        evaluate(engine, overtime_cost=SAT_PREMIUM)
    finally:
        engine.restore(snap)  # undoes overtime AND allocations
```

The restore undoes everything -- allocations and dynamic exceptions alike. No separate undo mechanism needed. Both are just state mutations that snapshot/restore handles uniformly.

### 7.3 Why This Matters

In real production scheduling, overtime is not free. It has a premium cost. The question "should we authorize Saturday overtime to meet Tuesday's due dates?" is an optimization problem. The engine makes it possible to explore both branches (with overtime, without overtime) and compare the total cost. The engine doesn't decide -- it provides the mechanism. The decision logic lives in the scheduling strategy above.

---

## 8. Resolution

Resolution defines what one integer unit means. It is set once per scheduling run and used at two boundaries:

1. **Compiler boundary:** datetime -> integer when compiling calendar periods
2. **API boundary:** integer -> datetime when returning results to users

The engine never references resolution. It works with dimensionless integers.

### 8.1 Resolution as a Performance Parameter

| Resolution | Units/week | Bitmap/resource/week | Precision |
|---|---|---|---|
| Second | 604,800 | 590 KB | Sub-minute |
| Minute | 10,080 | ~10 KB | Standard |
| 5-minute | 2,016 | ~2 KB | Coarse |
| Hour | 168 | 168 bytes | Simulation |
| Day | 7 | 7 bytes | Rough-cut |

For the bitmap engine, resolution directly controls memory and scan cost. For the interval list engine, resolution has negligible effect on storage -- the same number of intervals regardless of grain.

### 8.2 Resolution Alignment

The compiler rejects datetimes that don't align to the resolution. At hour resolution, a shift starting at 08:30 is an error, not silently rounded. The caller must ensure calendar times align to the chosen resolution. This is strict by design -- silent rounding hides discretisation error.

---

## 9. Portability

The engine interface is the portable core. Any implementation in any language must preserve:

1. **Integer-only engine.** No datetime, no float inside the engine.
2. **Half-open intervals.** `[begin, end)` throughout. Length = end - begin.
3. **find_slot does not mutate.** Read-only speculation.
4. **commit/release are exact inverses.** No residual drift.
5. **snapshot/restore round-trips.** State after restore is identical to state at snapshot.
6. **The test fixtures are the contract.** JSON fixtures define expected behavior. A port validates against the same fixtures as the Python reference.

The compiler and calendar are implementation details that may vary by language. The engine interface and its behavioral contract are what ports must match.

---

## 10. What This Architecture Excludes

Per the constitution (Section 6), these belong in libraries built on top of the engine:

- **Dispatch rules** -- which operation to schedule next
- **Resource selection** -- which machine to assign
- **Optimization algorithms** -- B&B, metaheuristics, constraint programming
- **Simulation** -- Monte Carlo, discrete event
- **Multi-resource constraints** -- operation needs machine AND operator AND tool

The engine provides the mechanism (find slot, commit, backtrack). The strategy layer above provides the policy. The architecture makes this boundary explicit: the engine answers "does this fit?" and "where?", never "should we?"

---

## 11. Relationship to Constitution and Spec

**Constitution** governs principles. This architecture applies them:
- Design Principle I (Boundary Rule) -> Section 2.3
- Design Principle II (Integer Time) -> Section 3, 8
- Design Principle III (Half-Open Intervals) -> Section 9
- Design Principle IV (Walk Does Not Mutate) -> Section 3 (find_slot)
- Design Principle VI (Visual Verification) -> unchanged, applies to both engines

**Spec** governs requirements. This architecture structures how they are met:
- FR-001 through FR-005 (calendar arithmetic) -> Lazy walk (Section 6)
- FR-010 through FR-017 (capacity tracking) -> Engine interface (Section 3)
- FR-018, FR-019 (backtracking) -> snapshot/restore (Section 3, 7)
- FR-020, FR-021 (boundary conversion) -> Compiler + Resolution (Section 5, 8)
- FR-027 through FR-029 (dynamic exceptions) -> set_available/set_unavailable (Section 7)

The spec's "Layer 1" and "Layer 2" terminology is superseded by this architecture's terminology: Calendar, Compiler, Engine, API.
