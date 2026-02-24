# Constitution: scheduling-primitives

**Version**: 1.0.0  
**Ratified**: 2026-02-23

---

## 1. Project Identity

**scheduling-primitives** is an open source Python library (MIT licence) providing the mechanical foundations for finite capacity scheduling: working calendars, occupancy state, and time arithmetic.

It is a substrate. It does not dispatch, optimise, simulate, or integrate with ERPs. Those concerns belong in libraries that import this one.

The library ships with a greedy reference scheduler that demonstrates correct use of the primitives. This is documentation in code form, not a production scheduler.

---

## 2. Planning Hierarchy

This project uses a flat three-level cascade. Vision and Epic levels are not used — the project scope is sufficiently bounded that a single spec governs all work.

```
Constitution    Project-wide principles and constraints (this document)
  Spec          What the library does — requirements and acceptance criteria
  Plan          How we will build it — phases and sequencing
  Tasks         Individual work items with acceptance criteria
  Retrospective What we learned (written after each phase)
```

**Locations**:

```
specs/
  constitution.md          ← this document
  spec.md                  ← current active specification
  plan.md                  ← current execution plan
  tasks.md                 ← current task list
  backlog.md               ← future work not yet in scope
  retrospectives/
    retro-{phase}.md
  archive/
    spec-v{N}.md           ← superseded specs, kept for reference
```

Rules:
- A task must trace to a spec requirement. If no requirement exists, update the spec first.
- The spec is the source of truth for scope. Not this conversation. Not the v2 design document. Not implementation assumptions.
- If a task reveals that the spec is wrong, update the spec explicitly before continuing. Do not silently work around it.

---

## 3. Terminology

This library uses practitioner-facing names for parameters and variables. Where these differ from the scheduling theory literature, the mapping is recorded here.

| This library | Scheduling theory | Notes |
|---|---|---|
| `allow_split = False` | Non-preemptive | Operation must run continuously once started. Cannot be interrupted. |
| `allow_split = True` | Preemptive | Operation may be interrupted and resumed. Consumes available runs greedily across gaps. |
| `work_units` | Processing time (pⱼ) | Integer count of time units required. |
| `earliest_start` | Release date (rⱼ) | First time unit the operation may begin. |
| `deadline` | Due date / deadline (dⱼ) | Last time unit by which the operation must finish. |
| `OccupancyBitmap` | Schedule / resource timeline | The committed allocation state for one resource. |
| `AllocationRecord` | Job interval | The assigned time window(s) for one operation on one resource. |

**On preemptive vs allow_split**: The theoretical term "preemptive" is preferred in documentation, comments, and any writing aimed at an OR or academic audience. The parameter name `allow_split` is used in code because it reads naturally to practitioners without requiring a definition. Both refer to the same concept. When in doubt about which to use: code uses `allow_split`, prose uses preemptive/non-preemptive with `allow_split` in parentheses on first use.

**Theoretical significance of the distinction**: For many classical scheduling objectives, the optimal preemptive schedule is solvable in polynomial time while the optimal non-preemptive schedule is NP-hard. Preemptive EDF (Earliest Deadline First) is optimal for minimising maximum lateness on a single machine. The `allow_split` flag therefore determines not just the shape of the allocation but which theoretical results apply to the problem being solved.

---

## 4. Design Principles

These are standing constraints. They apply to every spec, every implementation decision, and every review. Amending them requires an explicit rationale and a constitution version increment.

### I. Boundary Rule

**A layer's responsibility ends where a different kind of knowledge begins.**

Two boundaries are defined and must be maintained:

**The datetime boundary** sits at `OccupancyBitmap.from_calendar()`. Above it: shift patterns, exception dates, weekday rules, overnight periods — all resolved using Python datetime objects. Below it: integer arithmetic on a bytearray. After `from_calendar()` completes, no datetime object crosses into the engine.

**The primitives boundary** sits between mechanical slot-finding and policy decisions. The library answers: does this allocation fit, and if so, where? It does not answer: which operation goes next, or which resource to prefer. Those are policy questions requiring business knowledge the library does not have.

### II. Integer Time

All internal time values are integers. The time unit is a parameter (`TimeResolution`), set once at the boundary. Default is one minute. The engine is agnostic to what a unit means.

Floats do not cross the datetime boundary. If a float appears in engine code it is a bug.

Rationale: Integer arithmetic is exact, associative, and platform-independent. Discretisation error is bounded by one unit — smaller than the uncertainty in any realistic scheduling input. Deterministic optimisation exhausts computational budget before discretisation precision becomes the binding constraint.

### III. Half-Open Intervals

All intervals are `[begin, end)` — begin inclusive, end exclusive. Length is always `end - begin`. Adjacent intervals tile without overlap. This is consistent with Python's `range()`, slicing, and `bisect`. Closed intervals `[begin, end]` are not used anywhere in the engine.

### IV. Walk Does Not Mutate

