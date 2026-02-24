# Constitution

**Version**: 1.0.0
**Ratified**: 2026-02-16

---

## 1. Planning Hierarchy

Work is organised in a strict hierarchy. Each level has a defined purpose, lifecycle, and location within the repository.

```
Vision          What the product is and where it's heading
  Epic          A stable scope boundary for a major capability area
    Feature     A deliverable increment of work within an epic
      Research  Investigation phase (optional, before specification)
      Spec      Detailed specification and acceptance criteria
      Plan      Execution sequence and dependencies
      Tasks     Individual work items
      Retro     Post-completion reflection
```

### Vision

The product-level "what and why." Describes what the product is, who it serves, what problems it solves, and the strategic direction. Features must be traceable to the vision.

- **Location**: `specs/vision.md`
- **Lifecycle**: Written once at project inception. Updated deliberately when strategic direction changes. Changes are annotated inline with date and rationale.
- **Stability**: High. If the vision is changing frequently, the project lacks clarity.

### Epic

A stable scope boundary for a major capability area. An epic defines the "what and why" for a coherent body of work that will be delivered across multiple features. Epics do NOT have specs, plans, or tasks of their own — those belong to features.

- **Location**: `specs/epic-{name}.md` (one file per epic, in the specs root)
- **Lifecycle**: Written when the capability area is first scoped. Adjusted as features within it deliver findings. Closed when all constituent features are complete or the epic is superseded.
- **Stability**: High. An epic should survive largely unchanged through the delivery of its features. If an epic needs frequent revision, it was scoped too tightly or too loosely.

An epic contains:
- **Purpose**: What capability this epic delivers and why it matters
- **Scope boundary**: What is included and explicitly what is not
- **Success criteria**: How we know the epic is complete
- **Feature list**: Ordered list of features, with status
- **Version and changelog**: Track adjustments (see Archiving Policy)

### Feature

The deliverable unit of work. A feature sits within one epic and produces a working, tested increment. Features are numbered sequentially across the project (not per-epic) to preserve the order work was done.

- **Location**: `specs/{NNN}-{feature-name}/` (feature subfolder)
- **Lifecycle**: Created when the feature reaches the front of the backlog. Progresses through research (optional) -> specification -> planning -> execution -> retrospective. Status tracked in the spec header.
- **Stability**: Medium. The spec may be updated during execution as discoveries are made, but changes should be deliberate and annotated.

A feature folder contains:
```
specs/NNN-feature-name/
  research.md         # Optional: investigation before specification
  spec.md             # Detailed specification and acceptance criteria
  plan.md             # Execution sequence and dependencies
  tasks.md            # Individual work items
  retrospective.md    # Post-completion reflection (mandatory)
  data-model.md       # Optional: entity/schema design
  quickstart.md       # Optional: setup/run instructions
  checklists/         # Optional: custom checklists
```

### Backlog

An ordered list of upcoming features. Each entry has enough context to write a spec when the time comes. The order reflects current priority. Updated whenever a retrospective changes priorities.

- **Location**: `specs/backlog.md`

### Milestones

Milestones group features across epics into a shippable product increment. A milestone defines what "done" looks like for a release and provides the bridge between internal feature work and external delivery.

- **Location**: `specs/milestones.md`

A milestone contains:
- **Name and target**: What this release is called and when it should be deliverable
- **Feature set**: Which features (across which epics) constitute this milestone
- **Acceptance criteria**: What must be true for the milestone to be declared complete
- **Dependencies**: Any external prerequisites (infrastructure, licensing, data)

---

## 2. Research Phase

Research is a first-class activity in the planning cascade. It exists to prevent premature specification — investigating the problem space before committing to a design.

Research can be scoped at two levels:

### Epic-Level Research

Broad investigation that informs epic scope, feature prioritisation, or architectural decisions. Happens before features are defined or when a strategic question cuts across multiple features.

- **Location**: `specs/research-{topic}.md` (in the specs root, alongside epics)
- **Trigger**: A new epic is being scoped, or a cross-cutting question emerges
- **Output**: Findings that feed into epic scope definitions, feature backlog ordering, or constitution amendments

