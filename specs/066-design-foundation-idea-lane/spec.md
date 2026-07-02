# Feature Specification: Design-Foundation Idea Lane + Backlog Seed (G1)

**Feature Branch**: `066-design-foundation-idea-lane`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified under the recorded ADOPT-batch autonomous authority dated 2026-07-02
> (owner directive: build+ratify+merge the entire ADOPT bucket; the advisor
> exercises the delegated per-spec ratify authority). A recorded per-spec override
> within that batch, not a standing waiver. No OPEN carve-out remains; the three
> reserved items are resolved conservatively (each the narrowest, no-schema-churn
> choice): (1) lane grain = a new `## Design Foundation` section in idea-backlog.md
> (simplest, no per-idea tag migration, matches the existing section structure);
> (2) ledger = REUSE the existing shipped-ideas.yaml `{status, pr_sha, f_row}` shape
> UNCHANGED (no new field -> the IL1 ledger-contract guard is untouched); (3) no
> roadmap F-row (off-spine like IL1/SC2; f_row none). Scope is the basic lane
> (docs + small idea-engine JS routing) only -- the structured lint-backlog +
> auto-reconciler stays a deferred HORIZON extension, and G1 adds NO src/retail rule
> and never promotes an idea onto the roadmap (Principle V). analyze: clean (0/0);
> plan-review: PASS-WITH-NOTES.

**Input**: User description: "G1. Design-Foundation Idea Lane + Backlog Seed"

## Overview

The idea-engine already treats the Power BI presentation layer as a first-class
concept. It runs a dedicated `design` GENERATION lens, a `design-foundation`
panel REVIEWER, and its idea schema carries a `design-system` value in the
`strengthens_layer` enum (theme tokens, background/canvas conventions, layout
blueprints, accessibility/contrast, design-review evidence -- governance of the
design layer, never report authoring). In short: the engine emits design
judgments today.

But those judgments have nowhere durable to land. The rendered idea backlog
(`docs/roadmap/idea-backlog.md`) groups ideas only by triage verdict
(ADOPT / CONSIDER / PARK / REJECT), Rescue notes, SHIPPED/SETTLED, and Run
health. There is no design-foundation grouping, so design ideas scatter across
the verdict buckets with no way to see or track the design layer as a cohort.
And when a design idea ships, it gets no structured shipped-row link back to the
roadmap the way the knowledge layers now do via the IL1 shipped-ideas ledger
(`docs/roadmap/shipped-ideas.yaml`, spec-dir 052).

This feature closes that asymmetry with the SMALLEST viable seam: a
design-foundation grouping the backlog can present, the same shipped-row link
extended to design-layer ships, a small idea-engine edit so the existing design
lens and design-foundation reviewer route their output under that grouping, and
a "see also" pointer from the design skill to the new lane so a design author
can find it.

