---
description: "Task list for Adapter Compatibility Matrix (F032)"
---

# Tasks: Adapter Compatibility Matrix

**Input**: Design documents from `specs/026-adapter-compatibility-matrix/`

**Roadmap feature**: F032 (on-disk spec-dir 026; when they disagree the roadmap
F-number wins).

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a docs/planning-only feature (no runtime code) -- there are no unit
tests. Verification tasks (all nine adapters present, range + smoke-test per row,
UNKNOWN-not-compatible, no numeric score, ASCII/no-BOM) stand in for tests and are
included explicitly. Tasks that reference the two future deliverables are PLANNING tasks
("Plan/author spec for X"), not "implement X now".

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Docs/planning feature -- no `src/`/`tests/`. This slice writes only the five Spec-Kit
files under `specs/026-adapter-compatibility-matrix/`. The two FUTURE deliverables
(`docs/operations/adapter-compatibility-matrix.md`, `templates/adapter-version-record.md`)
are ENUMERATED, not created this slice.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin the reference shapes and the fixed adapter list before authoring.

- [ ] T001 [P] Re-read the house-style reference shapes -- an existing readiness/issue
      template (header + namespace/placeholder convention) and
      `docs/readiness/readiness-model.md` (the four-status vocabulary + no-fake-confidence
      rule) -- and capture the exact header/status idiom to reuse in the planned doc +
      template.
- [ ] T002 [P] Pin the FIXED adapter list the matrix must cover (nine rows): Tower BI Kit
      version, Python version, Postgres version, dbt-core version/range, dbt-postgres
      version/range, Dagster version/range, dagster-dbt version/range, Power BI PBIP/TMDL
      assumptions, Power BI MCP adapter status. This list is load-bearing for US2.

**Checkpoint**: house style pinned; the nine-adapter list is fixed and ready to drop in.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two boundaries + the no-fake-confidence vocabulary that ALL three
stories depend on. Fix these once, reuse verbatim.

**CRITICAL**: No user-story content may be authored until the record/policy + record/build
boundaries and the UNKNOWN-not-compatible rule are fixed, or the artifacts will drift into
F031 (enforcement), into the adapters (build), or invent a "probably fine" cell.

- [ ] T003 Write the record/policy boundary statement (single source of truth) to reuse in
      the spec, plan, and both checklists: F032 is the RECORD (verified ranges + smoke-test
      status + dates + owners); F031 is the POLICY (what a dependency-update PR must do, when
      to re-verify, what to block). The matrix carries NO PR gate, NO CI fail condition, NO
      enforcement logic.
- [ ] T004 Write the record/build boundary statement: F032 RECORDS the supported versions of
      the F029 dbt adapter, the F030 Dagster adapter, and the F016 Power BI execution adapter;
      it does NOT author, modify, or execute any adapter's runtime code, connection logic, or
      transformations.