### Feature-Level Research

Technical investigation before specification. Happens when a feature touches unfamiliar territory, when there are multiple viable approaches, or when the spec would be guesswork without investigation.

- **Location**: `specs/{NNN}-{feature-name}/research.md` (in the feature folder)
- **Trigger**: Feature reaches front of backlog but the problem space is unclear
- **Output**: Findings that feed into the feature spec. Research may also surface scope changes for the parent epic.

### Research Document Structure

Every research document follows the same structure:

1. **Questions**: What are we trying to find out? (Written before investigation.)
2. **Method**: How will we investigate? (Code reading, prototyping, external research, etc.)
3. **Findings**: What did we discover? (Factual observations, not recommendations.)
4. **Recommendations**: What should we do based on the findings? (Feed into spec/epic/backlog.)
5. **Open questions**: What remains unclear? (May trigger further research or become assumptions in the spec.)

### Research-First Workflow

The feature lifecycle with an optional research phase:

```
Backlog item reaches front of queue
  |
  v
Research needed?
  |           |
  YES         NO
  |           |
  v           |
Research      |
  |           |
  v           v
Specification
  |
  v
Planning
  |
  v
Execution
  |
  v
Retrospective
```

Research findings may cause a feature to be:
- **Specified as planned** — research confirms the approach
- **Re-scoped** — research reveals the feature is larger or smaller than expected
- **Split** — research reveals the feature should be two or more features
- **Deferred** — research reveals a prerequisite that must be addressed first
- **Abandoned** — research reveals the feature is unnecessary or infeasible

---

## 3. Document Lifecycle

### The Spec Kit Cascade

Documents are created in a specific order. Each document depends on its predecessors.

**Specs root** (stable, project-level):
```
specs/
  constitution.md           # Principles and process (this document)
  vision.md                 # Product direction
  backlog.md                # Feature queue
  milestones.md             # Release groupings
  epic-{name}.md            # Epic scope boundaries
  research-{topic}.md       # Epic-level research (optional)
  archive/                  # Archived research documents
```

**Feature subfolder** (per-feature, evolves during delivery):
```
specs/NNN-feature-name/
  research.md               # Optional: before specification
  spec.md                   # Required: what to build
  plan.md                   # Required: how to build it
  tasks.md                  # Required: individual work items
  retrospective.md          # Required: post-completion reflection
```

### Creation Order

1. **Constitution** exists before any work begins
2. **Vision** exists before any epics are defined
3. **Epic** exists before any features within it are specified
4. **Research** (if needed) exists before the spec is written
5. **Spec** exists before the plan is written
6. **Plan** exists before tasks are generated
7. **Tasks** exist before implementation begins
8. **Retrospective** is written after implementation is complete

This order is enforced: do not skip levels. If the spec is unclear, you need research, not guesswork in the plan.

---

## 4. Archiving and Versioning Policy

### Principle: Edit in Place, Let Git Track History

Documents are edited in place. Git history preserves previous versions. There is no need for `v1/v2` copies of the same document.

### Constitution Versioning

Changes to the constitution require:
1. Explicit discussion documenting the rationale for change
2. Assessment of impact on existing epics, features, and the vision
3. Version increment following semantic versioning:
   - **MAJOR**: Principle removal or incompatible redefinition
   - **MINOR**: New principle or material expansion
   - **PATCH**: Clarification or refinement

### Epic Versioning

Epics are adjusted in place with a version and changelog in the document header:

```markdown
**Version**: 1.2.0
**Changelog**:
- 1.2.0 (2026-03-15): Added Layer 2 event injection to scope
- 1.1.0 (2026-02-28): Narrowed scope to exclude daily mode
- 1.0.0 (2026-02-20): Initial scope definition
```

**Adjustment vs new epic**: If the epic's fundamental purpose remains the same but the scope boundary shifts, increment the version and update in place. If the purpose changes — you are describing a different capability area — create a new epic file and mark the old one as either **Complete** or **Superseded**.

