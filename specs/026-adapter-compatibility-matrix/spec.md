# Feature Specification: Adapter Compatibility Matrix -- the version-truth record the maintenance policy enforces against

**Feature Branch**: `026-adapter-compatibility-matrix`  **Roadmap feature**: F032

> Numbering note (spec-dir vs roadmap F-number): the roadmap F-number is the
> authoritative identity; the spec-directory number is the next free on-disk slot.
> This spec is on-disk slot 026 and roadmap feature F032. When the directory number
> and the F-number disagree, the roadmap F-number wins. Sibling specs in this batch:
> F024=018, F025=019, F026=020, F027=021, F028=022, F029=023, F030=024, F031=025,
> F032=026 (this spec), F033=027.

**Created**: 2026-06-25

**Status**: Planned (spec only -- no runtime code this slice)

**Input**: "Roadmap F032 (Category: Maintenance Automation per F024). Track the
SUPPORTED versions and required smoke tests for every adapter the kit depends on --
the kit itself, Python, Postgres, dbt-core, dbt-postgres, Dagster, dagster-dbt, the
Power BI PBIP/TMDL assumptions, and the Power BI MCP execution adapter status. The
matrix is the durable RECORD of what is verified-compatible; the F031 maintenance
policy is the POLICY that enforces against it. Every adapter carries a version range
and a named smoke test; an UNKNOWN version is marked unknown, NEVER assumed
compatible (hard rule #9 / Principle IX). Docs/templates first (rule #8). Generic
(#7). Readiness stage affected: none directly. This is the F031 half of the
record/policy pair."

## Why this feature exists

The kit is acquiring external adapters -- a dbt transformation adapter (F029), a
Dagster orchestration adapter (F030), and the parked Power BI execution adapter
(F016). Each adapter pins the kit to a set of external tools (Python, Postgres,
dbt-core, dbt-postgres, Dagster, dagster-dbt) whose versions move independently of
the kit. Today there is no single, committed answer to "which version of each of
these is actually verified to work with this kit, and what smoke test proves it?"
Without that record, two failure modes appear: a dependency-update PR silently
bumps a tool past a tested boundary, and an agent (or human) assumes an untested
version "probably works" because nothing says otherwise.

This feature is that record: the **adapter compatibility matrix** -- a committed,
reviewable table that, for every adapter the kit depends on, states the SUPPORTED
version range, the REQUIRED smoke test, the LAST VERIFIED date, and the OWNER who
attested it. It is the version-truth the F031 maintenance policy enforces against:
F032 is the record; F031 is the policy.

It belongs to the Maintenance Automation category defined by F024 (Companion Tools
Architecture): tooling that keeps the kit durable over time without being part of
the readiness spine. The matrix advances no readiness stage; it protects the kit's
ability to run the stages at all.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It is a RECORD, not a POLICY.** F032 stores supported version ranges + smoke-test
  status + last-verified dates + owners. It does NOT gate a PR, does NOT block a
  merge, does NOT fail a build, does NOT run in CI as an enforcing check. The PR-time
  enforcement ("a dependency-update PR must update the matrix") is the F031
  maintenance policy's job. F032 supplies the truth F031 reads; F031 decides what to
  do when a PR violates it. Keeping this boundary clean is itself a requirement
  (see "Relationship to shipped features").
- **It TRACKS adapters; it does not BUILD them.** F032 records the supported versions
  of the dbt adapter (F029), the Dagster adapter (F030), and the Power BI execution
  adapter (F016). It MUST NOT author, modify, or execute any of those adapters'
  runtime code, connection logic, or transformations. It names them and pins their
  version boundaries; the adapters own their own implementation.
- **It RECORDS smoke tests; it does not AUTHOR or RUN them.** For each adapter the
  matrix names the REQUIRED smoke test and records its last result + date. Writing
  the smoke-test code, executing it, or wiring it into CI is runtime work owned by the
  adapter features and a later automation slice. F032 records that a smoke test is
  required and what its last verified outcome was; it does not produce or invoke it.
- **No fake confidence; UNKNOWN is never "compatible".** This is hard rule #9 /
  Principle IX, instantiated for this feature. An untested version, an unverified
  range, or a cell with no smoke-test evidence is recorded as `unknown` -- NEVER as
  supported, NEVER as `pass`, NEVER inferred from "it probably works". A numeric
  compatibility score is forbidden; the matrix carries explicit status + evidence
  (smoke-test result + last-verified date + owner) only.
- **Planning artifacts only (this slice).** This slice writes the five Spec-Kit
  planning files and nothing else. The two repository deliverables
  (`docs/operations/adapter-compatibility-matrix.md`, `templates/adapter-version-record.md`)
  are FUTURE outputs ENUMERATED here, not created now. No runtime code, no CI config,
  no dbt/Dagster/Power BI files.
- **Generic.** No worked-example specifics (no C086 / retail_store_sales billing
  codes, segments, PII column names, grain keys). C086 is a filled instance cited as
  a reference, never baked in (Principle VII / roadmap rule 7). Concrete version
  strings in any future filled matrix are environment facts, not pharmacy specifics --
  but this planning slice carries generic field shapes and `<placeholder>` examples
  only.

## Relationship to shipped features (scope delta)

The matrix sits among several already-specified or already-shipped features and must
not duplicate or override any of them. Cited by roadmap F-number (the authoritative
identity); sibling specs in this batch are drafted in parallel, so they are cited by
identity, not by assumed content.

| Feature | What it owns | F032's delta (what F032 does NOT do) |
|---------|--------------|--------------------------------------|
| F024 Companion Tools Architecture | defines the Maintenance Automation category + the companion-vs-core authority rule | F032 is one entry IN that category; it does not redefine the category or the authority rule |
| F031 Adapter Maintenance Policy | the POLICY: what a dependency-update PR must do, when to re-verify, the enforcement procedure | F032 is the RECORD the policy reads + writes against; F032 enforces nothing |
| F029 dbt Transformation Adapter | the dbt adapter's runtime/build | F032 records dbt-core + dbt-postgres supported ranges + smoke test; it does not build or run the adapter |
| F030 Dagster Orchestration Adapter | the Dagster adapter's runtime/build | F032 records Dagster + dagster-dbt supported ranges + smoke test; it does not build or run the adapter |
| F016 Power BI Execution Adapter | the parked, execution-only Power BI MCP / connection adapter | F032 records the Power BI PBIP/TMDL assumptions + the MCP adapter STATUS (e.g. `parked`/`unknown`); it does not unpark, build, or execute it |
| F005 Retail Readiness Model | the seven-stage readiness spine + readiness-status.yaml | F032 advances NO spine stage; it uses the four-status vocabulary (`not_started`/`blocked`/`warning`/`pass`) plus `unknown` for the compatibility sense, never a score |

The single biggest design risk is scope-bleed from the RECORD into the POLICY (F031)
or into the ADAPTERS (F029/F030/F016). The spec holds that boundary explicitly in
every section: F032 states what is verified; it never decides what to do about it and
never touches an adapter's implementation.

## Architecture (planning posture: docs + one template; no runtime code this slice)

Consistent with the docs/templates-first posture (Principle VIII; roadmap rule #8),
the planned shape of F032 is **one operations doc + one generic record template**, with
the agent as the runtime that fills the template from verified evidence:

- A matrix DOC (`docs/operations/adapter-compatibility-matrix.md`) -- the single
  committed table: one row per adapter/dependency, columns for supported version
  range, required smoke test, smoke-test status, last-verified date, and owner; plus
  the rules (UNKNOWN-is-not-compatible, range-required, smoke-test-required, the
  record/policy boundary, how F031 reads it).
- A record TEMPLATE (`templates/adapter-version-record.md`) -- the generic, copy-me
  shape of ONE adapter's entry (the unit a future dependency-update PR fills/updates),
  in the authoring style of the existing readiness/issue templates.

This planning slice creates NEITHER of those files. It writes only the five Spec-Kit
files (spec.md, plan.md, tasks.md, checklists/acceptance.md, checklists/governance.md)
that PLAN them. There is no Python, no CLI subcommand, no `retail check` rule, no CI
job, no dbt/Dagster/Power BI artifact in this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record one adapter's supported version range + smoke test (Priority: P1)

A maintainer (or the agent on their behalf) takes the `adapter-version-record.md`
template and fills it for ONE adapter/dependency: the supported version range, the
required smoke test, the smoke-test's last result, the last-verified date, and the
named owner who attested it. The filled record is committed and reviewable.

**Why this priority**: a single filled record is the atomic unit of the matrix --
without one adapter's verified range + smoke test, there is nothing for the policy
(F031) to enforce against. This is the MVP of the record.

**Independent Test**: take the planned template, fill it for a GENERIC adapter (e.g.
"the transformation adapter against a generic <tool> version range"); confirm it
carries a version RANGE (not a single point with the rest left blank), a NAMED smoke
test, a smoke-test status from the allowed set, a last-verified date, and a named
owner -- with no C086 / pharmacy specifics and no numeric compatibility score.

**Acceptance Scenarios**:

1. **Given** the `adapter-version-record.md` template, **When** a maintainer fills it
   for one adapter, **Then** the result carries a supported version range, a named
   required smoke test, a smoke-test status, a last-verified date, and a named owner,
   and reads as a RECORD (no enforcement logic, no adapter code).
2. **Given** an adapter whose version has been verified by running its smoke test,
   **When** the record is filled, **Then** the smoke-test status is `pass`, the
   evidence cites the smoke test + its run date, and the owner who attested is named.
3. **Given** an adapter whose smoke test has NOT been run against a version, **When**
   the record is filled, **Then** that version is `unknown` -- not `pass`, not
   supported, not inferred -- and the missing smoke-test run is recorded as the blocker.

---

### User Story 2 - Assemble the full matrix across every adapter (Priority: P1)

The matrix doc lists EVERY adapter/dependency the kit pins -- Tower BI Kit version,
Python, Postgres, dbt-core, dbt-postgres, Dagster, dagster-dbt, the Power BI
PBIP/TMDL assumptions, and the Power BI MCP adapter status -- each as one row with its
supported range, required smoke test, smoke-test status, last-verified date, and
owner. No adapter is missing; no row is left without a version range or a smoke test.

**Why this priority**: the value is the COMPLETE picture -- a maintainer asking "is
this dependency-update PR within the supported set?" needs every adapter present, not
a partial list. A matrix with a missing adapter is a silent gap exactly where a PR
could regress the kit.

**Independent Test**: read the assembled matrix; confirm every one of the named
adapters/dependencies appears as a row, every row has a version range and a named
smoke test, every cell is either an explicit value or `unknown` (never blank-implies-
fine), and no row carries a numeric compatibility score.

**Acceptance Scenarios**:

1. **Given** the matrix doc, **When** it is read, **Then** it contains one row for each
   of: Tower BI Kit, Python, Postgres, dbt-core, dbt-postgres, Dagster, dagster-dbt,
   Power BI PBIP/TMDL assumptions, and Power BI MCP adapter status -- with no adapter
   absent.
2. **Given** any matrix row, **When** it is reviewed, **Then** it carries a version
   RANGE (e.g. `>=X,<Y`) and a NAMED smoke test; a row with only a single pinned point
   and no range, or with no smoke test, is a defect the review catches.
3. **Given** an adapter for which no version has yet been verified, **When** the matrix
   is assembled, **Then** that row's status is `unknown` with the missing smoke-test
   run recorded -- the row is present and honest, never omitted to hide the gap.

---

### User Story 3 - UNKNOWN is never assumed compatible (Priority: P1)

When a version, range, or adapter has not been verified by its smoke test, the matrix
records it as `unknown`. If asked to "just mark it compatible" or to infer support
from a version being "close enough", the record refuses to fabricate a supported
status and instead records `unknown` plus the missing-evidence blocker. No numeric
compatibility score is ever emitted.

**Why this priority**: this is the constitutional guardrail for this feature
(hard rule #9 / Principle IX). A compatibility matrix is precisely where an agent is
tempted to fill an untested cell with "probably fine"; that is forbidden and must
hard-stop at `unknown`.

**Independent Test**: ask the record to mark an untested version "compatible"; assert
it declines, records `unknown` with the missing smoke-test run as the blocker, cites
the no-fake-confidence rule, and emits no numeric score -- and that the only path to a
supported status is a named owner attesting a passed smoke test as evidence.

**Acceptance Scenarios**:

1. **Given** an untested version, **When** the record is filled, **Then** its status is
   `unknown` and the missing smoke-test run is the recorded blocker -- never supported,
   never `pass`, never inferred.
2. **Given** a request to assign a single numeric compatibility/confidence score,
   **When** the record is filled, **Then** it declines, cites readiness-model
   "No fake confidence", and records explicit status + evidence instead.
3. **Given** a version that a smoke test verified as working, **When** the record is
   promoted to supported, **Then** the promotion is backed by evidence = the passed
   smoke test + its run date + the named owner who attested -- the agent never
   self-promotes a cell to supported.

---

### Edge Cases

- **A transitive dependency moves but the direct adapter version is unchanged**: the
  matrix records the direct adapter rows; a transitive move that breaks a smoke test
  flips that adapter's smoke-test status to `blocked`/`unknown` at next verification --
  the matrix does not silently keep `pass` for an unverified state.
- **An adapter is parked (e.g. F016 Power BI MCP)**: the row records status `parked`
  (or `unknown` for compatibility) with a note that it is not yet exercised; it is NOT
  marked supported, and it is NOT omitted.
- **A version range with an open upper bound** (e.g. "tested at X, upper bound
  untested"): the supported range states the tested floor and marks the ceiling
  `unknown` -- it does not assume newer-is-fine.
- **A dependency-update PR bumps a tool past the recorded supported range**: the matrix
  RECORD shows the bump now sits outside the verified range; deciding what the PR must
  do about it (re-verify, block, accept) is the F031 POLICY, not F032.
- **A smoke test exists in name but has never been run**: the smoke-test status is
  `unknown` ("named, not yet run") -- a named-but-unrun test does not make a version
  supported.
- **An owner is missing for an attested row**: the owner cell reads `UNASSIGNED` and
  the row is flagged; a supported status requires a named attesting owner (no
  self-attestation by the agent -- Principle V posture).
- **Someone tries to put enforcement logic (a PR gate, a CI fail condition) into the
  matrix**: rejected -- the matrix is a RECORD; enforcement is F031 (the record/policy
  boundary).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: PLAN `docs/operations/adapter-compatibility-matrix.md` -- the single
  committed matrix doc (one row per adapter/dependency) -- as a FUTURE deliverable
  enumerated in this spec/plan; it is NOT created in this planning slice. ASCII +
  UTF-8 no BOM when authored.
- **FR-002**: PLAN `templates/adapter-version-record.md` -- the generic, copy-me shape
  of ONE adapter's entry -- as a FUTURE deliverable enumerated here; NOT created this
  slice. ASCII + UTF-8 no BOM, placeholders only, no worked-example specifics.
- **FR-003**: The planned matrix MUST carry one row for EACH of these adapters/
  dependencies: Tower BI Kit version, Python version, Postgres version, dbt-core
  version/range, dbt-postgres version/range, Dagster version/range, dagster-dbt
  version/range, Power BI PBIP/TMDL assumptions, and Power BI MCP adapter status. No
  named adapter may be absent.
- **FR-004**: The planned matrix MUST carry these columns for every row: supported
  version RANGE, required smoke test (named), smoke-test status, last-verified date,
  and owner. A row missing a version range or a smoke test is a defect.
- **FR-005**: Every adapter row MUST have a version RANGE (a floor and, where tested,
  a ceiling), not a single bare pinned point with the rest left implicit. Where a
  bound is untested, that bound is `unknown`, never assumed.
- **FR-006**: Every adapter row MUST name its required smoke test. A row with no smoke
  test is a defect. F032 NAMES the smoke test and records its last result; it does NOT
  author or run the smoke test (that is adapter/automation runtime work).
- **FR-007**: An UNKNOWN version, range, or adapter MUST be recorded as `unknown` --
  never as supported, never as `pass`, never inferred from "probably works". This is
  the no-fake-confidence instantiation (hard rule #9 / Principle IX).
- **FR-008**: The matrix MUST NOT contain a numeric compatibility/confidence score. It
  records explicit status (`pass`/`warning`/`blocked`/`not_started`/`unknown`) plus
  evidence (smoke-test result + last-verified date + owner) only.
- **FR-009**: A row reaches a SUPPORTED status only with a named owner attesting a
  PASSED smoke test, recorded as evidence (owner + run date). The agent MUST NOT
  self-promote a cell to supported and MUST NOT self-attest as owner (Principle V
  posture).
- **FR-010**: The record/policy boundary MUST be explicit in the planned doc: F032 is
  the RECORD (what is verified); F031 is the POLICY (what a dependency-update PR must
  do, when to re-verify, what to block). The matrix MUST NOT contain a PR gate, a CI
  fail condition, or any enforcement logic.
- **FR-011**: The record/build boundary MUST be explicit: F032 records the supported
  versions of the F029 dbt adapter, the F030 Dagster adapter, and the F016 Power BI
  execution adapter; it MUST NOT author, modify, or execute any of those adapters'
  runtime code, connection logic, or transformations.
- **FR-012**: The planned doc MUST state the trigger relationship F031 enforces: a
  dependency-update PR that changes a supported version MUST update the matrix. F032
  states the matrix is the record that such a PR updates; the ENFORCEMENT of that
  requirement is F031's policy (F032 does not gate the PR itself).
- **FR-013**: All planned artifacts MUST be GENERIC -- no C086 / retail_store_sales
  specifics. Concrete version strings in a future filled matrix are environment facts;
  this planning slice uses generic field shapes + `<placeholder>` examples only
  (Principle VII).
- **FR-014**: This feature MUST advance NO readiness stage. The planned doc MUST state
  "readiness stage affected: none directly" and explain that the matrix is a
  Maintenance Automation record supporting kit durability, not a spine gate.
- **FR-015**: This planning slice MUST add NO runtime code, NO CLI subcommand, NO
  `retail check` rule, NO CI job, and NO dbt/Dagster/Power BI artifact. `retail check`
  stays exit 0 and no new rule is added.

### Key Entities *(include if feature involves data)*

- **Adapter version record**: the atomic entry for one adapter/dependency. Attributes:
  adapter name, supported version `range`, required `smoke_test` (named), smoke-test
  `status` (one of the explicit statuses or `unknown`), `last_verified` date, `owner`
  (named attester), `evidence[]`, `blocking_reasons[]`. It is a RECORD, not an
  enforcement rule and not adapter code.
- **The compatibility matrix**: the committed collection of all adapter version records
  in one doc -- the version-truth the F031 policy reads against. One row per
  adapter/dependency; no adapter absent.
- **Required smoke test**: the NAMED check that, when run and passed, is the evidence a
  version is supported. F032 names it and records its last result + date; it does not
  author or run it.
- **Attesting owner**: the named human who attests a passed smoke test, promoting a row
  to supported. Attestation (owner + run date) is the evidence; the agent never
  self-attests and never self-promotes a cell.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The five Spec-Kit planning files for F032 exist (spec, plan, tasks, and
  the two checklists), are ASCII + UTF-8 no BOM, and enumerate BOTH future deliverables
  (`docs/operations/adapter-compatibility-matrix.md`, `templates/adapter-version-record.md`)
  as planned-not-created outputs -- verifiable by reading the five files.
- **SC-002**: The planned matrix's adapter list is COMPLETE: a reader can confirm all
  nine named adapters/dependencies (Tower BI Kit, Python, Postgres, dbt-core,
  dbt-postgres, Dagster, dagster-dbt, Power BI PBIP/TMDL, Power BI MCP status) are each
  required to appear as a row -- zero named adapters omitted (FR-003).
- **SC-003**: Every planned adapter row is required to carry a version RANGE and a NAMED
  smoke test; the spec defines a row missing either as a defect -- verifiable from the
  requirements + acceptance scenarios (FR-004/FR-005/FR-006).
- **SC-004**: The no-fake-confidence rule holds: a reader can confirm an untested
  version MUST be `unknown` (never supported/inferred) and that NO numeric compatibility
  score is permitted anywhere in the planned artifacts (FR-007/FR-008).
- **SC-005**: The record/policy boundary holds: a reader of the spec can state,
  unambiguously, that F032 RECORDS verified versions and that ENFORCING what a PR must
  do is the separate F031 policy -- no enforcement logic, PR gate, or CI fail condition
  in any planned F032 artifact (FR-010/FR-012).
- **SC-006**: The record/build boundary holds: a reader can confirm F032 TRACKS the
  versions of the F029/F030/F016 adapters and does NOT author, modify, or execute any
  adapter's runtime code (FR-011).
- **SC-007**: 100% of planned artifacts are generic: zero C086 / retail_store_sales
  specifics in any field shape or example; placeholders are obvious (FR-013).
- **SC-008**: This planning slice adds no new `retail check` rule and adds no
  runtime code, CLI verb, CI job, or adapter artifact -- verifiable by the diff
  and the absence of any non-planning file (FR-015).

## Human approval boundary

The human boundary here is deliberately LIGHT and specific (the classic data judgment
calls -- grain, PII, business rollup -- are N/A for a version record, stated so
explicitly rather than fake-fitted):

- A row reaches a SUPPORTED status ONLY when a NAMED owner attests a PASSED smoke test
  (evidence = smoke-test result + run date + owner). The agent recommends and records;
  the named owner decides and attests.
- The stop-and-ask is: when a version/range/adapter is untested, the agent MUST mark it
  `unknown` and stop -- it MUST NOT infer "compatible" (Principle V posture: surface
  the uncertainty, never bury it under a guessed status).
- The agent never self-attests as the owner of a row and never self-promotes a cell to
  supported.

## Allowed operations

- AUTHOR the five Spec-Kit planning files for F032 (this slice).
- ENUMERATE the two future deliverables (matrix doc + record template) as planned
  outputs inside the spec/plan.
- READ the roadmap, the readiness model, and sibling-feature specs to cite boundaries
  by F-number.
- In the future (non-this-slice) authoring slice: fill the matrix/record template from
  evidence a named owner has attested, and RECORD an `unknown` for any untested cell.

## Forbidden operations

- Creating ANY file other than the five Spec-Kit planning files in this slice
  (the matrix doc and record template are FUTURE outputs, not created now).
- Authoring, modifying, or executing the F029 dbt adapter, the F030 Dagster adapter,
  or the F016 Power BI execution adapter (F032 tracks versions; it does not build).
- Authoring or RUNNING any smoke test, or wiring a smoke test into CI (F032 names the
  smoke test and records its last result only).
- Adding a PR gate, a CI fail condition, a merge block, or any enforcement logic to the
  matrix (enforcement is the F031 policy; F032 is the record).
- Marking any untested version/range/adapter as supported, `pass`, or compatible by
  inference; recording any cell as anything other than `unknown` when its smoke test
  has not been run and passed.
- Emitting a numeric compatibility/confidence score anywhere.
- Self-attesting (the agent as owner) or self-promoting a cell to supported.
- Inlining C086 / retail_store_sales specifics, secrets, DSNs, tokens, or local
  machine paths into any artifact.
- Adding runtime code, a CLI subcommand, a `retail check` rule, or a new gate.

## Evidence required

- For a SUPPORTED row: the named required smoke test, its PASSED result, its run
  (last-verified) date, and the named attesting owner.
- For an `unknown` row: the missing-evidence blocker recorded in `blocking_reasons[]`
  ("smoke test not run" / "version untested" / "upper bound untested").
- For the feature itself (this slice): the five committed planning files, ASCII +
  no BOM, with both future deliverables enumerated as planned-not-created.

## Readiness stage affected

**None directly.** F032 advances no stage of the readiness spine (Source -> Mapping ->
Silver -> Gold -> Semantic Model -> Dashboard -> Publish). It is a Maintenance
Automation record (per the F024 category) that protects the kit's durability -- its
ability to run the stages at all -- rather than gating any single stage. This is stated
plainly rather than force-fitting a spine stage the way feature-delivery specs do.

## Dependencies

- **Upstream**: F024 (Companion Tools Architecture) defines the Maintenance Automation
  category and the companion-vs-core authority rule this feature lives under; the
  readiness model (`docs/readiness/readiness-model.md`) supplies the four-status
  vocabulary + the no-fake-confidence rule; the constitution (Principles V, VII, VIII,
  IX). Cited by F-number; F024 is a sibling in this drafting batch.
- **Paired**: F031 (Adapter Maintenance Policy) is the POLICY that enforces against
  this RECORD -- tightly coupled, but a separate feature. F032 supplies the truth;
  F031 supplies the enforcement.
- **References (tracked, not built)**: F029 (dbt adapter), F030 (Dagster adapter),
  F016 (Power BI execution adapter) -- their supported versions are rows in the matrix;
  their implementations are owned by those features.

## Non-goals

- Any enforcement: PR gate, CI fail condition, merge block (that is F031).
- Building, modifying, or running any adapter (F029/F030/F016 own their runtime).
- Authoring or executing smoke tests, or wiring them into CI.
- Any numeric compatibility/confidence score (deferred and forbidden, rule #9).
- Advancing or gating any readiness stage.
- Inlining C086 / retail_store_sales specifics (Principle VII).
- Any runtime code, CLI verb, `retail check` rule, or new gate in this slice.

## Assumptions

- **Docs + one template, agent as runtime** (Principle VIII; rule #8): the matrix is a
  committed doc + a copy-me record template; the agent fills it from attested evidence.
  No new Python, no CLI, no CI in the planned shape's first form.
- **Generic field shapes, C086 cited not inlined** (Principle VII): concrete version
  strings in a future filled matrix are environment facts; this planning slice carries
  generic shapes + placeholders only.
- **Record/policy split is the organizing decision**: F032 is the record, F031 is the
  policy. This pairing is the recommended default and is recorded in both specs; it is
  cheaply reconcilable if the batch later merges them (a doc move), but they are
  specified separately to keep the record honest and the policy enforceable.
- **Power BI execution adapter is parked (F016)**: its row records `parked`/`unknown`
  status, not supported; `pbi-cli` is no longer the preferred path -- the official
  Power BI MCP / connection is the preferred future adapter, and the matrix tracks its
  STATUS, not its implementation.
- **Last-verified dates and smoke-test results are point-in-time evidence**: the matrix
  is a record updated when a version is re-verified; staleness is honest (an old
  last-verified date is shown, not hidden), and re-verification timing is the F031
  policy's concern.

## Deferred decisions (future specs / issues -- recorded, not built)

- **A machine-readable matrix + automated PR check**: a `compatibility-matrix.yaml`
  plus a CI job that fails a PR which bumps a tool past the recorded range -- DEFERRED.
  When/whether to automate enforcement is F031's policy decision; F032 stays the
  human-readable record in its first form (rule #8: automate after the artifact proves
  useful).
- **A defined numeric compatibility score**: DEFERRED and currently FORBIDDEN (rule #9)
  until scoring rules exist; the matrix uses explicit status + evidence only.
- **Auto-running smoke tests on a schedule**: DEFERRED; smoke tests are named + their
  last result recorded by F032, authored/run by the adapter features + a later
  automation slice.
- **Merging F031 + F032 into one feature**: DEFERRED; specified separately to keep the
  record/policy boundary clean. A later batch may consolidate if the split proves
  needless.

## See also

- The policy half of the pair: F031 (Adapter Maintenance Policy), `specs/025-adapter-maintenance-policy/`.
- The category home: F024 (Companion Tools Architecture), `specs/018-companion-tools-architecture/`.
- The tracked adapters (not built here): F029 (dbt) `specs/023-dbt-transformation-adapter/`,
  F030 (Dagster) `specs/024-dagster-orchestration-adapter/`, F016 (Power BI execution adapter).
- The no-fake-confidence rule + four-status vocabulary: `docs/readiness/readiness-model.md`.
- The roadmap row + hard rules 7, 8, 9: `docs/roadmap/roadmap.md`.
- The constitution: `.specify/memory/constitution.md` (Principles V, VII, VIII, IX).
