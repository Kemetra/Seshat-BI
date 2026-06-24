---
description: "Task list for Metric Contract Store + Retail KPI Packs (F009)"
---

# Tasks: Metric Contract Store + Retail KPI Packs

**Input**: Design documents from `specs/010-metric-contract-store/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a docs/templates-only feature (no runtime code) -- there are no unit
tests. Verification tasks (YAML-valid, ASCII/no-BOM, `retail check` green, generic-check)
stand in for tests and are included explicitly.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Docs/templates feature -- no `src/`/`tests/`. New artifacts: `templates/`, `docs/metrics/`,
plus a pointer edit in `docs/readiness/semantic-model-ready.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new doc home and confirm the reference shapes.

- [ ] T001 Create `docs/metrics/` directory (parallel to `docs/readiness/`).
- [ ] T002 [P] Re-read the two reference shapes -- `templates/source-map.yaml` (header +
      namespace/placeholder convention) and `docs/readiness/readiness-model.md` +
      `templates/readiness-status.yaml` (four-status vocabulary + no-score rule) -- and
      capture the exact header/status idiom to reuse, so the new templates match house style.

**Checkpoint**: doc home exists; house style for headers + status vocabulary is pinned.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The boundary + readiness vocabulary that ALL three stories depend on.

**CRITICAL**: No user story artifact may be authored until the boundary + status rules are
fixed, or the artifacts will drift into F010 (checking) or invent a score.

- [ ] T003 Write the define/check boundary statement (single source of truth) to reuse in
      both templates' headers and the guide: this feature DEFINES contracts; it does NOT
      read `powerbi/`, assert measures/relationships/date-table, or add a `retail check`
      rule (that is F010 / on-disk 011). Keep it verbatim across all three new files.
