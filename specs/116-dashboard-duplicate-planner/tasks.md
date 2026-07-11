---
description: "Task list for Non-Duplicate Dashboard Planner implementation"
---

# Tasks: Non-Duplicate Dashboard Planner

**Input**: Design documents from `specs/116-dashboard-duplicate-planner/`

**Prerequisites**: plan.md, spec.md. (The finer companion docs -- research.md,
data-model.md, contracts/ -- are OPTIONAL implement-time outputs, not authored in
this spec-only slice; the data model and verifier contract are fixed inline in
plan.md's Summary + Technical Context and in the task descriptions below.)

**Tests**: INCLUDED. The output-faithfulness verifier IS the feature's mechanical
guarantee (the reason this is a Python classifier, not a skill), and the repo
mandates TDD -- so test tasks are first-class, written before the code they verify.
The verifier sits ON the classification OUTPUT, independent of the classifier
(MEMORY: "verifier must sit on the risk"; never read ground truth from the code
under test).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- Paths are repo-relative; single-project layout (`src/retail`, `tests/unit`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: fixtures + module skeleton every story leans on.

- [x] T001 [P] Add dashboard-planner fixtures under `tests/unit/fixtures/dashboard_planner/`: `has_page/design/` (a committed corpus modeled on `mappings/retail_store_sales/design/` -- a `dashboard-layout.md` with business questions, a `visual-list.md`, and a `visual-contract-binding-map.md` binding measure-bearing visuals to contracts + dimensions), `two_page/design/` (a corpus with TWO committed pages sharing/splitting tuples, for the multi-page precedence case, FR-004), `empty_design/design/` (dir present, no readable page), and `no_design/` (a table dir with NO `design/` subdir, for `new by absence`, FR-007). ASCII, UTF-8 no BOM; no C086-specific value baked in (generic, Principle VII).
- [x] T002 Create the classifier module skeleton `src/retail/dashboard_planner.py` with the public signatures `classify_proposal(repo_root, table, proposal) -> dict` and `render(verdict, fmt) -> str` (bodies raise `NotImplementedError`), plus a private `_load_design_corpus(design_dir)` helper (utf-8-sig read of the three design files; returns an empty corpus on missing dir / OSError / parse error, never raising). No DB/driver import at module load (driver-free import path, Principle VIII).

**Checkpoint**: fixtures exist; module imports; no DB/driver import at load.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared tuple-reduction + set-relationship core + the verifier every story's tests use.

CRITICAL: no user-story test can assert a verdict until the tuple-reduction core and the verifier exist.

- [x] T003 [US-shared] Implement the corpus-to-tuples reduction in `src/retail/dashboard_planner.py`: parse each committed page in the design corpus into its SET of `(business_question, bound_contract, dimension)` tuples (the data model fixed in plan.md's Summary + Technical Context) -- business questions from `dashboard-layout.md`, visuals from `visual-list.md`, each visual's approved contract + mapped dimension from `visual-contract-binding-map.md`. EXCLUDE slicer-only dimensions (not measure-bound; per the layout's own note). The match key is `(bound_contract, dimension)` compared by EXACT committed value (FR-002, FR-003) -- never fuzzy, never by question-text similarity.
- [x] T004 [US-shared] Implement the proposal-to-tuples reduction + the set-relationship decision core in `src/retail/dashboard_planner.py`: reduce the caller-supplied proposal to `(business_question?, bound_contract, dimension)` tuples AS GIVEN (the same tuple model fixed in plan.md; no enrichment, no invented tuple/metric, FR-006); then decide the verdict by SET MEMBERSHIP (FR-003) -- `duplicate of P` iff the proposal has >=1 readable tuple AND shares >=1 with P AND every proposal tuple is covered by page P; `extends P` iff shares >=1 and adds >=1; `new` iff disjoint from all pages OR the proposal has no readable tuple (an empty proposal is `new`, never a vacuous duplicate). The three verdicts are mutually exclusive and exhaustive. Multi-page precedence `duplicate` > `extends` > `new` naming the strongest-matched page (FR-004). NO overlap number / threshold / ranking anywhere (hard rule #9, FR-010). Return the verdict dict incl. verdict value, matched-page name, cited matched rows, added tuples, and `read_only: True`. `render` still stubbed.
- [x] T005 [US-shared] Write the reusable output-faithfulness verifier helper `assert_verdict_is_faithful(output_text_or_obj, corpus, proposal)` in `tests/unit/test_dashboard_planner.py` (the verifier contract fixed inline in plan.md's Summary): (V1) verdict is one of `new` / `extends <page>` / `duplicate of <page>`; (V2) every cited matched row (page + row id + contract + dimension) EXISTS in the parsed corpus (no fabricated citation, FR-005); (V3) the named page for a `duplicate`/`extends` verdict exists in the corpus; (V4) NO numeric-score / overlap / percentage / ranking token appears in the output (FR-010); (V5) the proposal tuples are echoed as supplied, none invented (FR-006). The verifier reads corpus ground truth from the FIXTURE FILES, NOT from the classifier under test (independence). TEST helper only -- NO `@register` rule, NO manifest change (FR-009).

**Checkpoint**: `classify_proposal` returns a correct verdict dict for all fixtures; verifier helper importable and independent of the classifier.

---

## Phase 3: User Story 1 - Categorical new/extends/duplicate verdict (Priority: P1) -- MVP

**Goal**: one categorical verdict per proposal, decided by set membership over committed tuples, with the matched page named.

**Independent Test**: run against `has_page` with a proposal re-stating a committed cut -> `duplicate of <page>` citing that row; with a superset proposal -> `extends <page>`; with a disjoint proposal -> `new`. No score anywhere.

### Tests for User Story 1 (write first, must FAIL)

- [x] T006 [P] [US1] In `tests/unit/test_dashboard_planner.py`, add `test_duplicate_verdict`, `test_extends_verdict`, and `test_new_verdict` against the `has_page` fixture; each composes the verdict and runs `assert_verdict_is_faithful`; assert the correct categorical value, the named matched page, and (SC-002) that no numeric/overlap/ranking token appears. Assert FAIL before T009.
- [x] T007 [P] [US1] In the same file, add `test_multi_page_precedence` against the `two_page` fixture: a proposal matching rows on two pages resolves to a single verdict by the fixed `duplicate` > `extends` > `new` precedence, naming one page, never two conflicting verdicts (FR-004). Assert FAIL before T009.

### Implementation for User Story 1

- [x] T008 [US1] Implement `render` in `src/retail/dashboard_planner.py` for text + `--format json`: the verdict line (`VERDICT: duplicate of <page>` / `extends <page>` / `new`), the cited matched committed rows (file + row id + contract + dimension), and (for `extends`) the added proposal tuples. ASCII `--`/`->`, no glyphs, no numeric/overlap/ranking token (FR-015).
- [x] T009 [US1] Add the CLI verb `src/retail/cli/commands/dashboard_planner.py` (`retail dashboard-planner --table <t> --proposal <text-or-@file> [--tuple <q>::<contract>::<dim> ...] [--format text|json]`) mirroring `cli/commands/blockers.py` / `next.py`; it PRINTS only, contains no file-write path (FR-008), and always returns exit 0 (FR-009).
- [x] T010 [US1] Register + dispatch the `dashboard-planner` subcommand in `src/retail/cli/parser.py` and the CLI dispatch table (`src/retail/cli/__init__.py`), following the shipped `blockers`/`next` wiring.

**Checkpoint**: MVP -- `retail dashboard-planner --table retail_store_sales --proposal "TotalSales by category"` prints `duplicate of` the overview page citing v06; US1 tests green.

---

## Phase 4: User Story 2 - Proposal ingested, verdict cites committed evidence (Priority: P1)

**Goal**: the proposal is classified AS GIVEN (no invented tuple/metric) and every match cites a real committed row; an unknown-measure tuple is adds-new, never matched by an invented contract.

**Independent Test**: run with a structured proposal (one matching tuple + one unknown-measure tuple) -> `extends`, echoing both tuples verbatim, citing the real committed row for the matched one, marking the unknown one adds-new; no invented contract.

### Tests for User Story 2 (write first, must FAIL)

- [x] T011 [P] [US2] In `tests/unit/test_dashboard_planner.py`, add `test_proposal_echoed_not_invented` (SC-003 / FR-006): assert the output reproduces the supplied proposal tuples verbatim and adds no tuple/question/metric the caller did not supply. Assert FAIL before T013.
- [x] T012 [P] [US2] Add `test_unknown_measure_is_adds_new` and `test_every_citation_exists` (FR-005/FR-006): a proposal measure with no committed contract is treated as adds-new (no invented contract, no emitted metric definition), and every cited row exists in the corpus. Assert FAIL before T013.

### Implementation for User Story 2

- [x] T013 [US2] Extend the reduction/decision + `render` so: (a) the proposal is echoed exactly as supplied (FR-006); (b) an `extends`/`duplicate` verdict cites each matched committed row (file + row id + contract + dimension) and an `extends` verdict names the absent proposal tuple(s) (FR-005); (c) a proposal measure absent from the binding map is classified adds-new, never matched by inventing a contract and never emitting a metric definition. No score/overlap token.

**Checkpoint**: verdicts are auditable against the corpus; the proposal is never rewritten; US1 + US2 green.

---

## Phase 5: User Story 3 - Missing/unreadable corpus -> new by absence (Priority: P2)

**Goal**: a missing/empty/unreadable `mappings/<table>/design/` corpus yields `new by absence` naming the path checked, never an empty view read as "found distinct".

**Independent Test**: point at `no_design` (no `design/` dir) -> `new by absence` naming the path; point at `empty_design` -> `new by absence` naming what was checked; no fabricated page.

### Tests for User Story 3 (write first, must FAIL)

- [x] T014 [P] [US3] In `tests/unit/test_dashboard_planner.py`, add `test_missing_corpus_new_by_absence` and `test_empty_corpus_new_by_absence` (FR-007 / SC-005): assert the verdict is `new` qualified "by absence -- no committed dashboard design found at <path>", the path is named, and no committed page/visual is fabricated. Assert FAIL before T015.

### Implementation for User Story 3

- [x] T015 [US3] Extend `classify_proposal`/`render` for the absent/empty/unreadable corpus: return `new` with the explicit `by absence` qualifier and the checked path; never present an absent corpus as "compared and found distinct" and never fabricate a page.

**Checkpoint**: all three stories independently functional; every fixture covered.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T016 [P] Add the tool doc `docs/tools/dashboard-planner.md` mirroring `docs/tools/blocker-explainer.md` (what it is, how to run, the scope wall, and what it will NOT do -- names all three neighbors: retargets `idea-engine.js`'s verdict shape, reads `dashboard-design`'s output as corpus but authors nothing, is not `dashboard-qa`).
- [x] T017 [P] [US-shared] Add the read-only / writes-nothing proof test (V-write, SC-004): run the CLI verb against a temp copy of a table dir; assert `git status` shows NO new/modified file and the classifier module contains no file-write call (grep-verifiable), matching the shipped read-only surfaces.
- [x] T018 [P] [US-shared] Add the generic proof test (SC-006): run the SAME classifier over `retail_store_sales`'s real committed `design/` corpus and a second distinct fixture table with no per-table branch in the classifier.
- [x] T019 Run `quickstart.md` end-to-end against `retail_store_sales`: confirm the `duplicate of` verdict on a committed cut, an `extends` on a superset, a `new` on a disjoint proposal, and zero score/overlap/ranking tokens. Run `ruff format --check src tests` + `ruff check src tests` + `pytest tests/unit/test_dashboard_planner.py -q`; confirm `retail check` still exits 0 and the rules-manifest count is UNCHANGED (proves no gate was added, FR-009).

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> User Stories (3-5) -> Polish (6).
- Phase 2 BLOCKS all stories (the tuple-reduction core, the set-relationship
  decision, and the verifier are shared).

### Story dependencies

- US1 (P1): after Phase 2. The MVP (the categorical verdict).
- US2 (P1): after Phase 2; extends the reduction/decision + `render` (shares
  T004/T008's functions, so sequence after them to avoid a same-file conflict).
- US3 (P2): after Phase 2; extends `classify_proposal`/`render` (sequence after
  T008/T013 for the same reason).

### Within each story

- Test first (must FAIL) -> implementation -> checkpoint.
- Corpus-to-tuples reduction (T003) + decision core (T004) before any render
  (T008/T013/T015).

### Parallel opportunities

- T001 fixtures are [P] with each other's authoring.
- The per-story TEST tasks (T006/T007, T011/T012, T014) are [P] within a story
  (distinct test functions), but each precedes its own implementation task.
- Polish tasks T016/T017/T018 are [P] (distinct files); T019 is the final serial gate.
- NOTE: T008, T013, T015 all edit `render`/the decision core in one file -> NOT
  parallel; run in story-priority order.

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational -> Phase 3 US1.
2. STOP and validate: `retail dashboard-planner --table retail_store_sales
   --proposal "TotalSales by category"` returns `duplicate of` the overview page
   citing v06; US1 tests green.

### Incremental delivery

- +US2 (proposal-ingest + cited evidence, the auditability half) -> +US3
  (missing-corpus robustness) -> Polish (tool doc, writes-nothing + generic proofs,
  full gate run).

---

## Notes

- [P] = different files, no incomplete-task dependency.
- The verifier (T005) is TEST-only -- no `@register` rule, no manifest change
  (FR-009 forbids a gate). It reads corpus ground truth from the fixture files, NOT
  from the classifier under test (independence; MEMORY "verifier must sit on the
  risk").
- The verdict is decided by SET MEMBERSHIP over committed tuples -- NO overlap
  number, threshold, or ranking anywhere (hard rule #9, FR-003/FR-010).
- The planner WRITES NOTHING and adds NO template output file (unlike spec 114):
  its output is a transient printed triage answer.
- ASCII only, UTF-8 no BOM in every authored file (Principle IX).
- Commit after each task or logical group; each checkpoint is independently testable.
- FR coverage: FR-001 (T009), FR-002 (T003), FR-003 (T004), FR-004 (T004/T007),
  FR-005 (T013), FR-006 (T004/T013), FR-007 (T015), FR-008 (T009/T017), FR-009
  (T005/T019), FR-010 (T004/T005), FR-011 (T002/T017), FR-012 (T003/T005), FR-013
  (T018), FR-014 (T004), FR-015 (T008).
