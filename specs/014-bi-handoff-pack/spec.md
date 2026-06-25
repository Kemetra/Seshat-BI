# Feature Specification: BI Handoff Pack

**Feature Branch**: `014-bi-handoff-pack`

**Created**: 2026-06-24

**Status**: Implemented (commit `f00ff13`, 2026-06-25) -- shipped to `main`

**Roadmap**: F013 (Layer 6 -- Dashboard & Delivery). Advances readiness stage
**Publish Ready** (stage 7 of 7).

**Input**: User description: "The documentation/evidence bundle handed to a BI
consumer -- the template/checklist defining what a complete handoff contains
(metric contracts, readiness scorecard, reconciliation evidence, known data
issues, approvals). Publish Ready requires the prior stages pass; this feature
does NOT publish to a workspace and does NOT invoke pbi-cli."

## Overview

The **BI Handoff Pack** is the committed documentation/evidence bundle a BI
consumer receives when a table/report reaches **Publish Ready** (stage 7). This
feature delivers the **template and checklist** that define what a *complete*
handoff contains -- it does NOT publish, deploy, or author Power BI artifacts.

The pack **composes existing readiness evidence**; it invents nothing. Every
section of the pack points at an artifact that already exists from an earlier
stage (the metric contracts from stage 5, the reconciliation report from stage
4, the readiness scorecard from the spine, the data-issues log). The pack adds
one thing on top: a **handoff review checklist** and a recorded **publish
approval** (a named human sign-off), per `docs/readiness/publish-ready.md`.

