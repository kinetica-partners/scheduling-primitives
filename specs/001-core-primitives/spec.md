# Feature Specification: Core Scheduling Primitives

**Feature Branch**: `001-core-primitives`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "A Python library that provides the primitives for doing core calculations that serve finite scheduling algorithms. Designed to be a performant, elegant core that can form as a reference for porting to other languages and applying common algorithmic approaches for doing the underlying calendar calculations."

## Purpose

This library serves three audiences:

1. **Developers building scheduling systems** — the primary technical audience. They need correct, performant primitives they can build dispatching, optimisation, and simulation on top of.

2. **Practitioners learning scheduling techniques** — operations managers, planners, and analysts whose experience may not extend beyond Excel. The library and its reference scheduler serve as a teaching tool: concrete, runnable code that makes scheduling concepts tangible. Clear naming, visual output, and worked examples matter as much as the algorithm.

3. **The scheduling community** — the library is open source to establish the author as a subject matter expert and authority in production scheduling, to invite collaboration and contributions, and to seed a shared foundation that others can build on. Code quality, documentation quality, and approachability are not afterthoughts — they are part of the value proposition.

These audiences shape design decisions throughout: practitioner-facing names over academic jargon, ASCII visualisation as a first-class feature, a reference scheduler that teaches by example, and a codebase clean enough to attract contributors.

## Clarifications

### Session 2026-02-24

- Q: When a dynamic exception removes capacity that overlaps an existing allocation, what should the library do? → A: Detect and report which allocation records are affected; caller decides how to handle (consistent with the primitives boundary — conflict resolution is policy).
- Q: At coarse resolution, when a working period does not align to unit boundaries, what should happen? → A: Strict rejection — no implicit rounding. Caller must ensure alignment to the chosen resolution.
- Q: When a dynamic exception or walk extends beyond the materialised horizon, what should happen? → A: Auto-extend. The capacity state grows on demand by materialising more calendar time. The horizon is not a hard wall — it is an initial estimate that extends lazily when needed.
- Q: Are calendars and exceptions assumed to be in the same time zone? Is UTC conversion required? → A: All datetimes are naive (no tzinfo) and assumed to be in the facility's local time. The library does not perform any time zone conversion. Cross-timezone coordination (e.g. global supply chains where Factory A in Shanghai feeds Factory B in Hamburg) is an orchestration concern handled by the calling layer.

## Terminology

This library uses practitioner-facing names. The mapping to scheduling theory is recorded here for clarity.

| Library term       | Scheduling theory          | Meaning                                                           |
| ------------------ | -------------------------- | ----------------------------------------------------------------- |
| `allow_split`      | Preemptive / non-preemptive | Whether an operation may be interrupted and resumed across gaps   |
| `work_units`       | Processing time (pj)       | Amount of working time an operation requires                      |
| `earliest_start`   | Release date (rj)          | First moment the operation may begin                              |
| `deadline`         | Due date / deadline (dj)   | Last moment by which the operation must complete                  |

In prose: use the theoretical term with the code name in parentheses on first use. In code: use the practitioner-facing name.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Calendar Time Arithmetic (Priority: P1)

A developer building a scheduling system needs to answer time questions against a working calendar: "If I start a 120-minute job at 4pm on Friday with an 8–5 Mon–Fri calendar, when does it finish?" and the reverse: "If this job must finish by 10am Wednesday, when must it start?" These are the foundational queries that every scheduling algorithm depends on.

**Why this priority**: Without calendar time arithmetic, no scheduling calculation is possible. This is the bedrock.

**Independent Test**: Can be fully tested by providing calendar rules and querying forward/backward walks. Delivers immediate value — developers can compute schedule dates without building the occupancy layer.

**Acceptance Scenarios**:

