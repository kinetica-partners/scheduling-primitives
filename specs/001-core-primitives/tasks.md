# Tasks: Core Scheduling Primitives

**Input**: Design documents from `specs/001-core-primitives/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: TDD is mandated by the constitution (§5). Tests are written first and must fail before implementation.

**Organization**: Tasks are grouped by user story. US4 (Calendar Rules and Exceptions) is split: planned exceptions build the calendar definition (Phase 3), dynamic exceptions require the bitmap (Phase 7).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project structure, packaging, shared test infrastructure

- [x] T001 Create project structure: `pyproject.toml`, `src/scheduling_primitives/__init__.py`, `tests/`, `data/fixtures/` per plan.md layout
- [x] T002 Configure pyproject.toml with UV, pytest, Hypothesis dependencies, zero runtime dependencies, and `scheduling-primitives` package metadata
- [x] T003 [P] Create `data/fixtures/simple.json` — the first canonical dataset: Mon–Fri 08:00–17:00, Tuesday holiday, Saturday overtime 10:00–14:00
- [x] T004 [P] Create `tests/conftest.py` with shared fixture loading from `data/fixtures/`, calendar construction helpers, and epoch/resolution defaults

**Checkpoint**: `uv run pytest` runs (0 tests collected, no errors)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types and boundary conversion that all layers depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests

- [x] T005 [P] Write tests for AllocationRecord and InfeasibleError in `tests/test_types.py` — invariants (span sum == work_units, wall_time, is_complete), construction, frozen dataclass behaviour. ≥3 cases each.
- [x] T006 [P] Write tests for TimeResolution in `tests/test_resolution.py` — to_int/to_datetime round-trip, alignment rejection (misaligned datetime raises ValueError), MINUTE and HOUR predefined instances. ≥3 cases each.

### Implementation

- [x] T007 [P] Implement AllocationRecord and InfeasibleError in `src/scheduling_primitives/types.py`
- [x] T008 [P] Implement TimeResolution with to_int, to_datetime, MINUTE, HOUR in `src/scheduling_primitives/resolution.py`
- [x] T009 Verify all Phase 2 tests pass. Run `uv run pytest tests/test_types.py tests/test_resolution.py -v`

**Checkpoint**: Foundation ready — shared types and boundary conversion working

---

## Phase 3: US4 — Calendar Rules and Planned Exceptions (Priority: P1)

**Goal**: Build the calendar definition layer — rules, planned exceptions, day-period resolution. This is the foundation that all calendar time arithmetic depends on.

**Independent Test**: Given rules and exceptions, verify that `periods_for_date()` returns the correct working periods for any date.

### Tests

- [x] T010 [P] [US4] Write tests for basic weekly rules in `tests/test_calendar_rules.py` — single-period day, multi-period day (split shift), non-working day (no rule). ≥3 cases each.
- [x] T011 [P] [US4] Write tests for overnight rules in `tests/test_calendar_rules.py` — rule with end_time < start_time, midnight boundary splitting, next-day carryover.
- [x] T012 [P] [US4] Write tests for planned exceptions in `tests/test_calendar_exceptions.py` — full-day holiday, overtime on non-working day, partial-day exception, multiple exceptions on same date.

### Implementation

- [x] T013 [US4] Implement WorkingCalendar constructor and `_periods_for_date()` with basic weekly rule resolution in `src/scheduling_primitives/calendar.py`
- [x] T014 [US4] Implement overnight rule splitting in `_periods_for_date()` — detect end_time < start_time, split into same-day and next-day intervals in `src/scheduling_primitives/calendar.py`
- [x] T015 [US4] Implement planned exception resolution in `_periods_for_date()` — holiday removal, overtime addition, partial-day modification in `src/scheduling_primitives/calendar.py`
- [x] T016 [US4] Implement `show_calendar()` in `src/scheduling_primitives/debug.py` — ASCII calendar view showing working/non-working periods for a date range. Print and visually verify against `simple.json` dataset.
- [x] T017 [US4] Verify all Phase 3 tests pass. Run `uv run pytest tests/test_calendar_rules.py tests/test_calendar_exceptions.py -v`

**Checkpoint**: Calendar definition working — rules, overnight, holidays, overtime, partial days all resolve correctly. Visual verification reviewed.

---

## Phase 4: US1 — Calendar Time Arithmetic (Priority: P1) 🎯 MVP

**Goal**: Forward walk, backward walk, working time counting, and interval enumeration on top of the calendar definition.

**Independent Test**: Given a calendar with holidays, walk forward 60 minutes from Monday 16:30 → should land on Wednesday. Walk backward from the result → should return to the start.

### Tests

- [x] T018 [P] [US1] Write tests for forward walk (`add_minutes`) in `tests/test_calendar.py` — simple within-day, across holiday, across weekend, start in non-working time, start mid-period. ≥3 cases.
- [x] T019 [P] [US1] Write tests for backward walk (`subtract_minutes`) in `tests/test_calendar.py` — simple within-day, across holiday, end in non-working time. ≥3 cases.
- [x] T020 [P] [US1] Write tests for `working_minutes_between` and `working_intervals_in_range` in `tests/test_calendar.py` — span with holiday, single-day, multi-day. ≥3 cases each.
- [x] T021 [P] [US1] Write round-trip consistency test in `tests/test_calendar.py` — `add_minutes(subtract_minutes(dt, n), n) == dt` for multiple (dt, n) pairs.

### Implementation

- [x] T022 [US1] Implement `add_minutes()` (forward walk) in `src/scheduling_primitives/calendar.py`
- [x] T023 [US1] Implement `subtract_minutes()` (backward walk) in `src/scheduling_primitives/calendar.py`
- [x] T024 [US1] Implement `working_minutes_between()` in `src/scheduling_primitives/calendar.py`
- [x] T025 [US1] Implement `working_intervals_in_range()` as a generator in `src/scheduling_primitives/calendar.py`
- [x] T026 [US1] Verify all Phase 4 tests pass including round-trip consistency. Run `uv run pytest tests/test_calendar.py -v`

**Checkpoint**: Calendar layer complete (Layer 1). Forward/backward walks, counting, interval enumeration all working. Round-trip consistency verified. This is the MVP — developers can compute schedule dates.

---

## Phase 5: US2 — Capacity Tracking and Allocation (Priority: P1)

**Goal**: Materialise calendars into bitmaps, find slots (non-splittable and splittable), commit and release allocations. This is finite capacity scheduling.

**Independent Test**: Materialise a calendar, allocate a 120-minute non-splittable job, verify bits are occupied. Allocate a 60-minute splittable job that spans a shift boundary, verify two spans. Deallocate, verify bits restored.

### Tests

- [x] T027 [P] [US2] Write tests for `OccupancyBitmap.from_calendar()` in `tests/test_occupancy.py` — bitmap size matches horizon, free bits match working time, non-working bits are zero. ≥3 cases.
- [x] T028 [P] [US2] Write tests for non-splittable walk in `tests/test_walk.py` — fits in window, must skip to next window, deadline exceeded (InfeasibleError). ≥3 cases.
- [x] T029 [P] [US2] Write tests for splittable walk in `tests/test_walk.py` — spans shift boundary, min_split skips small fragments, fits in single span. ≥3 cases.
- [x] T030 [P] [US2] Write tests for allocate/deallocate in `tests/test_allocate.py` — bits marked after allocate, bits restored after deallocate, two sequential allocates on same resource, deallocate wrong resource raises ValueError. ≥3 cases.

### Implementation

- [x] T031 [US2] Implement `OccupancyBitmap.from_calendar()` in `src/scheduling_primitives/occupancy.py` — materialise calendar intervals into bytearray, retain calendar reference for auto-extension
- [x] T032 [US2] Implement `walk()` (non-splittable) in `src/scheduling_primitives/occupancy.py` — scan for contiguous free run ≥ work_units, skip shorter runs
- [x] T033 [US2] Implement `walk()` (splittable) in `src/scheduling_primitives/occupancy.py` — greedy consumption across gaps, min_split threshold, deadline check
- [x] T034 [US2] Implement `allocate()`, `deallocate()`, `_mark_spans()` in `src/scheduling_primitives/occupancy.py` — allocate calls walk then marks bits; deallocate restores bits
- [x] T035 [US2] Implement auto-extension in `src/scheduling_primitives/occupancy.py` — when walk reaches horizon_end, extend bitmap by materialising more calendar time
- [x] T036 [P] [US2] Write tests for auto-extension in `tests/test_auto_extend.py` — walk beyond initial horizon triggers extension, extended bitmap is consistent
- [x] T037 [US2] Implement `show_bitmap()` in `src/scheduling_primitives/debug.py` — ASCII bitmap view with allocation labels, non-working markers, free capacity. Print and visually verify.
- [x] T038 [US2] Verify all Phase 5 tests pass. Run `uv run pytest tests/test_occupancy.py tests/test_walk.py tests/test_allocate.py tests/test_auto_extend.py -v`

**Checkpoint**: Both layers working. Calendar queries and capacity tracking operational. Non-splittable and splittable allocation verified. Visual verification reviewed.

---

## Phase 6: US3 — Speculative Planning and Backtracking (Priority: P2)

**Goal**: Snapshot and restore capacity state for branch-and-bound and similar search patterns.

**Independent Test**: Snapshot, allocate 3 operations, restore, verify bitmap identical to pre-allocation.

### Tests

- [x] T039 [P] [US3] Write tests for checkpoint/restore in `tests/test_checkpoint.py` — single allocation undo, multiple allocations undo, restore to earlier of two snapshots, keep allocation (no restore). ≥3 cases.
- [x] T040 [P] [US3] Write tests for copy in `tests/test_checkpoint.py` — deep copy independence, mutations to copy don't affect original.

### Implementation

- [x] T041 [US3] Implement `checkpoint()`, `restore()`, and `copy()` on OccupancyBitmap in `src/scheduling_primitives/occupancy.py`
- [x] T042 [US3] Verify all Phase 6 tests pass. Run `uv run pytest tests/test_checkpoint.py -v`

**Checkpoint**: Backtracking support complete. B&B and search algorithms can now use the library.

---

## Phase 7: US4 Dynamic Exceptions (Priority: P1)

**Goal**: Apply dynamic exceptions (breakdowns, unplanned overtime) to a materialised bitmap mid-run. Detect and report conflicts with existing allocations.

**Independent Test**: Allocate an operation, then apply a breakdown that overlaps it. Verify the affected allocation is reported. Apply unplanned overtime on a non-working window, verify it becomes available.

### Tests

- [x] T043 [P] [US4] Write tests for dynamic capacity removal in `tests/test_dynamic.py` — breakdown on free time, breakdown overlapping an allocation (conflict detection reports affected records). ≥3 cases.
- [x] T044 [P] [US4] Write tests for dynamic capacity addition in `tests/test_dynamic.py` — overtime on non-working window makes it available, overtime within existing working time (no-op). ≥3 cases.

### Implementation

- [x] T045 [US4] Implement `_allocations` index on OccupancyBitmap — append AllocationRecord on allocate, remove on deallocate, in `src/scheduling_primitives/occupancy.py`
- [x] T046 [US4] Implement `apply_dynamic_exception()` in `src/scheduling_primitives/occupancy.py` — is_working=False removes capacity and detects conflicts; is_working=True adds capacity
- [x] T047 [US4] Verify all Phase 7 tests pass. Run `uv run pytest tests/test_dynamic.py -v`

**Checkpoint**: Full US4 complete — planned exceptions in calendar layer, dynamic exceptions in capacity layer. Conflict detection working.

---

## Phase 8: US6 — Resolution and Performance Scaling (Priority: P2)

**Goal**: Verify the library works correctly at different resolutions and that coarser grain is proportionally smaller and faster.

**Independent Test**: Run the same scenario at minute grain and hour grain. Verify both produce correct results, hour grain bitmap is ~60x smaller.

### Tests

- [x] T048 [P] [US6] Write tests for multi-resolution in `tests/test_resolution.py` — minute-grain bitmap size, hour-grain bitmap size, results agree within one unit of coarser resolution. ≥3 cases.
- [x] T049 [P] [US6] Write tests for alignment rejection in `tests/test_resolution.py` — non-aligned datetime at hour grain raises ValueError, aligned datetime succeeds.
- [x] T050 [P] [US6] Write cross-layer consistency tests in `tests/test_consistency.py` — `resolution.to_datetime(record.finish, epoch) == calendar.add_minutes(start, work_units)` for multiple (pattern, start, work_units) combinations at both minute and hour grain.

### Implementation

- [x] T051 [US6] Verify multi-resolution tests pass with existing TimeResolution and OccupancyBitmap implementation (no new code expected — resolution is already parameterised). Fix any issues.
- [x] T052 [US6] Verify cross-layer consistency tests pass. Fix any discrepancies between Layer 1 and Layer 2.
- [x] T053 [US6] Run `uv run pytest tests/test_resolution.py tests/test_consistency.py -v`

**Checkpoint**: Library verified at multiple resolutions. Cross-layer consistency proven.

---

## Phase 9: US7 — Reference Scheduler (Priority: P2)

**Goal**: A simple greedy scheduler that demonstrates correct composition of the primitives. Documentation in code form.

**Independent Test**: Run the greedy scheduler against the simple dataset. Verify all operations scheduled, no double-booking.

### Tests

- [x] T054 [P] [US7] Write tests for greedy scheduler in `tests/test_greedy.py` — schedules all operations, no overlapping allocations on same resource, handles splittable and non-splittable jobs.

### Implementation

- [x] T055 [US7] Implement `greedy_schedule()` in `src/scheduling_primitives/greedy.py` — iterate operations in order, allocate each to earliest available slot on its assigned resource
- [x] T056 [US7] Implement `show_multi_resource()` in `src/scheduling_primitives/debug.py` — ASCII multi-resource view. Print and visually verify against greedy scheduler output.
- [x] T057 [US7] Verify all Phase 9 tests pass. Run `uv run pytest tests/test_greedy.py -v`

**Checkpoint**: Reference scheduler working. Practitioner-facing demonstration complete. Visual verification reviewed.

---

## Phase 10: US5 — Cross-Platform Test Contract (Priority: P2)

**Goal**: JSON test fixtures as the portable validation contract for any future language port.

**Independent Test**: Load all 5 canonical datasets from JSON, run fixture-driven tests, all pass.

### Tests and Fixtures

- [x] T058 [P] [US5] Create `data/fixtures/multi_shift.json` — two-shift pattern (06:00–14:00, 14:00–22:00)
- [x] T059 [P] [US5] Create `data/fixtures/overnight.json` — night shift (22:00–06:00)
- [x] T060 [P] [US5] Create `data/fixtures/resource_variety.json` — multiple resources with different patterns
- [x] T061 [P] [US5] Create `data/fixtures/stress.json` — large dataset for performance validation
- [x] T062 [US5] Create `data/datapackage.json` — Frictionless Data Package descriptor for all fixtures
- [x] T063 [US5] Write fixture-driven parametric tests in `tests/conftest.py` and `tests/test_fixtures.py` — load each JSON fixture, run calendar queries and allocation scenarios, compare to expected results embedded in fixture

### Implementation

- [x] T064 [US5] Embed expected results (forward walk finish times, working minutes counts, allocation spans) in each JSON fixture
- [x] T065 [US5] Verify all fixture-driven tests pass across all 5 datasets. Run `uv run pytest tests/test_fixtures.py -v`

**Checkpoint**: All 5 canonical datasets passing. Cross-platform test contract ready for ports.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Property-based tests, public API exports, validation, data loading, final verification

- [x] T066 [P] Write Hypothesis property-based tests in `tests/test_properties.py` — round-trip (add/subtract), allocate/deallocate inverse, to_int/to_datetime round-trip, monotonicity of walk, span sum invariant
- [x] T067 [P] Implement input validation in `src/scheduling_primitives/schema.py` — validate rules (non-overlapping periods, valid times), validate exceptions (valid dates, valid is_working)
- [x] T068 [P] Implement JSON/CSV loader in `src/scheduling_primitives/loaders.py` — load from JSON (stdlib), optional Polars DataFrame integration
- [x] T069 Update `src/scheduling_primitives/__init__.py` — export public API: WorkingCalendar, OccupancyBitmap, AllocationRecord, TimeResolution, MINUTE, HOUR, walk, allocate, deallocate, apply_dynamic_exception, InfeasibleError, greedy_schedule
- [x] T070 Run full test suite: `uv run pytest -v` — all tests pass
- [x] T071 Validate quickstart.md examples against actual library — run each code snippet, verify output matches
- [x] T072 Final visual verification: run `show_calendar`, `show_bitmap`, `show_multi_resource` against all 5 datasets, review ASCII output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US4 Planned)**: Depends on Phase 2
- **Phase 4 (US1)**: Depends on Phase 3 (calendar definition must exist)
- **Phase 5 (US2)**: Depends on Phase 4 (needs calendar + resolution)
- **Phase 6 (US3)**: Depends on Phase 5 (needs allocation to snapshot)
- **Phase 7 (US4 Dynamic)**: Depends on Phase 5 (needs bitmap for dynamic exceptions)
- **Phase 8 (US6)**: Depends on Phase 5 (needs bitmap at different resolutions)
- **Phase 9 (US7)**: Depends on Phase 5 (needs full primitive stack)
- **Phase 10 (US5)**: Depends on Phases 3–9 (needs implementations to generate fixtures)
- **Phase 11 (Polish)**: Depends on all previous phases

### User Story Dependencies

```
US4 (planned) ──▶ US1 ──▶ US2 ──┬──▶ US3
                                 ├──▶ US4 (dynamic)
                                 ├──▶ US6
                                 └──▶ US7
                                         └──▶ US5
