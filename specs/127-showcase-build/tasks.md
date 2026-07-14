---
description: "Task list for feature 127-showcase-build"
---

# Tasks: Shareable Seshat Proof (Showcase Bundle)

**Input**: Design documents from `specs/127-showcase-build/`

**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/showcase-contract.md

**Tests**: INCLUDED. The success criteria (SC-001..008) are test-defined and the
truthfulness invariants (INV-1..6) must be mechanically enforced, so test tasks
are first-class here and precede their implementation.

**Organization**: Grouped by user story (US1..US5), each independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task serves
- Exact paths included

## Path Conventions

Single project: `src/seshat/showcase/`, `tests/unit/`, `tests/integration/`,
`.claude/skills/showcase-build/`. Reused modules under `src/seshat/` are NOT
modified.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create the `src/seshat/showcase/` package with `__init__.py` exporting `build_showcase_bundle` and `render_showcase_html` (stubs), and create `src/seshat/showcase/assets/` for the showcase shell.
- [ ] T002 [P] Create the `.claude/skills/showcase-build/` directory with a SKILL.md stub matching the contract in `contracts/showcase-contract.md` (trigger, inputs, procedure, refusals).
- [ ] T003 [P] Add test fixtures under `tests/fixtures/showcase/`: a worked-example-derived workspace, an all-missing workspace, a mixed-state workspace (available + deferred + missing + input-defect + machine-local absolute path), and a comparable/non-comparable Passport snapshot pair.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The read-only composition spine every story renders from. No user story can begin until the projection is composed and the offline/fail-closed write path is wired.

- [ ] T004 Implement `build_showcase_bundle(repo_root, *, snapshots=None)` in `src/seshat/showcase/build.py` to call `seshat.explorer.build.build_explorer_projection`, carry through `workspace` / `tables` / `lineage` / `disclosure` verbatim, and return the `ShowcaseBundle` shape from data-model.md (badge/manifest/comparison wired in later stories, initially empty). READ-ONLY: assert no source write.
- [ ] T005 Implement `render_showcase_html(bundle, *, repo, rtl=False)` skeleton in `src/seshat/showcase/build.py` rendering the landing page + per-table detail + lineage from the carried-through projection, inlining a NEW `showcase.css` / `showcase.js` and embedding the brand mark as a data URI. MUST NOT read `explorer.css` / `explorer.js`.
- [ ] T006 Wire the write path in the skill procedure (documented in SKILL.md): resolve output via `seshat.cli.guards.resolve_local_output` (refuse uncontained path, write nothing) and gate the write on `bundle["disclosure"]["status"] == "pass"` (fail-closed).
- [ ] T007 [P] Add a guard unit test `tests/unit/test_showcase_no_cli_verb.py` asserting `seshat.cli._DISPATCH` has no `showcase` key (FR-005) and that importing the showcase package adds no network/driver import (mirrors the B1/B3 lazy-import guard).

**Checkpoint**: Composition spine + offline fail-closed write path ready.

---

## Phase 3: User Story 1 - Render a Shareable Proof Bundle (Priority: P1) MVP

**Goal**: One offline bundle showing per-table stages/evidence/blockers/approvals/next-action/lineage, sourced only from the projection; nothing inferred.

**Independent Test**: Generate over the worked example, open offline, confirm all sections render from committed evidence and sources are unchanged.

### Tests for User Story 1

- [ ] T008 [P] [US1] Integration test `tests/integration/test_showcase_render.py`: generate over the worked-example fixture; assert every table's stages/evidence/blockers/approvals/next-action/lineage render; assert the bundle is self-contained (no external ref; assets inlined) (SC-001, FR-007/008).
- [ ] T009 [P] [US1] Integration test in the same file: generate over the all-missing fixture; assert missing artifacts show as missing, deferred as unavailable, input defects as defects, and NO stage renders as pass without evidence (SC-002, FR-003, INV-1).
- [ ] T010 [P] [US1] Integration test: assert source readiness artifacts AND `src/seshat/explorer/assets/explorer.css`/`explorer.js` are byte-unchanged after generation (SC-008, FR-004/025, INV-6).

### Implementation for User Story 1

- [ ] T011 [US1] Complete the per-table + lineage rendering in `render_showcase_html` (evidence state classes available/missing/deferred; input-defect entries; approvals timeline records `valid_shape` but grants nothing) reusing the projection's classifications (FR-001/003/004).
- [ ] T012 [US1] Add the "local offline snapshot from committed evidence; publishing is a separate explicit human action" footer/disclaimer to the render (FR-027).

**Checkpoint**: MVP bundle renders truthfully offline.

---

## Phase 4: User Story 2 - Truthful Badge / Project Card (Priority: P2)