1. **Given** a standard Mon–Fri 08:00–17:00 calendar, **When** I walk forward 60 minutes from Monday 09:00, **Then** I get Monday 10:00.
2. **Given** a calendar where Tuesday is a holiday, **When** I walk forward 60 minutes from Monday 16:30, **Then** the result skips Tuesday entirely and lands on Wednesday.
3. **Given** the same calendar, **When** I walk backward 60 minutes from Wednesday 10:00, **Then** I get Monday 16:00 (skipping Tuesday).
4. **Given** two datetimes spanning a holiday, **When** I count working time between them, **Then** the holiday contributes zero.
5. **Given** a date range, **When** I request the working intervals, **Then** I receive the individual working periods within that range.

---

### User Story 2 — Capacity Tracking and Allocation (Priority: P1)

A developer needs to track what capacity is available on a resource over a planning horizon, find the earliest slot where work can fit, and commit that allocation. This is the core of finite capacity scheduling — knowing not just when time is working, but what's still free after prior commitments.

**Why this priority**: Calendar arithmetic alone gives infinite capacity. Finite capacity scheduling requires tracking what has been consumed. These two stories together form the minimum viable library.

**Independent Test**: Given a materialised calendar with some pre-existing allocations, find and commit a new allocation, then verify the occupied time is no longer available.

**Acceptance Scenarios**:

1. **Given** a resource with a materialised calendar and no prior allocations, **When** I find the earliest slot for 60 units of non-splittable work starting Monday 09:00, **Then** I get a contiguous block Monday 09:00–10:00.
2. **Given** a resource where Monday 16:30–17:00 is the only remaining free time on Monday, **When** I find a slot for 60 units of non-splittable work, **Then** the result skips to the next day with a large enough window.
3. **Given** the same situation, **When** I find a slot for 60 units of splittable work, **Then** the result uses Monday 16:30–17:00 (30 units) and continues into the next available day (30 units).
4. **Given** a committed allocation, **When** I release it, **Then** the capacity is restored exactly to its prior state.
5. **Given** a resource and a deadline, **When** the work cannot fit before the deadline, **Then** the library signals infeasibility.

---

### User Story 3 — Speculative Planning and Backtracking (Priority: P2)

A developer building an optimisation algorithm (branch-and-bound, beam search, etc.) needs to try allocations speculatively, evaluate the result, and undo them cleanly. The library must support saving and restoring capacity state so that search branches can be explored without corrupting shared state.

**Why this priority**: Without backtracking support, the library only serves greedy one-pass schedulers. Speculative planning unlocks the full range of optimisation approaches.

**Independent Test**: Snapshot state, commit multiple allocations, restore snapshot, verify state is identical to pre-allocation.

**Acceptance Scenarios**:

1. **Given** a resource with some allocations, **When** I snapshot the state, commit a new allocation, then restore, **Then** the capacity state is identical to the snapshot.
2. **Given** multiple allocations committed after a snapshot, **When** I restore, **Then** all allocations are undone.
3. **Given** two snapshots taken at different points, **When** I restore the earlier one, **Then** the state returns to that earlier point, not the later one.
4. **Given** a speculative allocation, **When** I decide to keep it (no restore), **Then** it persists as a committed allocation.

---

### User Story 4 — Calendar Rules and Exceptions (Priority: P1)

A developer needs to define working calendars from recurring weekly rules with date-specific exceptions. Rules define the recurring structure ("every Monday, 08:00–17:00"). Exceptions override it for specific dates ("25 Dec is not working", "this Saturday, 10:00–14:00 is working"). The calendar must handle real-world complexity including multiple periods per day and overnight rules that cross midnight.

Exceptions fall into two tiers:

- **Planned exceptions** are known before a scheduling run begins: public holidays, planned maintenance windows, pre-approved overtime. These are baked into the initial capacity state and are immutable during the run. They are part of the calendar definition.
- **Dynamic exceptions** arise during a run in response to conditions: unplanned overtime authorised because queues are too long, a machine breakdown discovered mid-schedule, an emergency maintenance window. These modify capacity state after it has been materialised.