The lane RECORDS and ROUTES; it never promotes. Consistent with IL1 and the
project invariant that the output is an idea BANK and not a roadmap, no step
(engine or otherwise) may write a roadmap F-row from the lane, and the design
lane may never self-assign an F-number. Grouping design ideas stays categorical
(a section/tag/status), never a computed or ranked numeric score (roadmap hard
rule #9).

Scope is deliberately the BASIC lane only -- documentation plus a small
JavaScript edit. It adds NO static-check rule module under `src/retail/rules/`
and NO auto-reconciler. Those (a structured design lint-backlog and a
ledger-reconcile rule) are the explicitly-deferred HORIZON extension and are
OUT OF SCOPE here.

G1 is off-spine: it maps to no roadmap readiness stage, directly analogous to
IL1 (spec-dir 052) and SC2 (spec-dir 065), both of which carry an `f_row` of
`none`. Whether G1 is ever given a roadmap F-row is a human decision recorded in
Clarifications, not something this spec self-assigns.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Design ideas have a lane to land in (Priority: P1)

As the maintainer running the idea-engine, when the backlog is rendered I want
design-foundation ideas to appear as a recognizable, first-class cohort (not
scattered anonymously across the verdict buckets) so I can see the design layer's
open ideas at a glance the way I already see the knowledge layers.

**Why this priority**: This is the load-bearing gap the idea names -- a design
GENERATOR (lens + reviewer) that today has no lane to fill. Delivering just this
story gives the design layer a durable home in the backlog and is a viable
minimum on its own.

**Independent Test**: Render (or hand-inspect) the backlog and confirm a
design-foundation grouping exists and that design-layer ideas are attributed to
it, with no numeric score attached to the grouping. Testable purely by reading
the rendered document; no runtime execution required.

**Acceptance Scenarios**:

1. **Given** the backlog has a design-foundation grouping, **When** a design-layer
   idea is present, **Then** it is presented under (or tagged to) that grouping and
   carries only categorical status (verdict/status/tag), never a computed score.
2. **Given** an idea that does not strengthen the design layer, **When** the
   backlog is rendered, **Then** it is NOT forced into the design-foundation
   grouping (the grouping reflects genuine design-layer membership, not padding).

---

### User Story 2 - A shipped design idea gets the same shipped-row link (Priority: P2)

As the maintainer, when a design-foundation idea has shipped I want it recorded in
the same human-curated shipped-ideas ledger with the same `{ status, pr_sha,
f_row }` shape the knowledge-layer ships use, so the engine's Memory stage stops
re-pitching it and the shipped evidence is available as known-history -- exactly
the link IL1 gave the other layers.

**Why this priority**: It extends the shipped-row->roadmap link to the design
layer. It is P2 because it only pays off once a design idea actually ships; the
lane (Story 1) is useful before then.

**Independent Test**: Add a design-layer key to the ledger following the existing
schema and confirm it validates under the same human-curated, engine-read-only
contract the knowledge-layer keys already satisfy (same three fields, `f_row`
allowed to be the literal `none`).

**Acceptance Scenarios**:

1. **Given** a design-foundation idea has shipped, **When** a human records it in
   the ledger, **Then** the entry uses the existing `{ status, pr_sha, f_row }`
   shape with `f_row` set to a human-placed roadmap label or the literal `none`.
2. **Given** the engine's Memory stage runs, **When** it reads the ledger, **Then**
   it consumes the design-layer entry as known-history and never appends to or
   rewrites the ledger (read-only contract preserved).

---

### User Story 3 - A design author can find the lane (Priority: P3)

As someone working in the Power BI design skill, when I follow the skill's
"See also" section I want a pointer to the design-foundation lane so I can find
where design ideas are tracked without hunting through the backlog.

**Why this priority**: A discoverability convenience. Lowest priority because the
lane works without it, but it makes the seam usable in practice.

**Independent Test**: Read the design skill's "See also" section and confirm it
names the design-foundation lane and points to the backlog location.

**Acceptance Scenarios**:

1. **Given** the design skill's "See also" section, **When** a reader scans it,
   **Then** it contains a pointer to the design-foundation lane in the backlog.

---

### Edge Cases

- What happens when a design idea has already shipped but is not yet in the
  ledger? The ledger is human-curated; the engine surfaces the prose-vs-ledger
  disagreement as a memory-integrity signal (inherited IL1 behavior) and never
  silently rewrites it. Building an automated reconciler for this is OUT OF SCOPE
  (HORIZON).
- What happens when an idea plausibly strengthens both the design layer and a
  knowledge layer? The idea schema assigns exactly one `strengthens_layer`; the
  lens judges the single best fit (existing engine behavior). The lane does not
  duplicate an idea across groupings.
- What happens when the design-foundation grouping is empty (no open design
  ideas)? The grouping renders as present-but-empty rather than being omitted, so
  the cohort stays visible as a first-class layer.
- What happens if a future author tries to enforce the lane with a static-check
  rule? That crosses out of this spec's scope. No design rule module exists under
  `src/retail/rules/` today and this spec deliberately does not add one; the
  boundary is a HORIZON extension, not a dependency.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backlog document (`docs/roadmap/idea-backlog.md`) MUST present a
  first-class design-foundation grouping that the design layer's ideas are
  attributed to.
- **FR-002**: The design-foundation grouping MUST classify ideas categorically
  (section / tag / status), and MUST NOT attach a computed or ranked numeric score
  to the grouping or to membership in it (roadmap hard rule #9).
- **FR-003**: The shipped-ideas ledger (`docs/roadmap/shipped-ideas.yaml`) MUST be
  able to record a shipped or settled design-foundation idea using the existing
  entry contract, so a design-layer ship gets the same shipped-row->roadmap link
  the knowledge layers have.
- **FR-004**: The ledger MUST remain human-curated and engine-READ-ONLY: no
  engine or automated step may append to it, rewrite it, or derive a roadmap F-row
  from it. This inherits the IL1 contract unchanged.
- **FR-005**: The design-foundation lane MUST NOT promote any idea onto the
  roadmap and MUST NOT self-assign an F-number; an `f_row` is recorded only when a
  human has already placed one, otherwise it is the literal `none`.
- **FR-006**: The idea-engine (`.claude/workflows/idea-engine.js`) MUST route the
  output of the existing design generation lens and the existing design-foundation
  panel reviewer under the new grouping when the backlog is rendered, using the
  existing `strengthens_layer = design-system` signal to identify design-layer
  ideas.
- **FR-007**: The idea-engine edit MUST be limited to grouping/routing/rendering;
  it MUST NOT add a scoring mechanism, MUST NOT change the read-only Memory
  contract, and MUST NOT introduce report/PBIP/PBIR authoring, DAX generation, or
  any metric invention.
- **FR-008**: The Power BI design skill (`.claude/skills/powerbi-dashboard-design/SKILL.md`)
  MUST gain a "See also" pointer to the design-foundation lane.
- **FR-009**: This feature MUST NOT add any static-check rule module under
  `src/retail/rules/` and MUST NOT add any automated ledger reconciler; those are
  the deferred HORIZON extension and are out of scope.
- **FR-010**: Every artifact this feature authors MUST be generic: no
  worked-example (e.g. pharmacy/c086) file paths, hex values, metric names, or
  sample data may be baked into the lane definition or its seed content. Any
  worked-example corpus is read only as one generic example a glob would match,
  never hardcoded.
- **FR-011**: The lane's grain in the backlog -- whether a new `## ` section, a
  per-idea tag on existing ideas, or a `strengthens_layer = design-system` filter
  view -- is a human design decision. [NEEDS CLARIFICATION: lane grain is a
  presentation/design call the human owns; see Clarifications.]
- **FR-012**: Whether the shipped-ideas ledger schema gains any design/layer field
  or design ideas reuse the existing `{ status, pr_sha, f_row }` shape unchanged is
  a human decision, because any schema change touches the IL1 ledger-contract
  guard. [NEEDS CLARIFICATION: ledger schema change is a contract decision the
  human owns; see Clarifications.]

### Key Entities *(include if feature involves data)*

- **Design-foundation grouping**: The first-class cohort in the backlog that
  design-layer ideas are attributed to. Identified via the existing
  `strengthens_layer = design-system` signal. Categorical only; carries no score.
- **Shipped-ideas ledger entry**: A human-curated record keyed by an idea's backlog
  short-code, with exactly `status` ("shipped" | "settled"), `pr_sha` (evidence
  string), and `f_row` (a human-placed roadmap label or the literal `none`).
  Design-layer ships reuse this shape.
- **Design skill "See also" pointer**: A discoverability link from the design skill
  to the lane's location in the backlog.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader inspecting the rendered backlog can identify the
  design-foundation grouping and see the design layer's open ideas as a cohort in
  a single pass, without reading engine internals.
- **SC-002**: 100% of the design-foundation grouping's presentation is categorical
  -- zero computed or ranked numeric scores are attached to the grouping or its
  membership.
- **SC-003**: A shipped design-layer idea can be recorded in the ledger using the
  existing three-field entry contract, and it validates against the same
  human-curated read-only contract the existing knowledge-layer entries satisfy.
- **SC-004**: Zero new static-check rule modules and zero automated reconcilers are
  introduced by this feature (verified by inspecting `src/retail/rules/` for no
  new module and the change set for no reconciler).
- **SC-005**: Zero worked-example-specific values (paths, hexes, metric names,
  sample data) appear in any artifact this feature authors.
- **SC-006**: A design author following the design skill's "See also" section
  reaches the design-foundation lane.

## Assumptions

- The existing `design` generation lens, `design-foundation` panel reviewer, and
  the `strengthens_layer = design-system` enum value already exist in the
  idea-engine and are the signal the lane groups on (confirmed in the repo today).
- G1 is off-spine and carries no roadmap readiness stage, matching IL1 (052) and
  SC2 (065); its `f_row` is `none` unless and until a human places one.
- The shipped-ideas ledger's IL1 contract (human-curated, engine read-only, never
  auto-promoting a roadmap F-row) is authoritative and inherited unchanged.
- The deferred HORIZON extension (a structured design lint-backlog and a
  ledger-reconcile rule) is a separate future decision and is not a dependency of
  this feature.
- No deferred capability is assumed to exist: F016 (Power BI execution/authoring
  adapter) and any spec-only runtimes are NOT relied on; this feature authors no
  report and executes nothing.

## Clarifications

<!--
  Principle-V carve-outs: decisions a human owns (constitution line 298). These are
  NOT answered by the planning agent. They are recorded here and left open for a
  human ruling. The clarify stage may add a dated session below for the ordinary
  (non-Principle-V) ambiguities it resolves.
-->

- **Lane grain (FR-011)** -- HUMAN-OWNED: whether the design-foundation grouping is
  a new `## ` section, a per-idea tag on existing ideas, or a
  `strengthens_layer = design-system` filter view. This is a backlog presentation/
  design call the idea text offers as alternatives; it is not derivable from the
  repo. Left open for a human decision.
- **Ledger schema change (FR-012)** -- HUMAN-OWNED: whether the shipped-ideas ledger
  gains a design/layer field or design ideas reuse the existing
  `{ status, pr_sha, f_row }` shape unchanged. Any schema change touches the IL1
  ledger-contract guard and is a contract decision. Left open for a human ruling.
- **Roadmap F-row for G1** -- HUMAN-OWNED: G1 has no roadmap F-number and no
  readiness stage. Whether it is correctly off-spine (like IL1/SC2, earning
  `f_row: none`) or should be given an F-row at all is a human decision. This spec
  self-assigns none.

### Session 2026-07-02

Ordinary (non-Principle-V) ambiguities resolved by the planning agent acting as
the advisor against the constitution, the IL1 contract, and the roadmap hard
rules. The three HUMAN-OWNED items above are Principle-V carve-outs and remain
open -- they are NOT answered here.

- **Q1 (scope: ADOPT vs HORIZON split)**: Does this spec scope the basic lane only
  (docs + small JS), explicitly excluding any static-check rule module and any
  automated ledger reconciler?
  - **Recommended answer**: YES -- scope ONLY the basic lane. The ADOPTed idea is
    the docs+JS seam; the structured design lint-backlog and the ledger-reconcile
    rule are the explicitly-deferred HORIZON extension.
  - **Reasoning**: The idea's own reviewers ADOPT the basic lane now and defer the
    structured variant. Adding a rule module would also collide with the
    "add the seam, not the implementation" YAGNI discipline and would touch the
    5-place rule-wiring surface, expanding scope well past the idea. FR-009 already
    fixes this boundary; this clarification confirms it.
  - **Reversible**: easy (a HORIZON follow-on spec can add the rule later).

- **Q2 (ledger action now vs shape-only)**: For User Story 2, does this feature add
  a concrete design-layer entry to `shipped-ideas.yaml` now, or only ensure the
  existing entry shape can carry a design-layer ship when one occurs?
  - **Recommended answer**: SHAPE-ONLY -- do not add a design-layer entry now. No
    design-foundation idea has shipped yet, and the ledger is human-curated and
    engine-read-only, so the agent must not fabricate a shipped row. The feature
    ensures the existing `{ status, pr_sha, f_row }` shape accommodates a
    design-layer key when a human records a real ship.
  - **Reasoning**: FR-004 keeps the ledger human-curated and engine-read-only;
    inventing a shipped entry with no real PR/SHA would violate that contract and
    fabricate evidence. This keeps the change additive-and-inert until a genuine
    design ship exists.
  - **Reversible**: easy (a human appends a real entry the moment a design idea
    ships).
