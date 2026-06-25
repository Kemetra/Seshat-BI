---
description: "Task list for Companion Tools Architecture (F024)"
---

# Tasks: Companion Tools Architecture

**Input**: Design documents from `specs/018-companion-tools-architecture/` (roadmap F024, on-disk 018)

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This is a planning/architecture-definition feature (no runtime code) -- there are
no unit tests. Verification tasks (ASCII/no-BOM, `retail check` green at unchanged rule
count, matrix-correctness, no-overlap classification, generic-check) stand in for tests and
are included explicitly. The five spec-kit files are the ONLY artifacts written in this
slice; the five future deliverables are enumerated as a later implementation phase
(authoring tasks), never produced now.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3) or SETUP/FOUNDATION/POLISH
- All paths are repo-relative from the worktree root

## Path Conventions

Planning feature -- no `src/`/`tests/`. The only writes this slice: the five files under
`specs/018-companion-tools-architecture/`. The future build phase authors the five enumerated
deliverables under `docs/architecture/`, `docs/decisions/`, `templates/`.

---

## Phase 1: Setup (Shared Inputs)

**Purpose**: Pin the inputs being formalized so the taxonomy cites them rather than reinventing.

- [ ] T001 [P] Re-read the roadmap's Six product layers (`docs/roadmap/roadmap.md`) and
      capture the functional-axis vocabulary verbatim, so the spec can state the five
      categories are ORTHOGONAL to (not a renumbering of) the layers.
- [ ] T002 [P] Re-read the constitution's authority rules (Principles I, V) and the shipped
      F005-F016 specs, listing each shipped surface so the classification table is sourced
      from real features, not invented.

**Checkpoint**: the functional axis + the authority rule + the surfaces to classify are pinned.

---

## Phase 2: Foundational (the closed contract every story depends on)

**Purpose**: Fix the five categories, the authority matrix, and the two sub-vocabularies --
the closed sets ALL three user stories reuse. If these drift, the categories overlap or a
non-Core tool gains truth-creating power.

**CRITICAL**: No classification work may proceed until the matrix and the seam are fixed.

- [ ] T003 [FOUNDATION] Fix the FIVE categories as a closed set (Core Authority, Official
      Workflow Skill, Product Module, Execution Adapter, Maintenance Automation) with a
      one-paragraph normative definition each. [FR-001]
- [ ] T004 [FOUNDATION] Author the AUTHORITY MATRIX (categories x {read, summarize, derive,
      execute, connect, publish, create-truth, grant-approval}); only Core Authority is `yes`
      on create-truth and grant-approval. Each row must be a checkable statement. [FR-002, FR-008]
- [ ] T005 [FOUNDATION] Fix the two closed sub-vocabularies: Module = `{ read-only,
      artifact-writing, execution-capable }`; Adapter = `{ local-only, DB-connected,
      external-service-connected, publish-capable }`. Invent no parallel axis for the other
      three categories. [FR-003, FR-004]
- [ ] T006 [FOUNDATION] State the module-vs-adapter SEAM (external trust/connectivity boundary)
      and the Maintenance-Automation distinguisher (no per-invocation human trigger; derived
      evidence only; never truth/self-approval), so the categories are provably disjoint. [FR-005, FR-006]

**Checkpoint**: the categories, matrix, sub-vocabularies, seam, and Maintenance definition are
fixed and identical across the spec.

---

## Phase 3: User Story 1 - Classify any tool into exactly one category (Priority: P1) MVP

**Goal**: The spec classifies real surfaces into exactly one category with no overlap.

**Independent Test**: classify three shipped surfaces + one proposed surface; each lands in
one category with its sub-axis; the matrix says what each may and may not do.

- [ ] T007 [US1] In `spec.md`, author the shipped-feature classification table: Core Authority
      = the truth artifacts; Workflow Skills = conductor + gate verbs; read-only Modules =
      control room + grain reviewer; artifact-writing Modules = handoff pack + dashboard design;
      publish-capable Adapter = F016. Cite existing features; invent no new claim. [FR-014, SC-001]
- [ ] T008 [US1] State the orthogonality of the five categories to the Six product layers (a
      tool carries TWO coordinates) and confirm the layers are not replaced/renumbered. [FR-007, SC-006]
- [ ] T009 [US1] Verify the classification has no overlap: no surface lands in two categories;
      every Module/Adapter carries its sub-axis; the matrix forbids non-Core truth-creation. [SC-001, SC-002]

**Checkpoint**: any tool can be classified into exactly one category. MVP done.

---

## Phase 4: User Story 2 - Module vs Adapter seam (Priority: P1)

**Goal**: The spec deterministically separates an execution-capable Module from an Execution
Adapter on the trust-boundary discriminator.

**Independent Test**: a local-only executor classifies as Module / execution-capable; a
DB-connected / publishing executor classifies as Adapter; on the boundary alone.

- [ ] T010 [US2] In `spec.md`, author the seam discriminator + worked examples (local index
      rewrite -> Module / execution-capable; live-Postgres materialize -> Adapter / DB-connected;
      publish -> Adapter / publish-capable). [FR-005, SC-003]
- [ ] T011 [US2] Add the edge case "executes but only reads/summarizes -> read-only" so
      summarizing is not mistaken for executing, and prove the two categories disjoint. [SC-003]

**Checkpoint**: the module/adapter ambiguity is resolved deterministically.

---

## Phase 5: User Story 3 - Maintenance Automation as its own category (Priority: P2)