- [ ] T005 Fix the no-fake-confidence vocabulary for compatibility: the four statuses
      (`not_started`/`blocked`/`warning`/`pass`) PLUS `unknown` for an untested cell; an
      UNKNOWN version/range/adapter is NEVER supported, NEVER `pass`, NEVER inferred; NO
      numeric compatibility score anywhere (hard rule #9 / Principle IX). Pin the
      owner-attests-a-passed-smoke-test rule as the only path to a supported status.

**Checkpoint**: both boundary statements + the UNKNOWN-not-compatible rule + the
owner-attestation rule are fixed and ready to drop into each artifact identically.

---

## Phase 3: User Story 1 - Record one adapter's range + smoke test (Priority: P1) MVP

**Goal**: Specify the per-adapter record template
(`templates/adapter-version-record.md`) as a planned deliverable -- the atomic unit of
the matrix.

**Independent Test**: the spec defines a filled record carrying a version RANGE, a named
smoke test, a smoke-test status, a last-verified date, and a named owner, generic, with
no numeric score -- and an untested version recorded `unknown`.

- [ ] T006 [US1] In spec.md, define the `adapter-version-record.md` template's required
      fields: `adapter` name, supported `range` (floor + tested ceiling; untested bound =
      `unknown`), `smoke_test` (named), `status`, `last_verified` date, `owner`,
      `evidence[]`, `blocking_reasons[]`. [FR-002, FR-004, FR-005, FR-006]
- [ ] T007 [US1] In spec.md, specify the smoke-test handling: the record NAMES the required
      smoke test and records its last result + date; it does NOT author or run it. A
      named-but-unrun test makes the version `unknown`. [FR-006, edge case]
- [ ] T008 [US1] In spec.md + plan.md, specify the promotion rule: a row reaches a supported
      status ONLY with a named owner attesting a PASSED smoke test (evidence = result + run
      date + owner); the agent never self-attests / self-promotes. [FR-009, Human approval
      boundary]
- [ ] T009 [US1] In plan.md Phase 1 Design, describe the template's header block (house
      style + both boundary statements from T003/T004 + the no-fake-confidence rule from
      T005) and one GENERIC example adapter row (placeholders only, zero C086). [FR-013]

**Checkpoint**: the atomic per-adapter record is fully specified as a planned deliverable. MVP.

---

## Phase 4: User Story 2 - Assemble the full matrix across every adapter (Priority: P1)

**Goal**: Specify the matrix doc
(`docs/operations/adapter-compatibility-matrix.md`) as a planned deliverable -- the
complete picture with no adapter absent.

**Independent Test**: the spec requires the matrix to list all nine named adapters as
rows, each with a version range + a named smoke test, each cell explicit or `unknown`,
no numeric score.

- [ ] T010 [US2] In spec.md, require one matrix row for EACH of the nine adapters/
      dependencies from T002; define a missing adapter as a defect. [FR-003, SC-002]
- [ ] T011 [US2] In spec.md, define the matrix columns for every row: supported version
      range, required smoke test, smoke-test status, last-verified date, owner; define a row
      missing a range or a smoke test as a defect. [FR-004, FR-005, FR-006, SC-003]
- [ ] T012 [US2] In spec.md + plan.md, specify the parked-adapter handling: the F016 Power
      BI MCP row records `parked`/`unknown` (not supported, not omitted); `pbi-cli` is not the
      preferred path -- the matrix tracks the MCP adapter's STATUS, not its implementation.
      [FR-011, edge case]
- [ ] T013 [US2] In plan.md Phase 1 Design, describe the matrix doc's header + table shape +
      rules section (UNKNOWN-not-compatible, range-required, smoke-test-required,
      no-numeric-score, how F031 reads it, "readiness stage affected: none directly").
      [FR-010, FR-012, FR-014]

**Checkpoint**: the complete matrix is specified -- every adapter present, every row shaped.

---

## Phase 5: User Story 3 - UNKNOWN is never assumed compatible (Priority: P1)

