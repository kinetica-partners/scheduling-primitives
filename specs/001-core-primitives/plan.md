# Implementation Plan: Core Scheduling Primitives

**Branch**: `001-core-primitives` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-core-primitives/spec.md`

## Summary

Build a zero-dependency Python library providing the mechanical foundations for finite capacity scheduling. Two-layer architecture: a datetime-based Working Calendar (horizon-free, lazy evaluation) and an integer-based Capacity State (auto-extending bitmap for allocation tracking). The library supports both short-horizon minute-grain scheduling and long-horizon hour-grain simulation through configurable time resolution.

## Technical Context

**Language/Version**: Python ≥ 3.10 (target 3.12+ for development)
**Primary Dependencies**: None in core (stdlib only). pytest + Hypothesis for testing. Optional Polars for data loading (pandas compatibility acceptable but Polars preferred).
**Storage**: N/A — in-memory data structures
**Testing**: pytest + Hypothesis (property-based tests for core algorithms)
**Target Platform**: Cross-platform CPython
**Project Type**: Library (PyPI package: `scheduling-primitives`)
**Performance Goals**: Resolution-proportional — coarser grain → proportionally less memory and faster calculations. Year-long simulations at hour grain must be feasible (~8,760 units per resource).
**Constraints**: Zero external dependencies in core. Integer-only arithmetic in engine (no floats). Half-open intervals throughout. Walk is read-only.
**Scale/Scope**: 20 resources × 4 weeks at minute grain ≈ 800 KB total bitmap. Comfortably in-memory for any realistic scenario.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --------- | ---- | ------ |
| I. Boundary Rule | Datetime boundary at `from_calendar()`. No datetime in engine. Primitives boundary: no policy decisions in library. | ✅ Spec FR-010, FR-020, FR-022, FR-033 enforce both boundaries |
| II. Integer Time | No floats in engine code. Resolution set once at boundary. | ✅ Spec FR-020, FR-034 (strict alignment rejection) |
| III. Half-Open Intervals | All intervals `[begin, end)`. Length = `end - begin`. | ✅ Will be enforced in all data structures and algorithms |
| IV. Walk Does Not Mutate | `walk()` is read-only. `allocate()` commits. | ✅ Spec FR-022 |
| V. allow_split Is a Job Property | Splittability is per-operation, not per-calendar or per-resource. | ✅ Spec FR-012, FR-013, FR-014 |
| VI. Visual Verification | ASCII representations for all interval/bitmap structures. Reviewed before marking complete. | ✅ Spec FR-023, SC-008 |
| TDD | Red/Green/Refactor. ≥3 cases per function. Property-based for core algorithms. | ✅ Spec SC-007, constitution §5 |
| Zero Dependencies | Core imports nothing outside stdlib. | ✅ Spec FR-025, SC-005 |
| Naming Convention | Practitioner-facing names in code. Theory terms in prose. | ✅ Spec Terminology table |

**No gate violations. Proceeding to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/001-core-primitives/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (public API)
│   └── public-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── scheduling_primitives/
    ├── __init__.py          # Public API exports
    ├── calendar.py          # Layer 1: WorkingCalendar (datetime-based, horizon-free)
    ├── occupancy.py         # Layer 2: OccupancyBitmap, walk, allocate, deallocate
    ├── resolution.py        # Boundary: TimeResolution (datetime ↔ int conversion)
    ├── types.py             # AllocationRecord, InfeasibleError, shared types
    ├── schema.py            # Input validation (rules, exceptions)
    ├── loaders.py           # CSV/JSON/DataFrame loading (optional Polars, pandas compatible)
    ├── greedy.py            # Reference scheduler
    └── debug.py             # ASCII visualisation (show_ functions, dev-only)

tests/
├── conftest.py              # Shared fixtures, dataset loading
├── test_calendar.py         # Layer 1: forward/backward walk, counting, intervals
├── test_calendar_rules.py   # Rules: weekly patterns, multi-period, overnight
├── test_calendar_exceptions.py  # Exceptions: holidays, overtime, partial days
├── test_resolution.py       # TimeResolution: conversion, alignment rejection
├── test_occupancy.py        # Layer 2: from_calendar, bitmap construction
├── test_walk.py             # Walk: non-splittable, splittable, min_split, deadline
├── test_allocate.py         # Allocate/deallocate, exact inverse property
├── test_dynamic.py          # Dynamic exceptions: add/remove capacity, conflict detection
├── test_checkpoint.py       # Checkpoint/restore for backtracking
├── test_consistency.py      # Cross-layer consistency (Layer 1 ↔ Layer 2)
├── test_auto_extend.py      # Horizon auto-extension
├── test_greedy.py           # Reference scheduler
└── test_properties.py       # Hypothesis property-based tests

data/
├── datapackage.json         # Frictionless Data Package descriptor
└── fixtures/
    ├── simple.json
    ├── multi_shift.json
    ├── overnight.json
    ├── resource_variety.json
    └── stress.json
```

**Structure Decision**: Single-package `src/` layout. Layer 1 (calendar.py) and Layer 2 (occupancy.py) in separate modules with the boundary conversion (resolution.py) between them. Shared types extracted to types.py to avoid circular imports. Test files mirror the module structure with additional cross-cutting test files for consistency and properties.

## Complexity Tracking

No constitution violations to justify. All gates pass.
