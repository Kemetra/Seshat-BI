# Feature Specification: Stage 7 Answerability Summary (executive-readable)

**Feature Branch**: `053-stage-7-answerability-summary-executive`

**Created**: 2026-07-01

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-07-01)

**Ratification note**: Ratified by the advisor agent acting under an explicit,
recorded per-session delegated override granted by the repo owner
(info@rahmaqanater.org) for the 2026-07-01 "release the kraken" session, covering
the seven idea-to-spec specs produced this session. Provenance: this Ratified line
is AI-authored under recorded human authority; it is NOT a human-typed ratification
and the git author identity does not by itself attest a human reviewer. The two
Principle-V open items are resolved as recorded rulings in the Clarifications
section / FR-014 / FR-015, both taking the conservative answer (explicit PII
no-publish-safety-judgment posture; flat blocked-pending list, no severity/priority
ordering). No new `retail check` rule is added (count stays 38). analyze=clean
(0 critical/0 high, 1 low); plan-review=PASS-WITH-NOTES (2 low, both addressed:
C086-by-reference tightened in T010, FR-011 no-grouping confirmation added, T011
re-scoped to encode the rulings). The override is per-session and per-this-set only,
not a standing waiver; it covers ratification, not the merge decision (normal CI
gate still applies).

**Input**: User description: "Stage 7 Answerability Summary (executive-readable)"

## Overview

A new generic handoff template -- `templates/handoff/answerability-summary.md` -- that
presents, for a single source table reaching Publish Ready (Stage 7), three
executive/sponsor-readable lists composed from artifacts that ALREADY exist:

- **Answerable today** -- decision questions whose KPI contract is Seeded and whose
  required fields are present (a "Covered" row in the KPI Coverage Scorecard).
- **Blocked -- pending decision** -- decision questions whose KPI is blocked because a
  required field is absent or a headline-moving business policy (VAT, returns, cost
  method, date choice, same-store, snapshot date) is undecided.
- **Out of scope** -- decision questions whose KPI belongs to a domain this table cannot
  serve.

The template is a READABILITY LAYER over the human publish-approval seam. It grants no
approval, moves no readiness stage to `pass`, and invents no data, KPI, rollup, or
number. `docs/readiness/publish-ready.md` gains a single NON-GATING reference to it.

This is a presentation-only Stage 7 filler. It is NOT a roadmap feature row, NOT a new
`retail check` rule, and NOT an execution path. It sits beside the engineer-facing
`templates/handoff/bi-handoff-pack.md` and serves a DISTINCT sponsor/finance audience;
it does not restate that pack.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sponsor reads what a table can answer today (Priority: P1)

A business sponsor or finance stakeholder, who does not read the engineer-facing handoff
pack, opens the answerability summary for a table that has reached Publish Ready. In one
executive-readable page they see, in plain business language, which decision questions
the table can answer today, which are waiting on a named business decision, and which are
out of scope -- each expressed as a status plus a named blocker, never as a percentage or
score.

**Why this priority**: This is the entire value of the idea -- an executive-readable
answerability view for an audience the engineer pack does not serve, filling the verified
zero-artifact gap at Stage 7 (Publish Ready).

**Independent Test**: Open the filled template for one table and confirm each of the three
lists is populated only from existing F7 domain decision questions and F8 coverage
statuses, that every blocked row names its specific missing field or undecided policy, and
that no percentage/score/readiness verdict appears anywhere.

**Acceptance Scenarios**:

1. **Given** a table whose KPI Coverage Scorecard marks a decision question "Covered"
   (contract Seeded and required fields present), **When** the summary is assembled,
   **Then** that decision question appears in the "Answerable today" list with no blocker.
2. **Given** a table whose scorecard marks a KPI "Blocked -- needs business definition"
   because VAT treatment (A1) is undecided, **When** the summary is assembled, **Then** the
   corresponding decision question appears in "Blocked -- pending decision" with the named
   undecided policy as its blocker.