Examples:
- "Add copula support to World Engine" -> adjustment to `epic-world-engine.md` (version bump)
- "Build a customer-facing web portal" -> new epic (`epic-web-portal.md`), not an adjustment to an existing one

### Feature Versioning

Feature specs are edited in place during execution. Annotate significant changes:
```markdown
<!-- Updated 2026-03-01: Removed US4 (deferred to Feature 015) -- too much scope -->
```

Features do not move to a `completed/` directory. The numbered prefix preserves delivery order. The feature's status is tracked in the spec header:

```markdown
**Status**: Complete | In Progress | Deferred | Abandoned
```

A retrospective is mandatory before marking a feature Complete. Features marked Abandoned must include a brief explanation in the spec header.

### Research Versioning

Research documents are written once and not revised. If new findings emerge later, they are recorded in a new research document or in the relevant feature's research phase — not by editing the original. This preserves the historical record of what was known when decisions were made.

To manage research document proliferation:
- Completed research documents may be moved to `specs/archive/research/` once their findings have been absorbed into epics or specs
- `specs/backlog.md` or the relevant epic maintains an index of research documents with one-line summaries, so that links remain navigable even after archiving
- Research that directly informed a feature spec should be cross-referenced in the spec header

---

## 5. Feedback Routing

Retrospectives and research produce findings that need to flow somewhere. This section defines where.

### Retrospective Findings Route To:

| Finding type | Routes to | Example |
|---|---|---|
| "The spec was wrong about X" | Feature spec (annotate in place) | Requirement FR-003 was infeasible |
| "We discovered a new constraint" | Constitution (if universal) or Epic (if scoped) | SQLite can't handle concurrent writes |
| "Feature Y should be re-prioritised" | Backlog | Layer 2 events need Layer 1 copula first |
| "The epic scope should change" | Epic (version bump + changelog) | ERP Simulator needs payment engine earlier |
| "The vision needs updating" | Vision (annotate) | BC licensing makes simulation-in-BC a fringe offering |
| "This approach should be standard" | Constitution (amendment) | Research phases should precede all specs |

### Research Findings Route To:

| Finding type | Routes to | Example |
|---|---|---|
| "We should build X this way" | Feature spec (becomes a requirement) | Use Marshall-Olkin algorithm for copula |
| "X is out of scope for this feature" | Backlog (new entry) or Epic (scope adjustment) | Multi-currency is a separate feature |
| "X is impossible/infeasible" | Epic or backlog (scope removal) | Daily mode requires BC API that doesn't exist |
| "We need to decide between A and B" | Discussion with human, then spec | Finite capacity in history: evaluate trade-offs |
| "X changes our architectural approach" | Constitution or vision | World/ERP separation is a core principle |

---

## 6. Lifecycle

### Feature Lifecycle

```
1. Consult backlog.md -> pick next feature
2. Read recent retrospectives for relevant learnings
3. Identify parent epic (create if needed)
4. Research phase (if needed):
   a. Write questions in research.md
   b. Investigate
   c. Record findings and recommendations
   d. Review with human
5. Write spec.md -> detailed specification
6. Write plan.md -> execution sequence
7. Generate tasks.md -> individual work items
8. Execute tasks, updating spec.md in place if needed
9. Write retrospective.md
10. Route retrospective findings (see Section 5)
11. Update backlog.md with any changed priorities
12. Return to step 1
```

### Epic Lifecycle

```
1. Identify a major capability area (from vision, research, or retrospective)
2. Write epic-{name}.md -> scope boundary and success criteria
3. Identify constituent features -> add to backlog
4. Features are delivered per the feature lifecycle above
5. After each feature retrospective, review epic scope
6. When all success criteria are met -> mark epic Complete
```

### Active Feature Discipline

The default is one active feature at a time. This constraint exists because:
- Context-switching between features destroys focus and introduces errors
- Sequential delivery surfaces integration issues early
- The retrospective loop works best with tight cycles