The distinction matters for performance: planned exceptions are resolved once at calendar construction and never revisited. Dynamic exceptions must be cheap to apply mid-run without rebuilding the calendar from scratch.

**Why this priority**: Real scheduling requires real calendars. A library that only handles simple 9–5 Mon–Fri is not usable in production. And real operations have both planned and unplanned disruptions.

**Independent Test**: Define a calendar with a mix of rules and planned exceptions, query working time, verify results match hand-calculated expectations. Separately, apply a dynamic exception mid-run and verify capacity is correctly modified.

**Acceptance Scenarios**:

1. **Given** a weekly rule with a planned holiday exception on a working day, **When** I query that day, **Then** it contributes zero working time.
2. **Given** a weekly rule with a planned overtime exception on a non-working day (e.g. Saturday), **When** I query that day, **Then** the overtime period is available.
3. **Given** a rule with multiple periods per day (e.g. 06:00–10:00, 14:00–18:00), **When** I walk forward through that day, **Then** the gap between periods is non-working.
4. **Given** an overnight rule (e.g. 22:00–06:00), **When** I walk forward through midnight, **Then** the working period spans correctly across the date boundary.
5. **Given** a partial-day exception that shortens a normal working day, **When** I query that day, **Then** only the reduced hours are available.
6. **Given** a materialised capacity state, **When** a dynamic exception removes capacity (e.g. breakdown), **Then** that time window becomes unavailable and the walk routes around it.
7. **Given** a materialised capacity state, **When** a dynamic exception adds capacity (e.g. unplanned overtime), **Then** that time window becomes available to the walk.

---

### User Story 5 — Cross-Platform Test Contract (Priority: P2)

A developer porting the library to another language (TypeScript, VBA, Power Query M) needs a shared set of test fixtures with expected results. The Python implementation serves as the reference; ports validate correctness against the same fixtures.

**Why this priority**: The library is explicitly designed as a reference for porting. Without a portable test contract, ports cannot prove equivalence.

**Independent Test**: Load JSON fixtures, run all test cases, compare results to expected values.

**Acceptance Scenarios**:

1. **Given** a set of JSON test fixtures defining calendars, queries, and expected results, **When** any conforming implementation runs them, **Then** it produces identical results.
2. **Given** test fixtures covering all user stories (calendar queries, allocations, backtracking), **When** the Python implementation runs them, **Then** all pass.

---

### User Story 6 — Resolution and Performance Scaling (Priority: P2)

A developer using the library for a two-week scheduling run needs minute-level precision. A developer running a year-long simulation needs it to be fast and memory-efficient, and is willing to trade precision for performance — hour-level or half-day-level granularity may be entirely appropriate when the inputs themselves are rough estimates.

The time resolution is not just a unit conversion — it is a performance parameter that controls the tradeoff between accuracy and speed. The library must support this as a conscious, tunable choice.

**Why this priority**: Without resolution flexibility, the library is limited to short-horizon minute-grain use cases. Simulation and long-range planning are important use cases that require coarser grain.

**Independent Test**: Run the same scheduling scenario at minute grain and at hour grain. Verify both produce correct results at their respective precision, and that the coarser grain is measurably faster and uses less memory.

**Acceptance Scenarios**:

1. **Given** a resolution of one minute, **When** I materialise a one-week horizon, **Then** the capacity state contains 10,080 units.
2. **Given** a resolution of one hour, **When** I materialise the same one-week horizon, **Then** the capacity state contains 168 units and operations complete proportionally faster.
3. **Given** a resolution choice, **When** the library performs calculations, **Then** all results are consistent with that resolution — no mixed-resolution arithmetic.
4. **Given** two different resolutions applied to the same calendar and query, **When** I compare results, **Then** they agree to within one unit of the coarser resolution (bounded discretisation error).

---

### User Story 7 — Reference Scheduler (Priority: P2)