**Goal**: The spec places scheduled/CI tools in Maintenance Automation, distinct from a
human-invoked Module, with truth-creation and self-approval forbidden.

**Independent Test**: a scheduled nightly recomputation classifies as Maintenance Automation
(not a Module); the matrix grants read/summarize/derive/scheduled-execute but forbids
truth-creation and self-approval.

- [ ] T012 [US3] In `spec.md`, pin Maintenance Automation by "no per-invocation human trigger"
      + "derived evidence only" + "never truth / self-approval", and show it is where F031
      (adapter-maintenance) and F033 (release-maturity) slot in. [FR-006, SC-007]
- [ ] T013 [US3] Add the edge cases (a Maintenance tool that would publish -> forbidden; a
      Maintenance tool that would create truth -> forbidden) to keep it distinct from an Adapter
      and from Core Authority. [FR-002, FR-008]

**Checkpoint**: the novel category is defined sharply enough for F031/F033 to declare against.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Whole-feature gates that span all three stories.

- [ ] T014 Enumerate (do NOT create) the five future deliverables in `spec.md` + `plan.md`:
      `docs/architecture/product-modules.md`, `docs/architecture/core-vs-modules-and-adapters.md`,
      `docs/decisions/0006-core-authority-vs-product-modules.md`, `templates/module-contract.md`,
      `templates/adapter-contract.md` -- as planned outputs, never authored this slice. [FR-009]
- [ ] T015 Confirm no numeric/maturity score appears anywhere; readiness stays status +
      evidence + blockers; the deferred maturity concept is parked to F033. [FR-011]
- [ ] T016 [P] Run `retail check`: confirm exit 0 and that the diff adds no new rule (no rule, no checker,
      no stage added). [FR-010, FR-012, SC-005]
- [ ] T017 [P] Grep all five files for C086 / retail_store_sales leakage (billing codes,
      segment rollups, PII columns, per-table grain keys) -- expect zero. [FR-013, SC-004]
- [ ] T018 Confirm every file is ASCII + UTF-8 no BOM (no em-dash, arrow, or smart quote), each
      header states both `018` and `F024` plus the numbering note, and repo-relative paths stay
      short. [Principle IX]

---

## Phase 7: Future Implementation (the enumerated deliverables -- AUTHORED LATER, not this slice)

**Purpose**: Record the build tasks the five enumerated deliverables become when this contract
is implemented. These are FUTURE work; this slice writes none of them.

- [ ] T019 [FUTURE] Author `docs/architecture/product-modules.md`: the five categories + the
      authority matrix + the two sub-vocabularies, as the normative reference.
- [ ] T020 [FUTURE] Author `docs/architecture/core-vs-modules-and-adapters.md`: the prose
      narrative of the authority boundary + the module-vs-adapter seam + the worked shipped
      classification.
- [ ] T021 [FUTURE] Author `docs/decisions/0006-core-authority-vs-product-modules.md`: the ADR
      recording why the authority cut is orthogonal to the six layers and why only Core
      Authority owns truth.
- [ ] T022 [FUTURE] Author `templates/module-contract.md`: the copy-me declaration every Module
      fills (category + capability level + Core Authority read + derived evidence + forbidden ops).
- [ ] T023 [FUTURE] Author `templates/adapter-contract.md`: the copy-me declaration every Adapter
      fills (category + connectivity level + the gate it is downstream of + execution-only
      forbidden ops).
- [ ] T024 [FUTURE] Enumerate (still deferred) the conformance check that asserts every tool
      declares a category -- a later `retail check` rule or CI lint; not built with these docs.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies -- start immediately.
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories (it fixes the closed
  categories, the matrix, the sub-vocabularies, and the seam every story reuses).
- **User Stories (Phase 3-5)**: all depend on Foundational. US1 (P1) is the MVP. US2 (P1)
  depends on the seam (T006). US3 (P2) depends on the Maintenance definition (T006).
- **Polish (Phase 6)**: depends on all three stories complete.
- **Future Implementation (Phase 7)**: depends on this whole spec being approved; it is the
  NEXT slice, not this one.

### User Story Dependencies

- **US1 (P1)**: independent after Foundational -- the classification MVP.
- **US2 (P1)**: needs the seam fixed (T006).
- **US3 (P2)**: needs the Maintenance definition fixed (T006).

### Parallel Opportunities

- T001 and T002 (read inputs) run in parallel.
- Within Foundational, T003-T006 edit ONE file (`spec.md`) -- author in one pass; not parallel.
- Once Foundational is fixed, US1/US2/US3 add different sections of `spec.md`; sequence the
  edits but they are conceptually independent.
- Polish T016/T017 are independent checks -- parallel.

## Parallel Example: Setup phase

```
# The two input reads touch nothing and can run together:
T001 Re-read the Six product layers (docs/roadmap/roadmap.md)
T002 Re-read constitution Principles I/V + the shipped F005-F016 specs
```

## Implementation Strategy

**MVP first**: Setup -> Foundational -> US1 = a usable classification (any tool lands in one
category). Then US2 (seam) + US3 (Maintenance) sharpen the disjointness, then the Phase 6
whole-feature gates.

**Boundary discipline (the load)**: every section carries the same closed categories + matrix
+ seam from Phase 2; Phase 6 (T014-T018) proves no checker/rule/stage was added, no score
leaked, the layers were cited not replaced, and the five future deliverables stay enumerated
(not authored). Phase 7 is explicitly the NEXT slice -- the spec must never claim to ship it.