**Exception**: Multiple features may be active simultaneously if ALL of the following conditions are met:
1. The features belong to different epics
2. The features are genuinely independent (no shared files, no shared state)
3. The human has explicitly approved concurrent execution
4. Each feature maintains its own complete spec/plan/tasks lifecycle — no blending

Research phases for upcoming features may overlap with execution of the current feature without requiring the exception above, provided they are independent and the human approves.

---

## 7. Core Principles

### I. Disciplined Planning

Work proceeds through the strict hierarchy defined above. Neither human nor AI shall anticipate implementation details for work not yet in scope.

**Non-negotiable**: Research and feasibility planning must not prescribe solutions for features that have not been formally specified. When uncertain whether something is in scope, ask.

### II. Structured Approach to Novel Domains

When the path is unclear, slow down and invest in research before specification. The cost of rework in unfamiliar domains is high.

**Non-negotiable**: For novel architectural decisions, every significant design choice must be documented with rationale before implementation. If no prior art exists, a research phase is mandatory.

### III. Rigorous Test-Driven Development

Tests are the primary feedback mechanism for autonomous AI work. The TDD protocol below applies to all implementation work.

#### The Red-Green-Refactor Cycle

1. **Red**: Write a test that exercises the intended behaviour. The test MUST fail with an AssertionError (not ImportError, NameError, or any other error). If the test passes immediately, the test is wrong or the behaviour already exists.
2. **Green**: Write the minimum implementation to make the test pass. No more.
3. **Refactor**: Clean up with all tests passing.

#### Test Validity Rules

- Tests must assert on behaviour, not on implementation details
- Each unit test requires 3+ input-output cases (triangulation) to prevent hard-coding
- New functions may use a scaffold pattern (return a sentinel value initially) to confirm the test exercises assertion logic before implementing
- Property-based tests (Hypothesis or equivalent) are required for any function with numeric, statistical, or domain-specific logic

#### Outside-In Test Architecture

- Start with acceptance tests that exercise the feature end-to-end
- Work inward: acceptance → integration → unit
- Unit tests for pure logic; integration tests for component boundaries; acceptance tests for user-visible behaviour

#### Mutation Testing

Mutation testing is required for any module containing business logic or domain calculations. Tests that survive mutations are insufficient.

**Non-negotiable**: Implementation code must not be written until a properly-failing test exists. The agent must demonstrate the failing test before proceeding to green.

### IV. Verification and Visual Understanding

Automated tests are necessary but not sufficient. Human inspection of data outputs, time series visualisations, and financial statements is required before marking any data generation phase complete.

**Non-negotiable**: Sample outputs must be visually inspected and confirmed by human review.

### V. Epistemic Honesty in Low-Familiarity Domains

Some work involves domains that are thinly represented in LLM training data. In these domains, the AI agent will generate plausible-looking code that may be subtly wrong because it lacks sufficient prior art to pattern-match against.

#### Identifying Low-Familiarity Work

Work is likely low-familiarity when it involves:
- Synthetic data generation (especially stochastic processes, distributional properties, correlation structures)
- Simulation of real-world physical or business phenomena (world models, ERP transaction flows, manufacturing processes)
- Domain-specific algorithms where correctness depends on mathematical properties not easily verified by reading the code
- Any implementation where the spec references phenomena, equations, or business rules that originate outside the software domain

#### Required Safeguards

When working in low-familiarity domains:

1. **Cite or derive**: Every non-trivial formula or algorithm must either reference a known source or be derived step-by-step with the derivation documented. The agent must not generate formulas from memory alone.
2. **Small-batch validation**: Implementation proceeds in small increments with human-inspectable intermediate outputs. Do not implement an entire pipeline and validate at the end.
3. **Sanity-check assertions**: Embed runtime assertions that verify domain invariants (e.g., probabilities sum to 1, quantities are non-negative, conservation laws hold). These are in addition to tests.
4. **Visual inspection gates**: Any output that has statistical, temporal, or distributional properties must be visualised and reviewed by the human before proceeding. Automated tests alone are insufficient for catching subtle distributional errors.
5. **Declare uncertainty**: If the agent is not confident about a domain concept, it must say so explicitly rather than generating a plausible guess. The cost of rework in these domains is much higher than the cost of pausing to verify.

