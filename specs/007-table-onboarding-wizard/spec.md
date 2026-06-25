# Feature Specification: table onboarding wizard -- the Source -> Mapping readiness workflow

**Feature Branch**: `007-table-onboarding-wizard` (roadmap feature F006; work per session convention, located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Implemented (commit `f75159e`, 2026-06-25) -- shipped to `main`

**Input**: "Roadmap F006 (Layer 1-2). Advances readiness stage: Source -> Mapping. An agent-first workflow/skill that walks a NEW table through profile -> business-meaning -> source-map -> the source-mapping gate, producing the per-table readiness artifacts and stopping at the Principle-V human seams (grain, PII, business rollup, identity). Agent-first not CLI-first (hard rule #1). No source goes directly to silver (hard rule #2): the wizard ENDS at Mapping Ready, it does not build silver. Docs/templates/checklist first (hard rule #8). Generic only -- no C086/pharmacy specifics (hard rule #7). Aligns to docs/readiness/source-ready.md and mapping-ready.md and the readiness spine (4 statuses + evidence + blockers, no fake confidence)."

## Why this feature exists

The roadmap (F006, Layers 1-2) names the **table onboarding wizard**: the
agent-first workflow that advances a brand-new table across the first readiness
transition, **Source Ready (Stage 1) -> Mapping Ready (Stage 2)**. The kit
already ships the verb that authors the mapping artifacts (the `source-mapping`
skill) and the conductor that sequences all verbs end-to-end (`retail-orchestrate`,
spec 005). What is missing is the **onboarding-shaped front door**: a single,
legible "I have a new raw table, walk me from nothing to a reviewed map" workflow
that is explicit about the readiness stage it advances, that produces the per-table
readiness-status record alongside the mapping artifacts, and that STOPS cleanly at
Mapping Ready without ever drifting into silver.

This wizard is not a new gate and not a second mapping method. It is the
**stage-scoped composition** of existing pieces -- `source-ready.md`,
`mapping-ready.md`, the `source-mapping` skill, and the `readiness-status.yaml`
template -- assembled into the one onboarding journey a human (or the conductor)
invokes when a table first appears. Per hard rule #8 it ships as a SKILL +
CHECKLIST + a readiness-status seed, not as code.

## Where this sits (and what it is NOT)

| Surface | What it does | Relationship to this wizard |
|---------|--------------|-----------------------------|
| `source-mapping` skill | profile -> author the five mapping artifacts -> stop at the gate | the wizard CALLS it as Step B; the wizard does not re-implement mapping |
| `retail-orchestrate` (F005) | sequences ALL verbs profile -> map -> build -> validate -> Power BI; self-heals against the gate | the wizard is the FIRST leg only (Source -> Mapping); the conductor may invoke the wizard, or a human may invoke it directly for one table |
| `retail-build-warehouse` (F006/spec-006) | authors silver/gold SQL from an APPROVED map | strictly DOWNSTREAM of this wizard; the wizard hard-stops before it |
| This wizard (007 / roadmap F006) | walks a NEW table Source-Ready -> Mapping-Ready, seeds the readiness-status, stops at the human seams | the onboarding front door for ONE table's first two stages |

The wizard is **agent-first** (hard rule #1, Principle I): it is a procedure the
agent performs, with `retail check` / the profile read-only connection as gates it
CALLS. It is **not** a CLI subcommand and adds no Python runtime.

## The stage boundary this feature respects (the load it carries)

- **It ENTERS at Source Ready and EXITS at Mapping Ready.** The terminal state is
  Mapping Ready with the three gate artifacts committed and `Gate status: CLEARED`
  iff a human has approved -- or, more commonly, `blocked` with recorded
  `blocking_reasons[]` parked at a Principle-V seam. Either terminal state is a
  SUCCESSFUL wizard run; clearing the gate is the human's act, not the wizard's.
- **It NEVER crosses into Silver Ready** (hard rule #2, Principle IV). No
  `silver.*` SQL, no migration, no call to `retail-build-warehouse`. The wizard's
  last action is to emit the `reconciliation-report.md` blank, write/update the
  readiness-status, state the next allowed action, and STOP.
- **It NEVER self-grants approval or invents a judgment call** (Principle V). The
  four reserved seams -- grain, PII publish-safety, business rollup/segment
  mapping, product identity -- are PROPOSED with evidence and raised as
  `unresolved-questions.md` rows; the wizard stops there. (See Deferred /
  open-for-human, below.)
- **No fake confidence.** Readiness is the four explicit statuses
  (`not_started` | `blocked` | `warning` | `pass`) + `evidence[]` +
  `blocking_reasons[]`. The wizard emits no numeric confidence score
  (readiness-model.md; Principle VIII spine note).

## Architecture (a pure skill + checklist; no new code, no CLI)

The wizard is `.claude/skills/<wizard-skill-name>/SKILL.md` plus a committed
onboarding CHECKLIST under `docs/` (or `templates/`) -- agent-procedure text, the
agent is the runtime, same posture as every other verb. **Decision: pure skill +
checklist + readiness-status seed; no new Python, no `.sql`, no CLI subcommand,
no codegen.** It REUSES `source-mapping` for the mapping leg and
`templates/readiness-status.yaml` for the state seed, so the wizard's own surface
is thin: the onboarding sequence, the stage-transition bookkeeping, the
human-seam stops, and the Source-Ready -> Mapping-Ready definition-of-done.

This keeps the kit's all-skills verb architecture intact and avoids duplicating
the mapping procedure that already lives in `source-mapping`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Onboard a new table from nothing to a reviewable map (Priority: P1)

A human (or the conductor) says "onboard `<schema>.<table>`". The wizard confirms
there is no existing `mappings/<table>/`, walks the table through Stage 1
(profile + PROPOSED semantics) into Stage 2 (author the map + assumptions +
unresolved-questions), seeds `readiness-status` with `source_ready: pass` and
`mapping_ready: blocked` (pending review), emits the reconciliation blank, states
the next allowed action ("review + approve the map"), and STOPS.

**Why this priority**: this is the feature -- the single onboarding journey that
advances the Source -> Mapping transition. Without it there is no stage-scoped
front door; everything else is detail on top of this walk.

**Independent Test**: invoke the wizard on a generic placeholder table with no
prior artifacts; assert it produces `mappings/<table>/` with the five artifacts
(STRUCTURE filled; mechanical numbers from the read-only profile OR marked
`[PENDING LIVE PROFILE]` in deferred mode), a `readiness-status` record whose
`current_stage` is `mapping_ready` with `source_ready: pass` + evidence and
`mapping_ready: blocked` + a blocking reason, and a printed next-action -- and
that it wrote NO `silver.*` SQL and granted NO approval.

**Acceptance Scenarios**:

1. **Given** no `mappings/<table>/` exists, **When** the wizard runs to completion
   with a live read-only connection, **Then** Stage 1 records the mechanical
   profile numbers (row/col counts, `'' OR NULL` missingness, candidate-PK proof,
   returns-column population) into `source-profile.md` and marks `source_ready:
   pass` with that file as evidence.
2. **Given** Stage 1 is `pass`, **When** the wizard proceeds, **Then** it authors
   `source-map.yaml` + `assumptions.md` + `unresolved-questions.md` starting from
   the RC1-RC16 defaults (via the `source-mapping` skill), emits the
   `reconciliation-report.md` blank, and sets `mapping_ready: blocked` (review
   pending) -- it does NOT set `Gate status: CLEARED`.
3. **Given** the wizard has produced the artifacts, **When** it finishes, **Then**
   its final message states the single next allowed action (human review/approval)
   and explicitly confirms it wrote no silver and self-granted no approval.

### User Story 2 - Hard-stop at the Principle-V human seams (Priority: P1)

When the table presents a judgment call the agent cannot decide from data alone --
ambiguous grain (candidate PK not unique on the rows), a `pii:true` candidate, a
business rollup/segment that needs an analyst-supplied value->group table, or a
product-identity question -- the wizard PROPOSES with the supporting data fact,
raises an `unresolved-questions.md` row with a named owner, records the matching
`blocking_reasons[]` in the readiness-status, and STOPS without clearing the gate.

**Why this priority**: the stop-at-judgment floor is what keeps an agent-first
onboarding from silently inventing the very grain/PII/rollup/identity decisions
the constitution reserves for a human (Principle V). It is co-equal with US1.

**Independent Test**: feed the wizard a table whose candidate PK is NOT unique on
the data; assert it raises a grain `unresolved-questions.md` row (with the
duplicate-count evidence), records `mapping_ready: blocked` with
`blocking_reasons: ["grain not confirmed unique on data"]`, and STOPS -- it does
not pick a PK, does not collapse the grain, does not clear the gate.

**Acceptance Scenarios**:

1. **Given** a candidate PK that fails uniqueness, **Then** STOP -- raise the grain
   question; never silently choose or collapse a grain.
2. **Given** a `pii:true` candidate column, **Then** STOP -- propose the default
   (drop) and raise the PII publish-safety question for governance; never assert a
   PII ruling as fact.
3. **Given** a categorical needing a business rollup/segment, **Then** STOP -- never
   invent the value->group table; raise it for the analyst.
4. **Given** a product-identity ambiguity (which column identifies the entity, or
   two columns that disagree), **Then** STOP -- raise it; never assert identity.

### User Story 3 - Resume safely and never skip ahead (Priority: P2)

The wizard is state-based: it recomputes the current stage from what is already on
disk (mirroring the conductor's run-state rule) so a re-invocation resumes rather
than restarts, and it refuses to advance past Mapping Ready.

**Why this priority**: resumability and the no-skip-ahead guarantee make the wizard
safe to re-run (idempotent onboarding) and keep it inside its stage boundary; it is
a robustness layer on the P1 walk, not the walk itself.

**Independent Test**: run the wizard twice on the same table; assert the second run
detects the existing `mappings/<table>/` + `Gate status`, reports the current stage,
and does NOT overwrite committed artifacts or re-profile destructively; and assert
that with `Gate status: CLEARED` present the wizard reports "Mapping Ready reached"
and refuses to author any silver.

**Acceptance Scenarios**:

1. **Given** an existing `mappings/<table>/` with `Gate status: OPEN`, **When** the
   wizard re-runs, **Then** it reports the open questions and the current stage and
   does not overwrite the filled artifacts.
2. **Given** `Gate status: CLEARED` (human-approved), **When** the wizard re-runs,
   **Then** it sets `mapping_ready: pass` with the approval + artifacts as evidence,
   states "Mapping Ready reached; next stage is Silver Ready (out of this wizard's
   scope)", and STOPS -- it never authors silver.
3. **Given** no live connection / no `db` extra, **When** the wizard runs, **Then**
   it stays useful in deferred-boundary mode: copies the blanks, marks mechanical
   numbers `[PENDING LIVE PROFILE]`, records `source_ready: warning` (not `pass`),
   and still drives the semantic stop-and-ask.

### Edge Cases

- **Table already partly onboarded** (some artifacts present, some missing): the
  wizard resumes from the first incomplete artifact; it never clobbers a committed
  one (immutability of reviewed work).
- **Source Ready never reached** (a required mechanical number is unmeasurable):
  the wizard records `source_ready: blocked` with the concrete reason and does NOT
  enter Stage 2 (no mapping on an unprofiled source).
- **Human approves in the same session**: the wizard still does not self-grant; it
  reads the human's recorded `Gate status: CLEARED` + `approvals[]` entry and only
  THEN promotes `mapping_ready` to `pass`.
- **Deferred-boundary mode** (no DSN / no `db` extra): `source_ready` is at most
  `warning`, never `pass`, because the mechanical numbers are `[PENDING LIVE
  PROFILE]` -- the wizard must not fabricate them (Principle VIII).
- **Conflicting answers** (an analyst answer contradicts a profiled data fact): the
  wizard surfaces the conflict and stops to reconcile rather than proceeding
  (Principle V evidence-cross-check).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/<wizard-skill-name>/SKILL.md` (ASCII, UTF-8 no
  BOM, valid frontmatter) describing the agent-first onboarding workflow. No new
  Python, no `.sql`, no CLI subcommand, no codegen.
- **FR-002**: Add a committed onboarding CHECKLIST (`docs/readiness/onboarding-checklist.md`,
  beside the stage docs it mirrors) enumerating the Source-Ready -> Mapping-Ready steps and their
  definition-of-done, so the journey is reviewable as text first (hard rule #8).
- **FR-003**: The wizard MUST compute current state from disk first (presence of
  `mappings/<table>/`, the artifacts, and `Gate status`) and resume rather than
  restart -- it MUST NOT create a separate run-state file (consistent with the
  `retail-orchestrate` run-state rule).
- **FR-004**: Stage 1 (Source Ready) -- the wizard drives the mechanical profile
  over a READ-ONLY connection and records row/col counts, `'' OR NULL` missingness
  (never `IS NULL` alone, RC5), candidate-PK uniqueness proof, and returns-column
  population into `mappings/<table>/source-profile.md`; semantic rows are PROPOSED,
  not invented. Definition-of-done = `source-ready.md`'s `pass` criteria.
- **FR-005**: Stage 2 (Mapping Ready) -- the wizard delegates artifact authoring to
  the `source-mapping` skill (it does NOT duplicate that procedure): author
  `source-map.yaml` + `assumptions.md` (RC1-RC16 adopted/deviated, each deviation
  citing a data fact) + `unresolved-questions.md`, and emit the
  `reconciliation-report.md` blank. Definition-of-done = `mapping-ready.md`'s
  artifact set present and filled.
- **FR-006**: The wizard MUST seed/update a per-table readiness-status from
  `templates/readiness-status.yaml`: `source_ready` (`pass` | `warning` | `blocked`
  with evidence/blockers), `mapping_ready` (`blocked` until human approval, then
  `pass`), `current_stage`, `next_action`, and `last_checked_at`/`checked_by`.
  Every `pass` MUST carry `evidence[]`; every `blocked` MUST carry
  `blocking_reasons[]`; NO numeric confidence score is emitted.
- **FR-007**: The wizard MUST carry a fail-loud human-seam table -- grain ambiguity
  (PK not unique), PII publish-safety, business rollup/segment mapping, and product
  identity -- where each is a HARD-STOP that raises an `unresolved-questions.md` row
  with a named owner and a supporting data fact, and is NEVER satisfiable by a
  silent agent default. (These four are the open-for-human seams; the wizard
  proposes, the human decides.)
- **FR-008**: The wizard MUST hard-stop at the Mapping Ready boundary (Principle IV,
  hard rule #2): it writes NO `silver.*` SQL, calls NO build verb, and self-grants
  NO approval / `Gate status: CLEARED`. Its terminal output states the single next
  allowed action and which surface owns it (human review, then Silver Ready /
  `retail-build-warehouse`, both out of scope here).
- **FR-009**: The wizard MUST stay GENERIC (hard rule #7, Principle VII): no
  C086/pharmacy specifics (no billing codes, segments, PII column names, or grain
  keys) in the skill, checklist, or status seed -- placeholders only, citing the
  C086 worked example as the filled instance, never copying it.
- **FR-010**: Append a `## Orchestration` pointer to the wizard skill and add a
  reciprocal pointer from `retail-orchestrate` so the conductor invokes the wizard
  as its Source -> Mapping leg. The wizard stays single-purpose (it does its leg and
  STOPS); the cross-table self-heal loop stays only in `retail-orchestrate`.
- **FR-011**: Deferred-boundary honesty: with no DSN / no `db` extra the wizard does
  NOT traceback and does NOT fabricate numbers -- it marks mechanical profile rows
  `[PENDING LIVE PROFILE]`, records `source_ready: warning` (never `pass`), prints
  the enable steps (`pip install 'retail[db]'`; set `DATABASE_URL` in the
  git-ignored `.env`; never commit a real DSN), and still drives the semantic
  stop-and-ask and the gate stop (Principle VIII, Principle IX).

### Key Entities

- **Onboarding wizard skill** (`.claude/skills/<wizard-skill-name>/SKILL.md`): the
  agent-first Source -> Mapping workflow; the agent is the runtime.
- **Onboarding checklist** (committed at `docs/readiness/onboarding-checklist.md`): the
  text-first, reviewable definition-of-done for each stage transition.
- **Readiness-status record** (one per table, from `templates/readiness-status.yaml`):
  the seeded state the wizard writes -- `source_ready` + `mapping_ready` statuses,
  evidence, blockers, `current_stage`, `next_action`. No fake confidence number.
  **Canonical filled location: `mappings/<table>/readiness-status.yaml`** (ADR 0004;
  co-located with the mapping artifacts per ADR 0003, spans all seven stages). The
  wizard is the FIRST writer of this file -- it seeds the ratified path, not a default.
- **The five mapping artifacts** (`mappings/<table>/`): produced by the delegated
  `source-mapping` leg -- `source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`, `reconciliation-report.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/<wizard-skill-name>/SKILL.md` and the onboarding
  checklist exist, are ASCII + UTF-8 no BOM, the skill has valid frontmatter and is
  registered by the harness, and they contain ZERO C086/pharmacy specifics
  (generic placeholders only).
- **SC-002**: `retail check` stays exit 0 (current rule count) with the new skill +
  checklist + status seed added; the full unit suite stays green; no new Python is
  added and `dependencies = []` is unchanged.
- **SC-003**: A generic onboarding dry-run produces, for a placeholder table, the
  five `mappings/<table>/` artifacts (structure filled) and a readiness-status whose
  `current_stage` is `mapping_ready`, `source_ready` is `pass` (or `warning` in
  deferred mode) with evidence, and `mapping_ready` is `blocked` with a blocking
  reason -- and the run wrote NO `silver.*` and granted NO approval.
- **SC-004**: For each of the four human seams (grain, PII, business rollup, product
  identity), the wizard demonstrably HARD-STOPS -- raising an
  `unresolved-questions.md` row with a named owner + supporting data fact and
  recording the matching `blocking_reasons[]` -- and never auto-answers it.
- **SC-005**: Reaching Mapping Ready is documented as the wizard's terminal state:
  the wizard explicitly states that Silver Ready (and `retail-build-warehouse`) are
  the next stage and OUT of this wizard's scope, and never authors silver.

## Assumptions

- Pure skill + checklist + readiness-status seed (no codegen / templates engine /
  CLI) -- onboarding is a composition of existing verbs, so a new runtime buys ~zero
  at this stage (YAGNI, hard rule #8).
- The wizard DELEGATES the mapping-artifact authoring to the existing
  `source-mapping` skill rather than duplicating it; its own surface is the
  stage-transition walk, the readiness-status bookkeeping, and the human-seam stops.
- The readiness-status template (`templates/readiness-status.yaml`) is the state
  seed; this feature uses it, it does not redefine it.
- Reaching Mapping Ready (gate artifacts present; `blocked` pending human review, or
  `pass` once a human approves) is a SUCCESSFUL terminal state. Clearing the gate /
  setting `Gate status: CLEARED` is the human's action, recorded in `approvals[]`.
- Deferred-boundary mode is expected and supported: no live DB means `source_ready`
  is at most `warning`; the wizard never fabricates profile numbers.
- The exact skill name and the checklist's home directory are settled in plan.md
  (auto-defaulted here; reversible -- see the decision record).

## Deferred decisions (future specs / issues -- recorded, not built)

- **The four Principle-V judgment calls are OUT OF SCOPE to answer here** and are
  the open-for-human seams: (1) the table's GRAIN (which is the right row level /
  candidate PK), (2) PII publish-safety (which columns are PII and whether dropping
  is the right handling), (3) the BUSINESS ROLLUP / segment value->group mapping,
  and (4) PRODUCT IDENTITY (which column authoritatively identifies the entity).
  The wizard PROPOSES each with evidence and STOPS; a human decides.
- **Driving multiple tables / cross-table conformed-dimension onboarding** -- the
  wizard onboards ONE table's first two stages; batch onboarding and conformed-dim
  reconciliation across tables are a later concern (the conductor / a future spec).
- **A grain-confidence surface and a mapping-version diff** (roadmap F008) -- the
  wizard records grain as `pass`/`blocked` with evidence, not a confidence score;
  surfacing grain-uniqueness confidence and diffing mapping versions is F008.
- **Automating the Source Drift check on re-onboarding** (roadmap F014) -- detecting
  when a re-onboarded source has drifted from its prior profile is deferred; the
  wizard for now resumes from committed artifacts without a drift diff.
- **Any CLI subcommand** (e.g. a `retail onboard` verb) -- explicitly NOT built;
  the wizard is agent-first (hard rule #1). Recorded should a CLI gate ever be wanted.

## See also

- The two stages this feature spans: `docs/readiness/source-ready.md`,
  `docs/readiness/mapping-ready.md`.
- The spine + state model: `docs/readiness/readiness-model.md`,
  `docs/readiness/readiness-pipeline.md`; `templates/readiness-status.yaml`.
- The delegated mapping leg: `.claude/skills/source-mapping/SKILL.md`.
- The conductor that invokes this leg: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md`.
- The downstream build verb (out of scope here): `.claude/skills/retail-build-warehouse/SKILL.md`;
  `specs/006-warehouse-builder/spec.md`.
- The roadmap row: `docs/roadmap/roadmap.md` (F006, Layers 1-2, Source -> Mapping).
- Principles: `.specify/memory/constitution.md` I (Agent-First), IV (Source Mapping
  Before Silver), V (Agent Stops at Judgment Calls), VII (C086 Is An Example),
  VIII (Static-First / no fake confidence), IX (Secrets/Reproducibility).
- The first filled instance (an example, never the schema): `docs/worked-examples/c086-pharmacy.md`.