3. **Given** a KPI whose domain the table cannot serve (e.g. an inventory KPI against a
   sales-only fact), **When** the summary is assembled, **Then** that decision question
   appears in "Out of scope" with the reason named.
4. **Given** any assembled summary, **When** a reader looks for a coverage percentage or a
   readiness/health score, **Then** none exists -- coverage is only status + named blocker.

---

### User Story 2 - Publish-ready doc points to the summary without gating on it (Priority: P2)

Someone walking `docs/readiness/publish-ready.md` finds a single non-gating reference to
the new answerability summary -- offered as an optional executive-facing companion to the
handoff pack, explicitly not a Stage 7 required artifact and not a gate.

**Why this priority**: The seam (a reference from the stage authority) is what makes the
template discoverable, but it must NOT become a required gate -- that would over-scope the
idea and change the Stage 7 pass conditions.

**Independent Test**: Read `publish-ready.md` and confirm the reference lives in a
non-gating location (e.g. "See also"), does not appear in "Required artifacts", "Required
checks", or "Blocking reasons", and its wording marks the summary as optional/non-gating.

**Acceptance Scenarios**:

1. **Given** the edited `publish-ready.md`, **When** the reference is located, **Then** it
   sits in a non-gating section and is worded as an optional executive companion, not a
   required artifact.
2. **Given** the edited `publish-ready.md`, **When** the "Required artifacts", "Required
   checks", and "Blocking reasons" sections are read, **Then** the answerability summary
   appears in NONE of them.

---

### User Story 3 - Template stays generic and schema-agnostic (Priority: P3)

An author copying the template for a new (non-pharmacy) table finds only generic
placeholders and generic KPI/domain names -- no pharmacy tables, categories, or field
names baked in. Any concrete pharmacy example is reached only by reference to the worked
example.