A developer or practitioner wants to see a working example of how the primitives compose into a simple greedy scheduler. This is documentation in code form — it demonstrates correct usage patterns, makes scheduling concepts concrete for learners, and shows contributors how the library is intended to be used. It is not a production scheduler.

**Why this priority**: For the practitioner and community audiences, the reference scheduler is how they first experience the library. It must exist early enough to serve as a teaching tool and an onboarding path for contributors.

**Independent Test**: Run the reference scheduler against a known dataset, verify all operations are scheduled and no capacity is double-booked.

**Acceptance Scenarios**:

1. **Given** a set of operations and resource calendars, **When** the reference scheduler runs, **Then** every operation is allocated without overlapping another on the same resource.
2. **Given** the reference scheduler's output, **When** I inspect it, **Then** each allocation is traceable to the primitives' public interface.

---

### Edge Cases

- Zero working time in a day (full holiday) — walk must skip the day entirely
- Job longer than any single working window — non-splittable job must wait for a window large enough; splittable job spans multiple windows
- Job that exactly fills a working window — no residual, next job starts at next window
- Start time falls during non-working time — walk advances to next working period
- Start time falls in the middle of a working period — walk begins from that point, not the period start
- Empty calendar (no working time at all) — must signal infeasibility, not loop forever
- Deallocating something on the wrong resource — must reject
- Splittable job with fragments smaller than minimum quantum — fragments below the quantum are skipped
- Overnight shift ending exactly at midnight — boundary handling
- Multiple exceptions on the same date (e.g. holiday override + overtime window) — must resolve correctly
- Dynamic exception applied to time that already has an allocation — library detects and reports which allocation records are affected; caller decides how to handle (e.g. deallocate and reschedule)
- Dynamic exception or walk beyond the initial horizon — capacity state auto-extends by materialising more calendar time on demand
- Coarse resolution (e.g. hourly) where a working period does not align to unit boundaries — strict rejection; caller must ensure calendar times align to the chosen resolution
- Year-long horizon at minute grain — must remain feasible in memory and performance
- Wrong input types (float for int, string for datetime, date for datetime) — must reject with actionable error message, never silently convert

## Requirements *(mandatory)*

### Functional Requirements

**Calendar Time Arithmetic**

- **FR-001**: The library MUST compute a finish datetime given a start datetime and a duration in working time units (forward walk).
- **FR-002**: The library MUST compute a start datetime given a finish datetime and a duration in working time units (backward walk).
- **FR-003**: The library MUST count the working time between any two datetimes.
- **FR-004**: The library MUST enumerate the individual working intervals within a datetime range.
- **FR-005**: Forward walk then backward walk with the same duration MUST return the original datetime (round-trip consistency).

**Calendar Definition**

- **FR-006**: The library MUST support recurring weekly rules with multiple periods per day.
- **FR-007**: The library MUST support planned exceptions (known before a run) that add working time (overtime) or remove it (holidays, partial days). Planned exceptions are part of the calendar definition and are immutable once the capacity state is materialised.
- **FR-008**: The library MUST support overnight rules that cross midnight.
- **FR-009**: Calendar queries MUST NOT require a pre-specified planning horizon. Arbitrarily long durations must be computable on demand.

**Dynamic Exceptions**

- **FR-027**: The library MUST support dynamic exceptions that remove capacity from a materialised capacity state mid-run (e.g. unplanned breakdown, emergency maintenance).
- **FR-028**: The library MUST support dynamic exceptions that add capacity to a materialised capacity state mid-run (e.g. unplanned overtime authorised in response to load).
- **FR-029**: Dynamic exceptions MUST NOT require rebuilding the capacity state from the calendar. They MUST be applicable as cheap mutations to the existing state.
- **FR-033**: When a dynamic exception removes capacity that overlaps an existing allocation, the library MUST detect the conflict and report which allocation records are affected. The library MUST NOT automatically resolve the conflict — that is a policy decision for the caller.