- [ ] T004 Fix the readiness vocabulary for contracts: exactly the four statuses
      (`not_started` / `blocked` / `warning` / `pass`) + `evidence[]` + `blocking_reasons[]`,
      NO numeric score field anywhere (roadmap rule #9). Pin the `pass`-needs-owner+date
      evidence rule.
- [ ] T005 Enumerate the Principle-V stop-and-ask trigger list to embed in every artifact:
      business rollup / segment mapping not analyst-supplied; grain ambiguity / grain finer
      than the bound fact; PII publish-safety. Each is a `blocking_reason`, never auto-filled.

**Checkpoint**: boundary text + four-status/no-score rule + Principle-V list are fixed and
ready to drop into each artifact identically.

---

## Phase 3: User Story 1 - Define a metric contract from the template (Priority: P1) MVP

**Goal**: Ship `templates/metric-contract.yaml` -- a generic, copy-me one-metric definition.

**Independent Test**: fill the template for a GENERIC metric (e.g. "total of an additive
money column at line grain"); confirm name/grain/formula-intent/owner/bound-gold-columns
are all present, the formula is INTENT not DAX, and no C086 specifics leak.

- [ ] T006 [US1] Author `templates/metric-contract.yaml` header block in the
      `source-map.yaml` style: what it is, principles it instantiates (III gold-only,
      V stop-and-ask, VII generic, IX no-BOM), the no-score rule (#9), the define/check
      boundary (from T003), and a generic-placeholder note (C086 cited, never inlined).
- [ ] T007 [US1] Add the required fields to `templates/metric-contract.yaml`: `name`
      (PascalCase, matching the DAX measure convention), `grain` (grain the metric is valid
      at), `formula_intent` (plain language; explicit "NOT DAX" note + a generic
      intent-vs-implementation example), `owner` (named), `binds_to` (gold table + column(s)
      -- gold ONLY per FR-012). [FR-001, FR-002, FR-008, FR-012]
- [ ] T008 [US1] Add the readiness block to `templates/metric-contract.yaml`: `status`
      (one of four words), `evidence[]`, `blocking_reasons[]`; NO score field. [FR-003, FR-010]
- [ ] T009 [US1] Add authoring notes to `templates/metric-contract.yaml` embedding the
      Principle-V stop-and-ask list (T005) and the `pass`-needs-owner-approval-as-evidence
      rule. [FR-009, FR-010]
- [ ] T010 [US1] Verify `templates/metric-contract.yaml` parses as valid YAML, is ASCII +
      UTF-8 no BOM, and a manual generic fill-in exercises every required field with zero
      C086/pharmacy specifics. [SC-001, SC-002]

**Checkpoint**: a metric can be fully DEFINED from one committed generic template. MVP done.

---

## Phase 4: User Story 2 - Group metric contracts into a generic KPI pack (Priority: P2)

**Goal**: Ship `templates/kpi-pack.yaml` -- the pack schema + ONE example generic pack.

**Independent Test**: fill the pack for a generic pack referencing 2+ contracts by name;
confirm every referenced name resolves, the pack is generic, and it has an owner + purpose.

- [ ] T011 [US2] Author `templates/kpi-pack.yaml` header (same house style + boundary text
      from T003) and the pack schema: `pack_name`, `purpose`, `owner`, `contracts[]`
      (stable metric-contract names). [FR-004]
- [ ] T012 [US2] Add ONE example generic retail KPI pack to `templates/kpi-pack.yaml` using
      generic KPI names only (e.g. a "sales overview" set) -- referencing the generic
      example contract name(s) from US1; ZERO C086 / pharmacy values. [FR-004, FR-006]
- [ ] T013 [US2] Verify `templates/kpi-pack.yaml` parses as valid YAML, is ASCII + UTF-8 no
      BOM, every referenced contract name in the example pack is resolvable (no dangling
      reference), and the example is generic. [SC-002]

**Checkpoint**: contracts can be grouped into a reusable, generic, owned pack.

---

## Phase 5: User Story 3 - The store records readiness with evidence, never a score (Priority: P1)

**Goal**: Ship `docs/metrics/metric-contract-store.md` -- store layout + authoring guide +
lifecycle + boundary, and resolve the Semantic Model Ready "artifacts PLANNED" note.

**Independent Test**: read the guide; confirm it defines exactly the four statuses, requires
`evidence[]` for a `pass`, requires `blocking_reasons[]` for a `blocked`, forbids a numeric
score, and names the metric owner as the approver.

- [ ] T014 [US3] Author `docs/metrics/metric-contract-store.md`: purpose; where filled
      contracts (`mappings/<table>/metrics/`) and packs (`metrics/packs/`) live (record O-1
      as the recommended, reversible default); the draft -> reviewed -> approved lifecycle
      mapped to the four statuses. [FR-005]
- [ ] T015 [US3] In the guide, state the no-score rule, the owner-approval-as-evidence rule
      (`pass` = owner + date), the Principle-V stop-and-ask list (T005), and the define/check
      boundary (T003 -- this feature defines; F010/on-disk-011 checks); and how Semantic
      Model Ready reads contracts. [FR-005, FR-009, FR-010]
- [ ] T016 [US3] Edit `docs/readiness/semantic-model-ready.md`: change the metric-contracts
      required-artifact row note from "PLANNED, not yet built" to point at
      `templates/metric-contract.yaml` (filled per table under `mappings/<table>/metrics/`),
      WITHOUT changing any gate, status, or the F010 PBIP-check responsibility. [FR-011, SC-004]
- [ ] T017 [US3] Verify the guide defines exactly four statuses + evidence/blockers + no
      score, names the owner as approver, and the `semantic-model-ready.md` edit altered no
      gate (diff shows only the artifact-row note changed). [SC-005]

**Checkpoint**: the store's rules are documented; the Semantic Model Ready artifact gap is
closed without introducing a PBIP check.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories.

- [ ] T018 Run `retail check` over the repo: confirm exit 0 and rule count UNCHANGED (this
      feature adds no rule). [FR-007, SC-003]
- [ ] T019 [P] Grep all four new/edited files for C086/pharmacy leakage (billing codes,
      segment rollups, insurance/PII columns, pharmacy grain keys) -- expect zero. [SC-002]
- [ ] T020 [P] Confirm no artifact reads `powerbi/` and no new Python/CLI/rule was added --
      the define/check boundary holds end-to-end. [SC-006]
- [ ] T021 Confirm all new files are ASCII + UTF-8 no BOM and repo-relative paths stay short
      (`<= 200` chars). [Principle IX]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (fixes the boundary,
  the four-status/no-score rule, and the Principle-V list every artifact reuses verbatim).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (P1) is the MVP and should
  go first because US2's example pack references a US1 contract name, and US3's guide cites
  the contract template. US3 (also P1) depends on US1 existing (it points the readiness doc
  at the US1 template).
- **Polish (Phase 6)**: depends on all three stories complete.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the atomic deliverable (MVP).
- **US2 (P2)**: needs US1's example contract NAME to reference (soft dependency); the pack
  SCHEMA is independent.
- **US3 (P1)**: needs US1's template to point the readiness doc at it.

### Parallel Opportunities

- T002 (read references) runs parallel to T001.
- Within US1, T006/T007/T008/T009 edit ONE file (`metric-contract.yaml`) -- author in one
  pass to minimize edit rounds (not parallel); T010 verifies after.
- US2 and US3 author DIFFERENT files (`kpi-pack.yaml` vs `metric-contract-store.md` +
  `semantic-model-ready.md`), so once US1 exists they can proceed in parallel.
- Polish T019/T020 are independent greps -- parallel.

## Parallel Example: after US1 ships

```
# US2 and US3 touch different files -- run together:
Author templates/kpi-pack.yaml (US2: T011-T013)
Author docs/metrics/metric-contract-store.md + edit semantic-model-ready.md (US3: T014-T017)
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = a usable metric-contract template (a metric can
be defined). Ship/commit there if needed. Then US2 (packs) + US3 (store guide + readiness
pointer) in parallel, then the Phase 6 whole-feature gates.

**Boundary discipline (the load)**: every artifact carries the same verbatim define/check
boundary (T003) and four-status/no-score rule (T004); Phase 6 (T018-T020) proves no rule,
no PBIP read, no C086 leak -- the three ways this feature could fail its own scope.
