# Claude Code Context: scheduling-primitives

## Project Overview

**Purpose**: Open source Python library providing mechanical foundations for finite capacity scheduling: working calendars, occupancy state, and time arithmetic.

**Phase**: Pre-spec. Constitution ratified. Next step: run the speckit process to produce spec.md from user requirements.

**Constitution**: `specs/constitution.md` — Read before any work. Governs all process, TDD, design principles, and quality requirements.

## Technology Stack

- **Language**: Python 3.12+
- **Testing**: pytest + Hypothesis
- **Package Management**: UV. No `pip install` without UV wrapper.
- **Dependencies**: None in core (stdlib only). Optional Polars (preferred) or pandas in loaders.

## Environment

Always use venv.

## Architecture

Greenfield — no code yet. Target structure from constitution:

```
src/scheduling_primitives/
  calendar.py       Layer 1: WorkingCalendar (datetime-based, horizon-free)
  occupancy.py      Layer 2: OccupancyBitmap, walk, allocate/deallocate (integer-based)
  resolution.py     Boundary: TimeResolution (datetime ↔ int conversion)
  debug.py          Visual verification (show_ functions, not imported by production code)
  greedy.py         Reference scheduler (documentation in code form, not production)
tests/
data/               Test fixtures (JSON)
specs/              Constitution, spec, plan, tasks
docs/               Design references
```

## Domain Context

Production scheduling. The library sits below dispatching and optimisation — it provides the time arithmetic and capacity tracking that schedulers are built on. Key concepts: working calendars with shift patterns and exceptions, bitmap-based occupancy tracking, preemptive vs non-preemptive allocation. The agent should expect interval arithmetic edge cases to be the primary source of bugs.

## Learned Rules

(None yet — will accumulate from retrospectives)

## DO NOT

- Add capabilities not in the spec. Flag and wait.
- Import datetime objects into Layer 2 code. The boundary is `from_calendar()`.
- Use floats in engine code. Integer arithmetic only.
- Use closed intervals. Everything is half-open `[begin, end)`.
- Use `pip install` directly. UV only.
- Silently work around a spec deficiency. Update the spec first.
- Treat scope expansion as implicit. Ask explicitly.

## Current Focus

Run the speckit process: specify → clarify → plan → tasks. The v2 design doc is input, not the spec itself.

## Navigation

- `specs/constitution.md` — Governing principles and process (read first)
- `docs/scheduling-primitives-spec-v2.md` — Design reference document (input for spec process, NOT the active spec)
- `specs/spec.md` — Active specification (does not exist yet)
- `specs/plan.md` — Execution plan (does not exist yet)
- `specs/tasks.md` — Task list (does not exist yet)