**Non-negotiable**: In low-familiarity domains, the agent must flag its confidence level when implementing domain-specific logic. "I am implementing this based on [source/derivation]" or "I am uncertain about this and recommend human verification before proceeding."

---

## 8. AI Assistant Instructions

### Context

This project uses the spec kit cascade defined above. Before writing any code, check `specs/` to understand what is being built and why.

### Before Starting Any Task

1. Read `specs/constitution.md` for project-level constraints and process
2. Identify the relevant epic (`specs/epic-{name}.md`) for scope boundaries
3. Read the feature spec (`specs/NNN-feature/spec.md`) for requirements
4. Read the feature plan (`specs/NNN-feature/plan.md`) for execution sequence
5. Check task status in `specs/NNN-feature/tasks.md`
6. Read any research documents relevant to the current work

### When Implementing

- Work on tasks in the order defined by the plan unless there is a clear technical reason to deviate
- Do not add capabilities not described in the spec. If something seems missing, flag it.
- If the spec is wrong or incomplete, say so explicitly. Do not silently work around spec issues.
- Mark tasks as complete when done, with a brief note on what was done

### When Asked to Research

- Write questions before investigating
- Separate findings (factual observations) from recommendations (what to do about them)
- Flag open questions explicitly
- Do not let research expand into specification or implementation

### When Asked to Plan or Specify

- Check completed features for retrospectives relevant to the new work
- Reference retrospective learnings explicitly when they affect the new spec
- Ensure consistency with the constitution, vision, and parent epic
- Flag conflicts between proposed work and existing constraints

### Scope Discipline

- If asked for something outside the current spec, confirm whether to update the spec or add it to the backlog
- Never treat scope expansion as implicit. Always make it visible.
- Research findings that suggest scope changes must be routed per Section 5, not silently absorbed.

---

## 9. Development Environment

- **Package management**: UV throughout. No pip install without UV wrapper.
- **Virtual environments**: Always use venv. No global package installations.
- **Notebooks**: Marimo for interactive exploration (not Jupyter).
- **Data interchange**: CSV or Parquet for human-inspectable exports. SQL for direct queries.
- **Code hygiene**: No proliferation. Single responsibility. DRY. Canonical locations for all reusable code.

---

## 10. Git Workflow

Single-branch workflow on `main`. Commit directly during normal development.

Short-lived branches only for risky experiments:
```
git checkout -b spike/experiment-name
# if it works -> merge to main
# if it fails -> delete the branch
```

Do not create long-lived feature branches. Specs and code live together on `main`.

---

## 11. Governance

This constitution governs all work on the project. Amendments require:

1. Explicit discussion documenting the rationale
2. Assessment of impact on existing epics, features, and vision
3. Version increment (MAJOR/MINOR/PATCH per Section 4)

Phases of autonomous AI work must be bounded by explicit human checkpoints. Autonomous phases are appropriate when success criteria are clear, encoded in tests, and tests genuinely indicate success. When these conditions are not met, return to the human for guidance.

### Autonomy Gradient

The degree of autonomous AI work is calibrated to the reliability of feedback:

| Domain familiarity                                          | Test coverage                                      | Autonomy level                                               |
| ----------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------ |
| High (standard patterns, well-represented in training data) | Comprehensive tests with mutation coverage         | Agent may complete full task cycles between human checkpoints |
| Medium (familiar patterns, project-specific logic)          | Tests exist but may not catch all domain errors    | Agent completes one task at a time, human reviews before next |
| Low (thin training data, novel domain logic)                | Tests may not be sufficient to catch subtle errors | Agent implements in small increments with visual inspection at each step |

The agent should self-assess which row applies and behave accordingly. When uncertain, default to the lower autonomy level.

All specifications, plans, and implementations must be reviewed against this constitution.