**Goal**: Encode the constitutional guardrail (hard rule #9 / Principle IX) across the
spec + both checklists: an untested cell is `unknown`, never supported; no numeric score.

**Independent Test**: the spec requires that a request to "mark it compatible" for an
untested version is declined and recorded `unknown` with the missing-smoke-test blocker,
citing the no-fake-confidence rule, with no numeric score emitted.

- [ ] T014 [US3] In spec.md, write US3 + FR-007/FR-008: UNKNOWN is never supported/`pass`/
      inferred; no numeric compatibility score anywhere; explicit status + evidence only.
      [SC-004]
- [ ] T015 [US3] In spec.md, define the stop-and-ask: when a version/range/adapter is
      untested, the agent marks it `unknown` and STOPS (surface the uncertainty, never bury
      it); record the missing-evidence blocker in `blocking_reasons[]`. [FR-007, Human
      approval boundary, Principle V posture]
- [ ] T016 [US3] In spec.md, state plainly that the classic data judgment calls
      (grain/PII/business rollup) are N/A for a version record -- do NOT fake-fit them; the
      only judgment call is "is this version verified?".
- [ ] T017 [US3] In checklists/governance.md, map the UNKNOWN-not-compatible rule + the
      no-self-attestation / no-self-promotion rule to `[ ]` gate items 1:1 against spec.md's
      Forbidden operations + Human approval boundary.

**Checkpoint**: the no-fake-confidence guardrail is encoded in spec + governance checklist.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories and confirm the
planning-only wall held.

- [ ] T018 Confirm spec.md enumerates BOTH future deliverables
      (`docs/operations/adapter-compatibility-matrix.md`, `templates/adapter-version-record.md`)
      as planned-not-created, and that NEITHER file was created in this slice. [FR-001, FR-002,
      SC-001]
- [ ] T019 [P] Confirm the planning-only wall: this slice created ONLY the five Spec-Kit
      files; no runtime code, no CLI verb, no `retail check` rule, no CI job, no
      dbt/Dagster/Power BI artifact, no adapter code. [FR-015, SC-008]
- [ ] T020 [P] Grep all five files for C086 / retail_store_sales leakage (billing codes,
      segments, PII column names, grain keys) and for any secret/DSN/token/local path --
      expect zero. [FR-013, SC-007]
- [ ] T021 [P] Confirm no enforcement logic (PR gate, CI fail condition, merge block) and no
      adapter implementation leaked into any file -- both boundary gates (record/policy,
      record/build) hold end-to-end. [FR-010, FR-011, SC-005, SC-006]
- [ ] T022 Confirm all five files are ASCII + UTF-8 no BOM, use `->`/`--` not Unicode
      symbols, repo-relative paths stay short (`<= 200` chars), and the header states BOTH the
      spec-dir number (026) and the roadmap F-number (F032). [Principle IX]
- [ ] T023 Author checklists/acceptance.md (`[x]` self-asserted quality items) and confirm
      checklists/governance.md (`[ ]` gate items) maps 1:1 to spec.md's Forbidden operations +
      Human approval boundary.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately (T001/T002 parallel).
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the two
  boundary statements + the UNKNOWN-not-compatible/no-score rule + the owner-attestation
  rule every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (the per-adapter record)
  is the MVP and goes first because US2 (the full matrix) is a collection of US1 rows and
  US3 (the UNKNOWN guardrail) governs both. US2 and US3 author into the SAME spec.md +
  checklists, so sequence them after US1.
- **Polish (Phase 6)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the atomic deliverable (MVP).
- **US2 (P1)**: needs US1's record shape (the matrix is a collection of records).
- **US3 (P1)**: governs US1 + US2 (the guardrail applies to every cell); authored after
  the row/matrix shapes exist so the guardrail has concrete anchors.

### Parallel Opportunities

- T001 + T002 (read references / pin adapter list) run in parallel.
- Within a user story, edits land in the SAME spec.md/plan.md -- author in one pass to
  minimize edit rounds (not parallel within a file).
- Polish T019/T020/T021 are independent greps/checks -- parallel.

## Parallel Example

```text
# Setup -- run together:
Re-read house-style references (T001)
Pin the nine-adapter list (T002)

# Polish -- independent verification, run together:
Confirm planning-only wall (T019)
Grep for C086 / secret leakage (T020)
Confirm no enforcement / no adapter code leaked (T021)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = the per-adapter record fully specified as a
planned deliverable. Then US2 (the full nine-row matrix) + US3 (the UNKNOWN guardrail),
then the Phase 6 whole-feature gates.

**Boundary discipline (the load)**: every artifact carries the same verbatim record/policy
(T003) + record/build (T004) boundaries and the UNKNOWN-not-compatible / no-score rule
(T005). Phase 6 (T019-T021) proves the three ways this feature could fail its own scope:
leaking enforcement (into F031's lane), leaking adapter code (into F029/F030/F016's lane),
or inventing a "probably fine" cell.