```

- **US4 planned → US1**: Calendar definition must exist before time arithmetic
- **US1 → US2**: Calendar queries needed for bitmap materialisation
- **US2 → US3, US4 dynamic, US6, US7**: These are all parallel once allocation works
- **All → US5**: Test contract needs all implementations

### Parallel Opportunities

After Phase 5 (US2) completes, the following can run in parallel:
- **US3** (backtracking) — separate module concerns
- **US4 dynamic** (dynamic exceptions) — separate from backtracking
- **US6** (resolution scaling) — tests against existing code
- **US7** (reference scheduler) — separate module

Within each phase, tasks marked [P] can run in parallel.

---

## Parallel Example: Phase 5 (US2)

```bash
# Launch all test tasks in parallel (different test files):
T027: tests for from_calendar in tests/test_occupancy.py
T028: tests for non-splittable walk in tests/test_walk.py
T029: tests for splittable walk in tests/test_walk.py
T030: tests for allocate/deallocate in tests/test_allocate.py

# Then implementation sequentially (same file, dependent):
T031: from_calendar → T032: walk (non-split) → T033: walk (split) → T034: allocate/deallocate → T035: auto-extend
```

---

## Implementation Strategy

### MVP First (Phases 1–4: Setup + Foundation + US4 Planned + US1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational types + resolution
3. Complete Phase 3: Calendar rules and planned exceptions
4. Complete Phase 4: Calendar time arithmetic
5. **STOP and VALIDATE**: Forward/backward walk, round-trip consistency, visual verification
6. At this point the library delivers immediate value — schedule date computation

### Core Complete (Add Phase 5: US2)

7. Complete Phase 5: Capacity tracking and allocation
8. **STOP and VALIDATE**: Finite capacity scheduling working — this is the minimum viable library

### Full Library (Add Phases 6–10)

9. Phases 6–9 can proceed in priority order or in parallel
10. Phase 10 extracts the test contract
11. Phase 11 polishes

---

## Notes

- Constitution mandates TDD: write tests first, verify they fail, then implement
- Constitution mandates visual verification: `show_` functions must be implemented and output reviewed before marking a data structure task complete
- Constitution autonomy: core algorithm work (walk, bitmap) = one task at a time with visual verification. Calendar rule resolution = may complete full task cycles with tests as feedback.
- [P] tasks = different files, no dependencies — can run in parallel
- [US*] label maps task to spec user story for traceability