`walk()` is read-only. It finds a candidate allocation but does not commit it. `allocate()` commits. This separation allows speculative inspection of candidates before branching, which is the B&B pattern.

### V. allow_split Is a Job Property

Whether an operation can split across non-contiguous working windows is a property of the operation, not the calendar or resource. Non-splittable operations wait for a contiguous run long enough to fit. Splittable operations consume greedily across gaps.

### VI. Visual Verification Is Not Optional

Automated tests are necessary but not sufficient. For any implementation that manipulates time intervals, bitmap state, or allocation spans: a human-readable ASCII representation must be printable to stdout and must be reviewed before that implementation is marked complete.

This is not a nice-to-have. It exists because subtle errors in interval arithmetic are invisible to tests that only check return values.

---

## 4. Visual Verification Protocol

This section defines how visual verification is done in practice, specifically for Claude Code sessions in the terminal.

### Principle

Every non-trivial data structure in this library has a natural visual representation. These representations should be first-class outputs during development, not afterthoughts.

### Symbol Legend

Three states, three symbols. They are never mixed or reused.

```
░   non-working    Calendar layer — immutable. Defined by shift rules and
                   exceptions. Cannot be allocated. The bitmap pre-occupies
                   these cells at construction. The walk never touches them.

·   available      Working time not yet committed. Each · is one display
                   quantum of free capacity. A run of ··· is that many
                   consecutive free units — the walk can consume any or all
                   of them.

A─Z  allocated     Allocation layer — mutable. Each letter identifies one
                   operation. A solid block (AAAA) is a non-preemptive
                   allocation. The same letter in two separate runs (AA···AA)
                   is a preemptive (allow_split=True) allocation whose spans
                   are non-contiguous, with genuinely free time between them.
```

**Scale**: One display character represents N time units, chosen to keep rows under 50 characters. The scale is stated in the header of every diagram.

### ASCII Representations Required

**WorkingCalendar — calendar layer only, no allocations**:

```
pattern: standard_day | week of 2025-01-06 | scale: 1 char = 30 min
         00    04    08    12    16    20    24
Mon 06   ░░░░░░░░·················░░░░░░░░░░░░  480 min
Tue 07   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0 min  (holiday)
Wed 08   ░░░░░░░░·······░░░░░░░░░░░░░░░░░░░░░░  180 min  (partial)
Thu 09   ░░░░░░░░·················░░░░░░░░░░░░  480 min
Fri 10   ░░░░░░░░·················░░░░░░░░░░░░  480 min
Sat 11   ░░░░░░░░░░░░·······░░░░░░░░░░░░░░░░░░  240 min  (overtime)
Total: 1860 working minutes
```

Every · is available. Every ░ is structurally unavailable regardless of what is allocated.

**OccupancyBitmap — both layers together**:

```
resource: LATHE-1 | Mon─Wed 2025-01-06 | scale: 1 char = 10 min
          08  09  10  11  12  13  14  15  16  17
Mon 06    ░░░AAAAAAAAAA···············BBBBBBB░░░
Tue 07    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (holiday — all ░)
Wed 08    BBBBB·······························░░░

A = MILL-004   non-preemptive   Mon 09:00─10:40   work=100 units
B = TURN-011   preemptive       Mon 16:00─17:00 + Wed 09:00─09:40
               span 1: Mon 16:00─17:00  (60 units)
               span 2: Wed 09:00─09:40  (40 units)
               total work: 100 units   wall time: spans 3 calendar days
···  = free working time (available to the walk)
░░░  = non-working (calendar layer — walk cannot enter)
```

Reading Mon: ░░░ is pre-shift non-working. A runs solid (non-preemptive). ··· is free capacity. B starts near the end of the shift and hits the ░ boundary before finishing — the shift ends with work remaining.

Reading Tue: entirely ░ — a holiday. The walk skips this day entirely.

Reading Wed: B resumes immediately at shift start and finishes after 40 units, leaving ··· free for the rest of the day.

The gap between B's two spans is ░ throughout — non-working time, not free time. This is why a preemptive split exists: the walk hit a hard calendar boundary before the work was complete. There is no case where a preemptive operation has · between its spans — if there were free working time available the greedy walk would have consumed it rather than splitting.

**Multi-resource view — resource pool selection**:

```
work centre: LATHE | Mon 2025-01-06 | scale: 1 char = 10 min
             08  09  10  11  12  13  14  15  16  17
LATHE-1      ░░░AAAAAAAAAA·····BBBBB·····BBB···░░░
LATHE-2      ░░░·····CCCCCCCCCCCCCC···············░░░
LATHE-3      ░░░·······················DDDDD······░░░

A = MILL-004   LATHE-1   09:00─10:40  non-preemptive
B = TURN-011   LATHE-1   preemptive, 2 spans
C = BORE-007   LATHE-2   10:20─13:20  non-preemptive
D = FACE-002   LATHE-3   15:00─15:50  non-preemptive
```

This is what a resource-pool scheduler sees: three bitmaps for the same window. Walk runs speculatively against each before any commit. LATHE-3 has the most free capacity; LATHE-2 offers the earliest start for a new operation.

