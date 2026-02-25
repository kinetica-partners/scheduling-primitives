# Constitution: scheduling-primitives

**Version**: 2.0.0
**Ratified**: 2026-02-23
**Amended**: 2026-02-24 — Slimmed: moved terminology table, visual verification format, and specific test requirements to spec. Kept principles and process.
**Amended**: 2026-02-24 — Added Architecture step to planning hierarchy. Updated Boundary Rule to use architecture terminology (Engine, Compiler, Calendar, API) instead of Layer 1/Layer 2. MAJOR version bump: Design Principle change.

---

## 1. Project Identity

**scheduling-primitives** is an open source Python library (MIT licence) providing the mechanical foundations for finite capacity scheduling: working calendars, occupancy state, and time arithmetic.

It is a substrate. It does not dispatch, optimise, simulate, or integrate with ERPs. Those concerns belong in libraries that import this one.

The library ships with a greedy reference scheduler that demonstrates correct use of the primitives. This is documentation in code form, not a production scheduler.

---

## 2. Planning Hierarchy

This project uses a four-level cascade. Vision and Epic levels are not used — the project scope is sufficiently bounded that a single spec governs all work.

```
Constitution    Project-wide principles and constraints (this document)
  Architecture  Core abstractions, boundaries, engine interface
  Spec          What the library does — requirements and acceptance criteria
  Plan          How we will build it — phases and sequencing
  Tasks         Individual work items with acceptance criteria
  Retrospective What we learned (written after each phase)
```

The architecture document sits between the constitution and the spec. It defines the core abstractions (Calendar, Compiler, Engine, API), their boundaries, and the engine interface. The spec references the architecture for structural decisions; the architecture references the constitution for principles.

**Locations**:

```
specs/
  constitution.md          ← this document
  architecture.md          ← core abstractions and boundaries
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

## 3. Naming Convention

This library uses practitioner-facing names in code (e.g. `allow_split`, `work_units`, `earliest_start`). Where these differ from scheduling theory terminology, the full mapping is recorded in the spec. In prose aimed at an OR or academic audience, use the theoretical terms with the code name in parentheses on first use.

---

## 4. Design Principles

These are standing constraints. They apply to every spec, every implementation decision, and every review. Amending them requires an explicit rationale and a constitution version increment.

### I. Boundary Rule

**A layer's responsibility ends where a different kind of knowledge begins.**

Two boundaries are defined and must be maintained. See `specs/architecture.md` Section 2.3 for the concrete definitions and the full abstraction stack.

**The datetime boundary** sits at the compiler -- the process that transforms a calendar (rules + planned exceptions) into integer intervals at a given resolution. Above it: datetimes, dates, shift patterns, weekday rules. Below it: the engine, which operates on pure integers. After compilation, no datetime object crosses into the engine.

**The primitives boundary** sits at the engine interface. Below it: mechanical slot-finding and state management. Above it: policy decisions (which operation next, which resource to prefer, whether to authorize overtime). The engine answers "does this fit, and where?" It does not answer "should we do this?" Those are policy questions requiring business knowledge the library does not have.

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

## 5. Test-Driven Development

### The Cycle

1. **Red**: Write a failing test. It must fail with `AssertionError`, not `ImportError` or `NameError`. If it passes immediately, the test or the implementation is wrong.
2. **Green**: Write the minimum implementation to pass. No more.
3. **Refactor**: Clean up with all tests green.

### Rules

- Tests assert on behaviour, not implementation internals.
- Each public function requires at least three distinct input/output cases before it can be considered tested.
- Property-based tests (Hypothesis) are required for core algorithm functions. The spec identifies which functions.
- Cross-boundary consistency (calendar-level datetime walk agrees with engine-level integer walk) must hold before any phase is declared complete. The spec defines the specific assertions.
- Test fixtures are JSON and serve as the contract for any future port.

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
- **No dependencies in the core**: `calendar.py`, `occupancy.py`, `resolution.py` import nothing outside the standard library. Optional Polars (preferred) or pandas dependency in `loaders.py` only.
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
2. Read `specs/architecture.md` for core abstractions and boundaries.
3. Read `specs/spec.md` for what is in scope.
4. Read `specs/plan.md` for the current phase and sequence.
5. Check `specs/tasks.md` for the current task status.

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