**Goal**: An evidence-derived badge + card; no fabricated score; renders offline.

**Independent Test**: Stages 1-3 pass, stage 4 blocked -> badge reads a contiguous-passed summary, no %/grade, inline render.

### Tests for User Story 2

- [ ] T013 [P] [US2] Unit test `tests/unit/test_showcase_badge.py`: badge label for a stages-1-3-pass fixture names the highest contiguous stage + passed count and matches none of `/%/`, grade tokens, or numeric-confidence patterns (SC-003, FR-012/013, INV-2).
- [ ] T014 [P] [US2] Unit test: no-stage-passed fixture yields the truthful earliest-stage/onboarding label, never empty/celebratory (FR-015).
- [ ] T015 [P] [US2] Integration test in `test_showcase_render.py`: the badge renders as inline SVG / data URI with no external image fetch (FR-014).

### Implementation for User Story 2

- [ ] T016 [P] [US2] Implement `src/seshat/showcase/badge.py`: derive `highest_contiguous_pass`, `passed_stage_count`, `next_blocked_stage`, `label`, and inline `svg` from the projection stages (data-model Badge). No score.
- [ ] T017 [US2] Wire `badge` into `build_showcase_bundle` and render the badge + richer project card (per-table stage chips, blocker/approval counts) in `render_showcase_html`.

**Checkpoint**: Badge + card are truthful and offline.

---

## Phase 5: User Story 3 - Disclosure Manifest (Priority: P2)

**Goal**: Four-category ledger (included/redacted/omitted/unavailable); no silent drops; normalizations listed.

**Independent Test**: Mixed-state fixture -> each item under exactly one category with a locator.

### Tests for User Story 3

- [ ] T018 [P] [US3] Unit test `tests/unit/test_showcase_manifest.py`: on the mixed-state fixture, every reference in tables/lineage appears under exactly one manifest category (coverage + disjointness) (SC-004, FR-016/017/018, INV-3).
- [ ] T019 [P] [US3] Unit test: an absolute path is reduced to repo-relative AND listed under `redacted` with `original_class=absolute_path`; a deferred sentinel lands under `unavailable`; a missing artifact and an out-of-scope table land under `omitted` (FR-017/019).
- [ ] T020 [P] [US3] Integration test `tests/integration/test_showcase_disclosure.py`: a fixture whose composed content contains a secret / DSN / PII value / absolute path BLOCKS generation fail-closed and writes NO bundle file; findings are reported (SC-005, FR-009/010, INV-4).

### Implementation for User Story 3

- [ ] T021 [P] [US3] Implement `src/seshat/showcase/manifest.py`: build the four-category manifest from the projection (available->included, deferred/prose->unavailable, missing/defect/out-of-scope->omitted) and record composer normalizations under redacted.
- [ ] T022 [US3] Implement the portability normalization step (absolute path -> repo-relative label; private/internal URL stripped) feeding `redacted`, per research R3. If extending the shared scanner (preferred): add a private-URL rule to `src/seshat/disclosure.py` with its own unit test and confirm the shared scanner stays fail-closed for the existing consumers; else strip composer-locally and list under redacted.
- [ ] T023 [US3] Wire `manifest` into `build_showcase_bundle` and render the manifest section in `render_showcase_html`.

**Checkpoint**: Manifest is complete, disjoint, and honest; disclosure stays fail-closed.

---

## Phase 6: User Story 4 - Before/After Only When Comparable (Priority: P3)

**Goal**: Diff two comparable Passport snapshots; omit gracefully otherwise; never fabricate a delta.

**Independent Test**: Comparable pair diffs; mismatched-scope pair omitted with a note.

### Tests for User Story 4

- [ ] T024 [P] [US4] Unit test `tests/unit/test_showcase_compare.py`: comparable pair (same schema+scope, differing revision) yields real `stage_transitions` + `evidence_verdicts` in the Passport verify vocabulary (SC-006, FR-020/021).
- [ ] T025 [P] [US4] Unit test: mismatched-scope, mismatched-schema, single-snapshot, and no-snapshot cases each set `comparable=false` with an `omitted_reason` and produce NO fabricated delta (FR-021, INV-5).

### Implementation for User Story 4

- [ ] T026 [P] [US4] Implement `src/seshat/showcase/compare.py`: load two snapshots, decide comparability (same `schema_version` + `scope`, differing `source_revision`), and compute stage transitions + evidence verdicts reusing `seshat.passport.verify_passport` vocabulary. Read-only.
- [ ] T027 [US4] Wire optional `comparison` into `build_showcase_bundle` (only when `snapshots` supplied) and render the before/after section (omitted with note when not comparable) in `render_showcase_html`.