This is a **docs/templates-first** slice (hard rule #8): the handoff is a doc +
a status entry before it is ever code. No validator, no automation, no
publishing path is built here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assemble a complete handoff pack from existing evidence (Priority: P1)

A BI analyst has taken a table all the way to `dashboard_ready: pass` and now
needs to hand it to a BI consumer (a report builder, a downstream team, a
data-owner who will authorize publish). The analyst copies the handoff-pack
template, fills its index by pointing each required section at the
already-committed evidence artifact, and works the handoff-review checklist.

**Why this priority**: This is the feature. Without a single, legible bundle
that says "here is everything a consumer needs and here is the evidence behind
each claim," the Publish Ready gate has no concrete deliverable. This story is
the MVP: the pack template + the checklist.

**Independent Test**: Copy `templates/handoff/bi-handoff-pack.md` for a generic
`<schema>.<table>`, fill each index row with a path to an existing readiness
artifact, and confirm the checklist can be walked end to end and every required
item resolves to a committed file (or is explicitly recorded as a gap). Delivers
a reviewable bundle with zero invented content.

**Acceptance Scenarios**:

1. **Given** a table at `dashboard_ready: pass` with all prior-stage artifacts
   committed, **When** the analyst fills the handoff-pack template, **Then**
   every required section resolves to an existing committed artifact path and no
   section fabricates new data, metrics, or confidence.
2. **Given** the filled pack, **When** the handoff-review checklist is walked,
   **Then** each checklist item is either satisfied (with evidence cited) or
   recorded as an explicit gap in the pack's "Known data issues / caveats"
   section -- never silently skipped.
3. **Given** a pack whose reconciliation section points at an *unfilled*
   `reconciliation-report.md`, **When** the checklist runs, **Then** the pack
   cannot reach "complete" and the gap is recorded as a blocking reason for
   `publish_ready`.

---

### User Story 2 - Record the publish approval as a named human sign-off (Priority: P1)

A data-owner / governance reviewer reads the assembled pack and decides whether
to authorize publishing the table/report to consumers. Their decision is
recorded as a named, dated sign-off in the readiness status `approvals[]` for
stage `publish_ready` -- the agent cannot self-grant it (Principle V).

**Why this priority**: Publish Ready `pass` is meaningless without a recorded
human authorization. The approval is the one thing the pack adds that is not
inherited evidence; it is the gate's teeth. Co-equal P1 with US1 because a pack
with no approval is not a handoff -- it is a draft.

**Independent Test**: Walk the approval section of the checklist for a generic
table: confirm the template provides the exact `approvals[]` shape (`stage:
publish_ready`, `owner`, `at`), confirm the agent-must-not list forbids
self-granting, and confirm that an absent approval is recorded as a blocking
reason rather than auto-promoting to `pass`.

**Acceptance Scenarios**:

1. **Given** an assembled pack and a data-owner who has reviewed it, **When**
   the owner signs off, **Then** the sign-off is recorded in
   `readiness-status.yaml` `approvals[]` as `{stage: publish_ready, owner:
   <data_owner|governance>, at: <YYYY-MM-DD>}` and cited in the pack.
2. **Given** an assembled pack with no recorded approval, **When** readiness is
   evaluated, **Then** `publish_ready` is `blocked` with reason "no recorded
   publish approval" -- it does NOT become `pass`.
3. **Given** an agent driving the workflow, **When** it reaches the approval
   step, **Then** it STOPS and requests the named human owner -- it never writes
   the approval itself.

---

### User Story 3 - Honest caveats: PII, returns handling, known gaps, out-of-scope (Priority: P2)

The pack's "Known data issues / caveats" section forces the handoff to state,
in plain language, what the deployed data does and does NOT carry: which columns
were dropped for PII safety, how returns/refunds are handled, which rows land on
a `-1` unknown member, and what is explicitly out of scope. These are pulled
from the existing `data-issues.md` log and the `assumptions.md`/`caveats`
evidence -- the pack composes them, it does not re-decide them.

**Why this priority**: A handoff that hides caveats is worse than no handoff --
it ships unstated assumptions to a consumer who will build on them. P2 because
US1 already provides the section's slot; this story makes the caveats
*mandatory and honest* rather than optional. The grain/PII/rollup/identity
decisions behind these caveats are human calls (Principle V) and are recorded,
not invented, by the pack.

**Independent Test**: Confirm the template's caveats section requires (a) a PII
exclusion statement, (b) a returns/refunds handling statement, (c) the
known-gaps list sourced from `data-issues.md`, and (d) an out-of-scope list; and
confirm the checklist FAILS the pack if any of these four is missing.

**Acceptance Scenarios**:

1. **Given** a pack whose caveats omit the PII-exclusion statement, **When** the
   checklist runs, **Then** the pack is incomplete and `publish_ready` is
   `blocked` (per `publish-ready.md` blocking reasons).
2. **Given** the `data-issues.md` log records N rows on a dimension's `-1`
   unknown member, **When** the caveats are filled, **Then** that known gap
   appears verbatim (with its measured count) in the pack's caveats -- never
   softened to an adjective.
3. **Given** a returns/refunds handling decision recorded in `assumptions.md`,
   **When** the caveats are filled, **Then** the pack states the handling and
   cites the assumption; it does not re-derive or change it.

---

### User Story 4 - Data dictionary against the DEPLOYED schema (Priority: P3)

The pack includes a column-by-column data dictionary for the consumer, written
against the **deployed** `gold.<...>` schema (the star + the governed model),
not against an aspirational design. Each column row carries name, type, grain
role (fact measure / dimension attribute / degenerate dim), and a one-line
business meaning sourced from existing mapping artifacts.

**Why this priority**: The consumer needs to know what each column means to use
the model correctly. P3 because the dictionary is largely a transcription of the
deployed schema + existing `source-map.yaml` semantics; it is valuable but the
pack is already a viable handoff (US1/US2/US3) without the full per-column
detail.

**Independent Test**: Confirm the template provides a column-by-column table keyed
to the deployed `<schema>.<table>`, with columns for name/type/role/meaning, and
that the checklist requires the dictionary to match the deployed schema (a
dictionary that lists a column not in the deployed table, or omits one, FAILS).

**Acceptance Scenarios**:

1. **Given** a deployed `gold` star, **When** the data dictionary is filled,
   **Then** every deployed column appears exactly once and no non-deployed
   column is listed.
2. **Given** a column's business meaning recorded in `source-map.yaml`, **When**
   the dictionary is filled, **Then** the meaning is carried from that artifact,
   not invented at handoff time.

---

### Edge Cases

- **A prior stage is not `pass`.** The pack MUST NOT be marked complete. The
  handoff index records the missing prior-stage evidence as a blocking reason;
  `publish_ready` stays `blocked` (publish-ready.md: "any prior stage not
  pass").
- **Reconciliation evidence exists but is FAIL or unfilled.** The pack records
  the reconciliation result honestly; an unfilled or FAIL reconciliation blocks
  completion. The pack MUST NOT edit totals or the schema to make it "tie"
  (publish-ready.md agent-must-not list).
- **A non-fatal gap is present (e.g. a caveat marked TBD).** The pack may be
  assembled with the gap recorded as a `warning`, but a `warning` MUST NOT
  auto-promote to `pass` (publish-ready.md statuses).
- **Numeric "confidence" requested.** The pack MUST NOT emit a fabricated
  confidence number. Readiness is the four explicit statuses + evidence +
  blockers (Principle "No fake confidence"; constitution Readiness System).
- **Consumer asks for a metric not in the contracts.** The pack does not invent
  it. New metrics go back through the metric-contract store (stage 5), not the
  handoff (rule #5 / dashboard-ready.md).
- **C086 (or any worked example) specifics.** The template and checklist stay
  generic; worked-example billing codes, segments, PII columns, and grain keys
  live in that example's own artifacts (Principle VII / rule #7).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST deliver a generic, copy-per-table handoff-pack
  template at `templates/handoff/bi-handoff-pack.md` whose every required
  section points at an EXISTING committed readiness artifact (composes, does not
  invent).
- **FR-002**: The feature MUST deliver a handoff-review CHECKLIST (the
  completeness gate) that a human walks before publish -- as a docs artifact, NOT
  as runtime code or a new validator.
- **FR-003**: The handoff pack MUST require these sections, each resolving to an
  existing artifact: (a) **Metric contracts** (from stage 5, F009/F010); (b)
  **Readiness scorecard** (`templates/readiness-scorecard.md` filled instance);
  (c) **Reconciliation evidence** (`mappings/<table>/reconciliation-report.md`,
  filled); (d) **Known data issues / caveats** (`data-issues.md` +
  `assumptions.md`); (e) **Data dictionary** against the deployed schema; (f)
  **Publish approval** (recorded sign-off).
- **FR-004**: The caveats section MUST require an explicit statement of: PII
  exclusion, returns/refunds handling, known gaps (with measured counts from
  `data-issues.md`), and out-of-scope items. A missing one MUST fail the
  checklist (publish-ready.md blocking reasons).
- **FR-005**: The publish approval MUST be recorded as a named, dated human
  sign-off in `readiness-status.yaml` `approvals[]` for stage `publish_ready`.
  The agent MUST NOT self-grant it (Principle V).
- **FR-006**: The pack MUST NOT mark `publish_ready: pass` while any prior stage
  (1-6) is not `pass`, or while caveats/reconciliation/approval are missing
  (publish-ready.md statuses + blocking reasons).
- **FR-007**: A non-fatal gap MUST be recordable as a `warning` that does NOT
  auto-promote to `pass`.
- **FR-008**: The feature MUST NOT publish to any workspace, MUST NOT invoke
  pbi-cli / PBIP automation, and MUST NOT deploy to Fabric (hard rule #6; F016
  is the last, gated adapter).
- **FR-009**: The template, checklist, and stage doc MUST stay generic -- no
  C086/pharmacy specifics; the worked example is cited by reference only
  (Principle VII / rule #7).
- **FR-010**: The pack MUST NOT emit a fabricated confidence number; readiness
  is expressed as the four explicit statuses + evidence + blockers
  (constitution "No fake confidence"; rule #9).
- **FR-011**: The data dictionary MUST be written against the DEPLOYED
  `<schema>.<table>` and MUST match it (every deployed column once; no
  non-deployed column) -- per publish-ready.md "data dictionary does not match
  the deployed schema" blocking reason.
- **FR-012**: All delivered artifacts MUST be ASCII, UTF-8 without BOM, and use
  repo-relative paths kept short for Windows `MAX_PATH` (Principle IX).
- **FR-013**: The feature MUST update `docs/readiness/publish-ready.md` "Required
  artifacts" / "See also" to reference the concrete pack template path, and MUST
  cross-link the pack from the readiness model's "See also" (keeping the spine's
  docs internally consistent).

### Key Entities *(include if feature involves data)*

- **BI Handoff Pack** (`templates/handoff/bi-handoff-pack.md`): the generic,
  copy-per-table bundle index. Attributes: table identity, an index of required
  sections each pointing at an existing artifact, the caveats block, the data
  dictionary, and the recorded approval. Composes; invents nothing.
- **Handoff-Review Checklist** (`templates/handoff/handoff-review-checklist.md`):
  the completeness gate a human walks -- one line per required pack section, each
  either "satisfied (evidence)" or "gap (recorded)". Not runtime code.
- **Publish Approval** (a record in `readiness-status.yaml` `approvals[]`): a
  named, dated human sign-off authorizing publish; the only non-inherited thing
  the pack adds.
- **Inherited evidence artifacts** (referenced, not created here): metric
  contracts (stage 5), `readiness-scorecard.md`, `reconciliation-report.md`,
  `data-issues.md`, `assumptions.md`, `source-map.yaml`, the deployed `gold`
  schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new analyst can assemble a complete handoff pack for a generic
  table using ONLY the template + checklist + already-committed evidence, with
  zero invented data, metrics, or confidence numbers.
- **SC-002**: 100% of the pack's required sections resolve to an existing
  committed artifact path (or are recorded as an explicit gap) -- there is no
  section the pack originates from nothing.
- **SC-003**: The checklist FAILS (pack incomplete) whenever any of the four
  mandatory caveats (PII / returns / known-gaps / out-of-scope), the
  reconciliation evidence, the data-dictionary-matches-schema check, or the
  publish approval is missing.
- **SC-004**: `publish_ready` never reaches `pass` without (a) all prior stages
  `pass` and (b) a recorded named publish approval -- verified by the
  publish-ready.md statuses + blocking reasons.
- **SC-005**: The delivered template + checklist + updated stage doc contain no
  worked-example specifics and pass the kit's docs conventions (ASCII, UTF-8
  no BOM, short repo-relative paths, cross-links resolve).
- **SC-006**: No publishing, pbi-cli/PBIP, or Fabric action is introduced --
  confirmed by absence of any deploy/authoring step in all delivered artifacts.

## Assumptions

- **Pack home is `templates/handoff/`.** Consistent with the existing
  `templates/` directory that houses every other readiness artifact
  (`readiness-scorecard.md`, `data-issues.md`, etc.). A per-table FILLED instance
  would live alongside the table's other working artifacts; the generic blanks
  live in `templates/`. (Auto-decision; reversible-easy.)
- **The pack is a doc + checklist, not code.** Per hard rule #8 (docs/templates
  first) and Principle VIII (static-first). No validator, no automation is built
  in this slice. (Auto-decision.)
- **Metric contracts (stage 5, F009/F010) are referenced as an input, not built
  here.** The pack assumes they exist and are committed by the time a table is
  at `dashboard_ready: pass`. If they are not yet defined, the pack records that
  as a blocking gap. (Auto-decision; reversible-easy.)
- **Publish approval is recorded in `readiness-status.yaml` `approvals[]`.** This
  reuses the existing approval mechanism (publish-ready.md "Required owner");
  no new approval store is introduced. (Auto-decision.)
- **The reconciliation evidence is the FILLED `mappings/<table>/reconciliation-report.md`
  instance** from stage 4 / feature 004 (NOT the blank `templates/` template); the pack
  references that filled instance, it does not re-run validation. (Auto-decision.)
- **Out of scope (this slice):** publishing/deployment, pbi-cli/PBIP authoring,
  Fabric, a new validator or `retail check` rule, automated approval, and any
  scoring/confidence number (rules #6, #8, #9; constitution Scope Boundaries).
- **Human-decided inputs the pack RECORDS but does NOT decide** (Principle V):
  PII publish-safety (which columns are safe to ship), business-rollup / segment
  mappings, product/grain identity. The pack carries these from existing
  artifacts and the human approval; it never invents them. See the spec's
  open-for-human items.