**Capacity Tracking**

- **FR-010**: The library MUST materialise a working calendar into a capacity representation suitable for allocation queries. The initial materialisation covers an estimated horizon; the capacity state MUST auto-extend by materialising more calendar time on demand when a walk or dynamic exception reaches beyond it.
- **FR-011**: The library MUST find the earliest position where a given amount of work fits, respecting already-committed allocations.
- **FR-012**: Non-splittable work MUST require a single contiguous free window. If no window is large enough, it waits for the next one.
- **FR-013**: Splittable work MUST consume free time greedily across gaps until the required amount is fulfilled.
- **FR-014**: Splittable work MUST support a configurable minimum fragment size. Fragments below this threshold are skipped.
- **FR-015**: The library MUST support committing an allocation (marking capacity as occupied).
- **FR-016**: The library MUST support releasing a committed allocation (restoring capacity to free). Release MUST be the exact inverse of commit — no residual drift.
- **FR-017**: The library MUST support deadlines. If work cannot complete before the deadline, the library MUST signal infeasibility.

**Backtracking**

- **FR-018**: The library MUST support snapshotting capacity state.
- **FR-019**: The library MUST support restoring to a previously saved snapshot, undoing all allocations made since that snapshot.

**Boundary Conversion and Resolution**

- **FR-020**: The library MUST convert between datetime and integer time at a configurable resolution (e.g. minutes, hours, 5-minute blocks).
- **FR-021**: Cross-layer consistency: a datetime-based forward walk and an integer-based capacity walk MUST produce identical finish times for the same inputs at a given resolution.
- **FR-030**: The resolution MUST be a conscious performance parameter. Coarser resolution MUST result in smaller capacity state and faster calculations.
- **FR-031**: Discretisation error MUST be bounded: results at any resolution MUST be accurate to within one unit of that resolution.
- **FR-032**: The library MUST NOT mix resolutions within a single capacity state. All calculations against a given capacity state use the resolution it was materialised with.
- **FR-034**: The boundary conversion MUST reject datetimes that do not align to the chosen resolution. No implicit rounding. The caller is responsible for ensuring calendar times align to the resolution before materialisation.
- **FR-035**: The library MUST reject timezone-aware datetimes (datetimes with tzinfo) at the public API boundary. All datetimes are naive and assumed to be in the facility's local time. Time zone conversion is the caller's responsibility.

**Input Validation**

- **FR-036**: The library MUST validate all inputs at the public API boundary with strong type and value checks. Invalid inputs MUST raise `TypeError` or `ValueError` with actionable error messages that name the parameter, state what was expected, and show what was received. The library MUST NOT perform implicit conversion from incorrect types (e.g. float to int, string to datetime, aware to naive datetime). If the type is wrong, it is an error — not an invitation to guess.
- **FR-037**: Calendar rule validation MUST reject overlapping periods within the same day (after overnight splitting), invalid time formats, and weekday keys outside 0–6.
- **FR-038**: Exception validation MUST reject invalid date formats, invalid time formats, and logically inconsistent entries (e.g. is_working=True with no time range).
- **FR-039**: Integer parameters (`work_units`, `earliest_start`, `min_split`, `deadline`) MUST be non-negative integers. Floats MUST be rejected, not truncated.

**Slot-Finding vs Committing**

- **FR-022**: Finding a slot MUST be a read-only operation. It MUST NOT alter capacity state. Committing is a separate explicit action.

**Visual Verification**

- **FR-023**: The library MUST provide human-readable ASCII representations of calendar state and capacity state for development-time verification.

**Reference Scheduler**

- **FR-024**: The library MUST include a greedy reference scheduler that demonstrates correct composition of the primitives. It is labelled as a reference, not a production scheduler.

**Portability**

- **FR-025**: The core of the library MUST have zero external dependencies (standard library only).
- **FR-026**: Test fixtures MUST be stored as JSON and serve as the cross-platform validation contract.