**Checkpoint**: Before/after appears only when honest.

---

## Phase 7: User Story 5 - Accessible, Responsive, RTL/Arabic Shell (Priority: P3)

**Goal**: Shell aligned to spec-102 a11y rules; responsive; RTL/Arabic-safe; explorer assets untouched.

**Independent Test**: Shell passes spec-102 contrast/colorblind; reflows narrow with no body horizontal scroll; renders under `dir="rtl"` with Arabic labels.

### Tests for User Story 5

- [ ] T028 [P] [US5] Integration test `tests/integration/test_showcase_a11y_rtl.py`: the shell palette/text satisfy the spec-102 `design_contrast` and `design_categorical_distinctness` thresholds (reuse the shipped rule logic against the shell palette) (SC-007, FR-022).
- [ ] T029 [P] [US5] Integration test: `rtl=True` renders `dir="rtl"` with correct `lang` and Arabic sample labels without breakage; a narrow-width render has no horizontal body scroll (wide content in its own scroll container) (FR-023/024).
- [ ] T030 [P] [US5] Integration test: re-assert `explorer.css`/`explorer.js` are byte-unchanged after an RTL render (FR-025, INV-6).

### Implementation for User Story 5

- [ ] T031 [P] [US5] Author `src/seshat/showcase/assets/showcase.css` (and `showcase.js` if needed): responsive layout (no body horizontal scroll; wide content scrolls in-container), spec-102-aligned palette/contrast, and RTL-aware rules (logical properties / `[dir=rtl]` mirroring).
- [ ] T032 [US5] Add the `rtl` render mode to `render_showcase_html` (`dir`/`lang`, Arabic-ready label slots) and document the mode in SKILL.md.

**Checkpoint**: The shell is accessible, responsive, and RTL/Arabic-safe.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T033 [P] Verify the truthfulness invariants end-to-end: no fabricated score/claim/delta/approval/pass across all fixtures (FR-026); add a consolidated assertion in `test_showcase_render.py` if not already covered.
- [ ] T034 [P] Finalize `.claude/skills/showcase-build/SKILL.md`: complete procedure, refusals (uncontained path, blocking finding, publish request), and the "publishing is a separate explicit human action" note (FR-005/011/027).
- [ ] T035 Run the full CI gate set locally: `ruff format --check src tests`, `ruff check src tests`, `pytest -m unit -q`, `retail check`, `retail semantic-check`; confirm all green and the new package carries no committed DSN/secret (C2).
- [ ] T036 [P] Run quickstart.md end-to-end against the worked example; confirm the bundle opens offline, the badge/manifest read as documented, and `git status` shows only contained-output files.

---

## Dependencies & Execution Order

- **Setup (T001-T003)**: no dependencies.
- **Foundational (T004-T007)**: depends on Setup; BLOCKS all user stories (the composition spine + write path).
- **US1 (T008-T012)**: depends on Foundational. The MVP.
- **US2 (T013-T017)**, **US3 (T018-T023)**: depend on Foundational; independent of each other; both build on the US1 render surface but are independently testable via `build_showcase_bundle` fields.
- **US4 (T024-T027)**: depends on Foundational; independent (optional section).
- **US5 (T028-T032)**: depends on Foundational + the US1 render skeleton (renders the shell around it); independent of US2/US3/US4 content.
- **Polish (T033-T036)**: after all targeted stories.

### Within each story

- Tests are written FIRST and must FAIL before implementation.
- Reuse before re-implement: any task that would re-derive readiness/evidence/disclosure is a defect (see the spec Reuse Map).
- Commit after each task or logical group.

### Parallel opportunities

- T002/T003 (setup) parallel.
- All `[P]` test tasks within a story parallel (distinct files).
- `badge.py` (T016), `manifest.py` (T021), `compare.py` (T026), `showcase.css` (T031) are distinct files -> parallel once Foundational is done.

---

## Implementation Strategy

### MVP first (US1)

1. Setup -> Foundational -> US1.
2. STOP and validate: bundle renders truthfully offline over the worked example and the all-missing fixture; sources + explorer assets unchanged.

### Incremental delivery

US1 (MVP) -> US2 (badge) -> US3 (manifest) -> US4 (before/after) -> US5 (a11y/RTL). Each adds value without breaking the prior; US3's fail-closed disclosure and US5's untouched-explorer-assets checks are the load-bearing guards.

## Notes

- No new top-level CLI verb (Option B); the surface is the skill over the library function.
- The feature gates nothing and advances no readiness stage; it renders committed truth.
- ASCII + UTF-8-no-BOM for all tracked text; keep repo-relative paths short (Windows MAX_PATH).