**Why this priority**: C086 leak protection (hard rule #7 / Principle VII). A generic
template must remain reusable for any retail source, not shade toward the first worked
example.

**Independent Test**: Scan the template for pharmacy-specific table names, category names,
or field names; confirm none are present and any concrete instance is cited by reference to
`docs/worked-examples/c086-pharmacy.md`.

**Acceptance Scenarios**:

1. **Given** the template, **When** it is scanned for concrete schema names, **Then** only
   `<placeholder>` tokens and generic KPI/domain names appear.
2. **Given** the template, **When** a concrete example is needed, **Then** it is cited by
   reference to the worked example, never inlined.

---

### Edge Cases

- **A table where every decision question is blocked**: the "Answerable today" list is
  legitimately empty; the summary shows an empty list with an explicit "none today" note,
  never a fabricated positive or a percentage.
- **A KPI marked Planned in F8 (no seeded contract)**: it is neither answerable-today nor a
  business-decision blocker; the template MUST state where a Planned KPI is placed so it is
  never silently dropped or miscounted as answerable. (Resolved in Clarifications: Planned
  routes to a distinct note, not into any of the three headline lists.)
- **An undecided PII exclusion**: the summary must not imply a field is safe to expose; it
  inherits the caveats-note PII posture and asserts no publish-safety judgment
  (Principle-V item, left for Clarifications).
- **A blocked-pending list with many items**: whether the list carries any
  severity/priority ordering is a judgment the agent must not make unilaterally
  (Principle-V item, left for Clarifications).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deliverable MUST be a new file `templates/handoff/answerability-summary.md`
  and a single non-gating reference added to `docs/readiness/publish-ready.md`. No runtime
  code, no new `retail check` rule (rule count stays 38).
- **FR-002**: The template MUST present exactly three lists -- "Answerable today",
  "Blocked -- pending decision", and "Out of scope" -- each composed ONLY from existing F7
  domain decision questions (`skills/retail-kpi-knowledge/domains/*.md`) and F8 coverage
  statuses (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`).
- **FR-003**: Each "Answerable today" row MUST correspond to a decision question whose KPI
  is "Covered" in the coverage scorecard (contract Seeded AND required fields present); it
  MUST NOT be inferred from field presence alone.
- **FR-004**: Each "Blocked -- pending decision" row MUST name its specific blocker -- a
  named missing field or a named undecided policy drawn from
  `skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md` (A1-A11). It MUST NOT soften a
  blocker to an adjective and MUST NOT resolve the undecided policy.
- **FR-005**: Coverage/answerability MUST be expressed as STATUS + named blocker ONLY. A
  percentage, count-based score, or any numeric confidence/health figure is FORBIDDEN
  (hard rule #9; the F8 no-score discipline).
- **FR-006**: The template MUST grant no approval and move no readiness stage to `pass`. It
  MUST state explicitly that it is a presentation over the human publish-approval seam and
  changes no stage status (Principle V).
- **FR-007**: The reference in `docs/readiness/publish-ready.md` MUST be non-gating: it MUST
  NOT appear in "Required artifacts", "Required checks", or "Blocking reasons", and MUST be
  worded as an optional executive companion.
- **FR-008**: The template MUST be generic and schema-agnostic -- placeholders and generic
  KPI/domain names only, no pharmacy tables/categories/field names. Any concrete instance
  is cited by reference to `docs/worked-examples/c086-pharmacy.md` (hard rule #7).
- **FR-009**: "Answerable today" MUST mean paper-answerable (contract Seeded + fields
  present per F8), NOT live-validated. The template MUST NOT assume a live publish path or
  the F016 Power BI execution adapter (deferred/absent).
- **FR-010**: The template MUST target a sponsor/finance audience and MUST NOT duplicate the
  engineer-facing `templates/handoff/bi-handoff-pack.md`; it composes and references rather
  than restating pack sections.
- **FR-011**: The three lists MUST compose existing F7 domain routes + F8 coverage
  statuses only; the template MUST invent no rollup, segment, or grouping not already
  present in the domain files.
- **FR-012**: All authored text MUST be ASCII, UTF-8 without BOM (use `--` and `->`, no
  Unicode glyphs; rule IX). Paths MUST stay short (Windows MAX_PATH).
- **FR-013**: A KPI marked "Planned" in F8 (no seeded contract) MUST be routed to a
  distinct "Planned / not yet contracted" note and MUST NOT appear in any of the three
  headline lists, so it is neither dropped nor counted as answerable.

### Principle-V requirements (left for human ruling; see Clarifications)

- **FR-014** (human-ruled 2026-07-01): The template MUST carry an explicit PII posture:
  it inherits the caveats-note PII-exclusion stance and states, in a fixed template line,
  that "answerable today" is an answerability statement ONLY and asserts NO publish-safety
  judgment -- no field is implied safe to expose by appearing in any list. Publish-safety
  remains an un-delegatable human judgment (Principle V).
- **FR-015** (human-ruled 2026-07-01): The blocked-pending list MUST stay a FLAT observed
  list with NO severity/priority/rank ordering (list order carries no meaning beyond source
  order). Which blocker matters most is a priority judgment the agent must not make; if an
  owner later wants an ordering, that is a separate human-supplied input, out of scope here.

### Key Entities

- **Decision question**: an existing row in an F7 domain file that routes a business
  question to a Seeded contract or an honest Planned marker. The atomic unit of all three
  lists.
- **Coverage status**: one of the F8 vocabulary values -- Covered / Blocked -- missing
  field / Blocked -- needs business definition / Planned / Out of scope -- attached to a
  KPI for a specific table.
- **Named blocker**: the specific missing field or specific undecided policy (A1-A11) that
  keeps a decision question out of "Answerable today".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A sponsor with no engineering context can read the summary and, for any
  listed decision question, state whether the table answers it today and -- if not -- the
  named reason, without consulting any other document.
- **SC-002**: Zero numeric coverage/answerability figures appear in the template or the
  publish-ready reference (no percentage, no score, no count-as-score).
- **SC-003**: The publish-ready reference appears in exactly one non-gating location and in
  none of "Required artifacts", "Required checks", or "Blocking reasons"; Stage 7 pass
  conditions are unchanged.
- **SC-004**: A scan of the template finds zero pharmacy-specific table/category/field
  names; every concrete example is reached by reference to the worked example.
- **SC-005**: Every "Blocked -- pending decision" row names a specific field or a specific
  A1-A11 policy; zero rows use a softened adjective in place of a named blocker.
- **SC-006**: The `retail check` rule count remains 38 (no new rule added).

## Assumptions

- The F7 KPI Decision-Question Index (12 domain files) and the F8 KPI Coverage Scorecard
  template are shipped and are the sole answerable-today / coverage sources; this feature
  adds no new source of truth.
- Tracked source paths are under `skills/retail-kpi-knowledge/` (the `.claude/skills/...`
  paths cited elsewhere are worktree copies and MUST NOT be referenced).
- "F7"/"F8" are idea-bank family ids (shipped PRs), NOT roadmap feature rows F007/F008;
  this feature has no roadmap F-number and advances no stage to `pass`.
- The domain-file count is 12 (customer.md was added), not the roadmap's stale "11".
- The F016 Power BI execution adapter is absent; "answerable today" is paper-answerable,
  never live-validated.
- The summary is filled per table by an analyst/agent from existing artifacts; the
  template ships with placeholders and an illustrative-by-reference example only.
- The Stage 7 human publish approval remains an un-delegatable human action; this template
  is presentation over it and self-grants nothing (Principle V).

## Clarifications

### Session 2026-07-01

Advisor-resolved (ordinary ambiguities; reasoned against the constitution, the readiness
spine, and the F8 no-score discipline):

- **Q: Where in `publish-ready.md` does the non-gating reference go?**
  A: In the "See also" section only, worded as an optional executive companion. Reasoning:
  "Required artifacts" / "Required checks" / "Blocking reasons" are gating sections; placing
  it there would change Stage 7 pass conditions (over-scope, violates YAGNI). "See also" is
  the existing non-gating list. Reversible: easy (a doc line).
- **Q: How is a "Planned" (no seeded contract) KPI handled so it is neither dropped nor
  miscounted as answerable?**
  A: Route Planned KPIs to a distinct "Planned / not yet contracted" note, outside the three
  headline lists (FR-013). Reasoning: F8 treats Planned as "nothing to cover, do not
  fabricate"; folding it into answerable-today would fabricate coverage, and dropping it
  silently would hide a real gap. Reversible: easy.
- **Q: What is the atomic unit each list is keyed on -- KPI or decision question?**
  A: The decision question (the F7 domain-file row), with its KPI's F8 coverage status
  attached. Reasoning: the audience is sponsor/finance, who think in business questions, not
  KPI internals; F7 already routes each decision question to a contract or Planned marker, so
  no new mapping is invented (Principle VII, no rollup). Reversible: easy.

Human-ruled 2026-07-01 (Principle-V judgment calls -- resolved by the repo owner under the
recorded per-session ratify override; encoded into FR-014 / FR-015 above):

- **PII publish-safety (FR-014)**: RULED -- the template MUST inherit the caveats-note
  PII-exclusion posture and carry a fixed line asserting that "answerable today" is an
  answerability statement only and makes NO publish-safety judgment (no field is implied
  safe to expose). Rationale: the conservative posture removes the "safe to expose"
  misread while keeping publish-safety a human judgment (Principle V). Reversible: easy.
- **Business rollup/segment ordering (FR-015)**: RULED -- the blocked-pending list stays a
  FLAT observed list with no severity/priority/rank ordering. Rationale: ordering is a
  "which blocker matters most" priority judgment the agent must not make unilaterally; a
  later owner-supplied ordering would be a separate, out-of-scope input. Reversible: easy.

## Out of Scope

- Any runtime code, validator, or new `retail check` rule.
- Any live publish path, Power BI execution, or F016 adapter dependency.
- Any new roadmap feature row or any change to Stage 7 pass conditions.
- Any pharmacy/C086-specific content inside the generic template.
- Any new rollup, segment, or grouping not already present in the F7 domain files.
- Restating the engineer-facing handoff pack.