### Key Entities

- **Working Calendar**: A named availability pattern composed of recurring weekly rules and date-specific exceptions. Answers time queries without knowing how the time will be used.
- **Capacity State**: The occupied/available state for one resource over a planning horizon. Materialised from a Working Calendar with an initial estimated horizon, but auto-extends on demand when walks or exceptions reach beyond it. Reflects both calendar structure (non-working time) and committed allocations.
- **Allocation Record**: An immutable record of a committed (or candidate) allocation. Contains the resource, the time window(s) consumed, and the amount of work fulfilled. Self-contained — the capacity state can be updated from this record alone.
- **Time Resolution**: The configurable unit that gives meaning to integer time values (e.g. 1 unit = 1 minute). Set at the boundary between datetime and integer domains. Acts as a performance parameter: coarser resolution trades precision for speed and memory efficiency.
- **Dynamic Exception**: A mid-run modification to capacity state — either removing capacity (breakdown, emergency maintenance) or adding it (unplanned overtime). Applied as a mutation to an already-materialised capacity state, without rebuilding from the calendar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five canonical test datasets (simple week, multi-shift, overnight, resource variety, stress) pass all acceptance scenarios with zero failures.
- **SC-002**: Forward-then-backward round-trip consistency holds for all tested combinations of calendar patterns, start points, and durations.
- **SC-003**: Cross-layer consistency holds: datetime-based calendar queries and integer-based capacity queries produce identical results for matched inputs across all test datasets.
- **SC-004**: Commit-then-release round-trip restores capacity state to bit-identical pre-commit state for all tested allocations.
- **SC-005**: The library has zero external dependencies in its core. Only the standard library is imported.
- **SC-006**: A developer unfamiliar with the library can run the reference scheduler against a test dataset and understand the output within 15 minutes, using only the reference scheduler code and ASCII visualisation as documentation.
- **SC-007**: Every public function has at least three distinct test cases, plus property-based tests for core algorithm functions as identified during planning.
- **SC-008**: All data structures that manipulate time intervals or capacity state have corresponding ASCII visualisation functions, and these have been reviewed before the implementation is marked complete.
- **SC-009**: A practitioner with Excel-level scheduling experience can follow the reference scheduler's execution through ASCII output and understand what happened and why, without reading the library internals.
- **SC-010**: The codebase is structured and documented well enough that a new contributor can find, understand, and modify a single component (e.g. add a new calendar exception type) with no guidance beyond the code, tests, and spec.

## Assumptions

- The library has three audiences (developers, practitioners, community) as defined in Purpose. Design decisions should serve all three.
- The default time resolution is minutes, suitable for short-horizon scheduling (1–4 weeks). Coarser resolutions (hours, half-days) are expected for long-horizon simulation (months to years). The resolution choice is the caller's responsibility.
- A single resource's capacity state fits comfortably in memory for typical horizons. At minute grain: ~10 KB per resource-week. At hour grain: ~170 bytes per resource-week. Auto-extension means the horizon grows as needed; memory is proportional to the time range actually touched, not a pre-specified maximum.
- The five canonical test datasets provide sufficient coverage of real-world calendar patterns. Additional datasets may be added but these five are the baseline.
- The greedy reference scheduler is intentionally simple. It exists to demonstrate the API and teach scheduling concepts, not to produce optimal schedules.
- Practitioners coming from Excel will read the reference scheduler and ASCII output before they read the API. These are the front door.
- All datetimes are naive (no tzinfo) and represent facility local time. The library is time-zone-agnostic. Cross-timezone coordination in global supply chain or network simulation scenarios is handled by the orchestration layer above this library.

## Scope Exclusions

Per the constitution (Section 6), the following are permanently out of scope for this library:

- Dispatch rules, resource selection policy, optimisation algorithms
- Discrete event simulation
- ERP integration or data connectors
- Multi-resource constraint resolution