### Output Rules for Claude Code

1. ASCII verification output goes to `stdout` via `print()`, not to a file.
2. Verification prints must be concise — designed to fit within approximately 40 lines so they are readable in the Claude Code summary panel without requiring ctrl+O.
3. Every verification function is prefixed `show_` and lives in `scheduling_primitives/debug.py`. It is never imported by production code — only by tests and development scripts.
4. Verification runs are triggered explicitly. Tests do not print unless `SCHEDPRIM_VERBOSE=1` is set.
5. When Claude Code implements a new data structure or algorithm, it must implement the corresponding `show_` function before marking the task complete.

### When Visual Verification Is Required

- After implementing `WorkingCalendar` interval generation for a new pattern type
- After implementing `OccupancyBitmap.from_calendar()` for any dataset
- After implementing `walk()` changes — show a before/after bitmap for a representative case
- After any change to the `AllocationRecord` span structure
- Before marking any phase complete — run `python -m scheduling_primitives.debug` against the test datasets and review the output

---

## 5. Test-Driven Development

### The Cycle

1. **Red**: Write a failing test. It must fail with `AssertionError`, not `ImportError` or `NameError`. If it passes immediately, the test or the implementation is wrong.
2. **Green**: Write the minimum implementation to pass. No more.
3. **Refactor**: Clean up with all tests green.

### Rules

- Tests assert on behaviour, not implementation internals.
- Each function requires at least three distinct input/output cases before it can be considered tested.
- Property-based tests (Hypothesis) are required for `walk()`, `allocate()`, `deallocate()`, and all arithmetic in `TimeResolution`.
- The cross-layer consistency test must pass before any phase is declared complete: `resolution.to_datetime(record.finish, epoch)` must equal `calendar.add_units(start, work_units)` for matched inputs.

### Test Data

The five canonical datasets (`simple`, `multi_shift`, `overnight`, `resource_variety`, `stress`) are the ground truth for all implementations. Test fixtures are JSON; they are the contract that any future port (TypeScript, VBA, M) must validate against.

---

## 6. What the Library Is Not

These are permanent scope exclusions. They belong in libraries that import scheduling-primitives.

- Dispatch rules (which operation goes next)
- Resource selection policy (which machine to assign)
- Optimisation algorithms (B&B, simulated annealing, genetic algorithms)
- Discrete event simulation
- ERP integration or data connectors
- Multi-resource constraint resolution (the operation needs a machine AND an operator AND a tool fitter simultaneously)

The greedy reference scheduler in `scheduling_primitives/greedy.py` demonstrates how these concerns are implemented *on top of* the primitives. It is clearly labelled as a reference implementation and makes no claim to optimality.

---

## 7. Development Environment

- **Package management**: UV throughout. No `pip install` without UV wrapper.
- **Python**: ≥ 3.10
- **Testing**: pytest. Hypothesis for property-based tests.
- **No dependencies in the core**: `calendar.py`, `occupancy.py`, `resolution.py` import nothing outside the standard library. Optional pandas dependency in `loaders.py` only.
- **Debug module**: `scheduling_primitives/debug.py` may import any visualisation dependency, but is excluded from the package's runtime dependencies.

---

## 8. Git Workflow

Single branch (`main`). Commit directly during normal development.

Short-lived branches for risky experiments only:

```
git checkout -b spike/experiment-name
# works → merge to main and delete
# fails → delete the branch
```

Specs and code live together on `main`.

---

## 9. AI Assistant Protocol

Before any session:

1. Read this constitution.
2. Read `specs/spec.md` for what is in scope.
3. Read `specs/plan.md` for the current phase and sequence.
4. Check `specs/tasks.md` for the current task status.

During implementation:

- Implement the corresponding `show_` function before marking a data structure task complete.
- Run visual verification and print the output before reporting a task done.
- If the spec is wrong or missing a requirement, say so. Do not silently work around it.
- Do not add capabilities not in the spec. If something seems missing, flag it and wait.

Scope discipline:

- If asked for something outside the current spec, state that explicitly and ask whether to update the spec or add it to the backlog.
- Never treat scope expansion as implicit.

Autonomy level for this project:

The core algorithm work (walk, bitmap, interval arithmetic) is **medium familiarity** — standard CS patterns but with project-specific correctness requirements. Complete one task at a time. Print visual verification output. Wait for human confirmation before the next task.

The calendar rule resolution (shift patterns, exceptions, overnight periods) is **high familiarity** — standard datetime arithmetic. Agent may complete full task cycles with tests as the feedback mechanism.

---

## 10. Governance

Amendments to this constitution require:

1. Explicit rationale documented in the amendment
2. Assessment of impact on the current spec, plan, and tasks
3. Version increment (MINOR for additions, MAJOR for changes to Design Principles)

This constitution is the highest-authority document in the project. Where it conflicts with anything else — design documents, prior conversations, implementation convenience — the constitution governs.
