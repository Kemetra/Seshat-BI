---
description: "Task list for Dashboard Gap Detector implementation"
---

# Tasks: Dashboard Gap Detector

**Input**: Design documents from `specs/117-dashboard-gap-detector/`

**Prerequisites**: plan.md, spec.md

**Tests**: INCLUDED. The independent-oracle status verifier is the feature's
mechanical guarantee -- it sits ON the real risk (an uncovered/undecided
required item silently classified `Covered`), with an expected-status oracle
hand-declared per fixture, NEVER read back from the classifier under test. Repo
mandates TDD, so tests precede code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- Paths repo-relative; single-project layout (`src/retail`, `tests/unit`).
- Each task cites the FR(s) it delivers.

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 [P] Add fixtures under `tests/unit/fixtures/gap_detector/`:
  `mixed/` (a page-intent naming required metrics + dimensions, and a target
  table whose `metrics/` has one `pass` contract [-> Covered], one present-but-
  `not_started` contract [-> Blocked -- needs business definition], and a
  required metric with NO contract file [-> Planned]; a `source-map.yaml`
  `gold_star` that CONTAINS one required dimension [-> Covered] and OMITS
  another [-> Blocked -- missing field]; and one required subject the table
  cannot serve [-> Out of scope]); `open_decision/` (page-intent whose required
  metric depends on an OPEN `unresolved-questions.md` row, owner governance,
  plus a second OPEN analyst row); `all_answered/` (all `unresolved-questions.md`
  rows `answered`, Gate status CLEARED -- the `retail_store_sales` shape);
  `edge_cases/` (a required metric whose contract IS `pass` but whose `binds_to`
  gold column is ABSENT from `gold_star` [-> Blocked -- missing field, not a
  silent Covered]; and a page-intent item whose name matches NO committed metric
  or dimension [-> unmatched-item GAP]); `no_page_intent/` (table present, no
  page-intent supplied); `missing_source_map/` (page-intent present, no
  `source-map.yaml`); `missing_metrics/` (page-intent present, no `metrics/`
  directory); `missing_questions/` (page-intent present, no
  `unresolved-questions.md`); and a `second_table/` distinct conformant table for
  the generic proof. ASCII, UTF-8 no BOM. (FR-001..FR-006, FR-013, FR-014)
- [x] T002 Create the composer skeleton `src/retail/gap_detector.py` with
  `build_gap_inventory(repo_root, table, page_intent) -> dict` and
  `render_view(view) -> str` (raise `NotImplementedError`), reusing the
  `_load_yaml_mapping` idiom and a small committed-markdown-table parser for the
  `unresolved-questions.md` Open-questions table. No DB/driver import at module
  load; NO file-write call. (FR-010, FR-012)

**Checkpoint**: fixtures exist, module imports.

---

## Phase 2: Foundational (Blocking Prerequisites)

CRITICAL: the shared status-enum extraction + the independent-oracle verifier gate every story.

- [x] T003 Extract the shared status vocabulary: create
  `src/retail/coverage_status.py` holding `_ENUM` (the closed five-value set) +
  a `_norm(cell)` membership/normalize helper, MOVED verbatim from
  `src/retail/rules/scorecard.py`; update `scorecard.py` to import them.
  Behavior-preserving move-refactor (plan Structure Decision). (FR-002, FR-008)
- [x] T004 [P] Regression-lock: confirm/extend `tests/unit/test_scorecard.py`
  asserts `check_coverage_scorecard` output is BYTE-IDENTICAL after T003 (SL1
  Findings unchanged; the rule still emits on the same fixtures). Must be green
  before proceeding. (FR-008)
- [x] T005 [US-shared] Write the independent-oracle status verifier
  `assert_status_inventory_sound(view, expected_status_by_item)` in
  `tests/unit/test_gap_detector.py`: (V1) every emitted per-item status is a
  member of `coverage_status._ENUM` (imported directly -- proves "matches SL1");
  (V2) the CRITICAL never-false-Covered check -- no item whose HAND-DECLARED
  expected status is not `Covered` is classified `Covered` by the detector (the
  oracle `expected_status_by_item` is authored in the test from the fixture's
  ground truth, NEVER read back from `build_gap_inventory`'s own output, else the
  check is circular -- spec 114/115's independent-oracle discipline); (V3) every
  non-`Covered` item carries a named blocker citing a committed path; (V4) no
  numeric token (score / percentage / count) appears anywhere in `render_view`
  output. TEST-only -- NO `@register` rule, NO manifest change (FR-008). (FR-002,
  FR-007, FR-011)
- [x] T006 Implement the classification core in `src/retail/gap_detector.py`:
  read the page-intent + the three committed inputs; for each required METRIC,
  classify by `metrics/<Metric>.yaml` `readiness.status` (pass -> Covered;
  present-but-not-pass OR blocked-by-open-decision -> Blocked -- needs business
  definition; no contract file -> Planned; FR-003); for each required DIMENSION,
  classify by presence in `source-map.yaml` `gold_star`
  (`dimensions[]`/`date_dimension`/`degenerate_dimensions[]`): present ->
  Covered; absent -> Blocked -- missing field (FR-004); an out-of-domain subject
  -> Out of scope (FR-005); assign each status from the imported `_ENUM` only
  (FR-002). Match a page-intent item to a committed metric/dimension by its
  recorded NAME (exact, never fuzzy); an item that matches nothing committed ->
  a GAP (unmatched required item), never silently dropped and never fuzz-matched
  (spec Edge Cases). For a metric whose contract IS `pass` but whose `binds_to`
  gold column is NOT in the committed `gold_star` -> `Blocked -- missing field`
  naming the intra-artifact disagreement (never a silent `Covered` over a
  committed inconsistency; spec Edge Cases). Return the GapInventory dict incl.
  `document_gaps[]` for missing inputs and `read_only: True`. `render_view` still
  stubbed. (FR-002..FR-005, FR-013)

**Checkpoint**: `build_gap_inventory` returns a correctly-classified model for
all fixtures; verifier importable and passing V1/V2 on `mixed/`.

---

## Phase 3: User Story 1 - Designer sees every design-blocking gap before drawing (Priority: P1) -- MVP

**Goal**: per-item categorical status (from SL1's enum) + named blocker for the whole supplied page-intent, before any visual is placed.

**Independent Test**: run against `mixed/` -> Covered / Blocked -- needs business definition / Planned / Blocked -- missing field / Out of scope each appear on the right item; every non-Covered item names a blocker; no numeric token.

### Tests for User Story 1 (write first, must FAIL)

- [x] T007 [P] [US1] In `tests/unit/test_gap_detector.py`, add
  `test_mixed_statuses` and `test_all_covered_nothing_blocks`: compose for
  `mixed/` and a clean page-intent over `all_answered/`, run
  `assert_status_inventory_sound` with the hand-declared oracle; assert the five
  statuses land on the correct items (V1/V2), each non-Covered item names a
  blocker + path (V3), and the all-covered case states plainly "nothing blocks
  design", records no `pass`, emits no score (V4). Also add
  `test_edge_binds_to_mismatch_and_unmatched_item` over `edge_cases/`: a `pass`
  contract whose `binds_to` gold column is absent from `gold_star` is
  `Blocked -- missing field` (NOT `Covered`; V2), and a page-intent item that
  matches nothing committed is an unmatched-item GAP (never dropped, never
  fuzz-matched). Assert FAIL before T008. (FR-002, FR-003, FR-004, FR-005,
  FR-007, FR-011, FR-013)

### Implementation for User Story 1

- [x] T008 [US1] Implement `render_view` for the ordered per-item inventory
  (status + named blocker per required item) + the "nothing blocks design" empty
  case, per plan. Ordering, if any, uses a FIXED key (e.g. item order in the
  page-intent, then a fixed status order), never a computed score. ASCII
  `--`/`->`, no glyphs, no numeric token, ASCII status strings
  (`Blocked -- missing field`). (FR-007, FR-011, FR-015)
- [x] T009 [US1] Add the CLI verb `src/retail/cli/commands/gap_detector.py`
  (`retail dashboard-gaps --table <t> --page-intent <path> [--format text|json]`)
  mirroring `cli/commands/blockers.py`; no `--write` (FR-010); always exit 0 (no
  gate; FR-008). (FR-001, FR-008, FR-010)
- [x] T010 [US1] Register + dispatch the `dashboard-gaps` subcommand in
  `src/retail/cli/parser.py` and the CLI dispatch table
  (`src/retail/cli/__init__.py`). (FR-008)

**Checkpoint**: MVP -- `retail dashboard-gaps --table <t> --page-intent <path>`
prints the per-item status inventory; `mixed/` classifies correctly; US1 tests +
regression-lock green.

---

## Phase 4: User Story 2 - Open owner decisions block design and are surfaced as gaps (Priority: P1)

**Goal**: OPEN `unresolved-questions.md` rows a required item depends on surface as `Blocked -- needs business definition` gaps, owner + question verbatim; answered rows never do.

**Independent Test**: run against `open_decision/` -> the dependent required metric is Blocked -- needs business definition naming the row's `Who must answer` owner + verbatim question; against `all_answered/` -> no answered row becomes an open gap.

### Tests for User Story 2 (write first, must FAIL)

- [x] T011 [P] [US2] In `tests/unit/test_gap_detector.py`, add
  `test_open_decision_blocks_dependent_metric` (OPEN row -> dependent required
  metric is Blocked -- needs business definition, blocker names owner + verbatim
  question + `unresolved-questions.md` path; unrecognized owner echoed verbatim)
  and `test_answered_decision_not_a_gap` (all-`answered`/CLEARED -> no
  owner-decision gap). The OPEN-row oracle (which rows are open + their owners)
  is HAND-DECLARED in the test, not read from the production parser (else a
  parser bug drops the row from both sides and passes vacuously). Assert FAIL
  before T012. (FR-006, FR-007)

### Implementation for User Story 2

- [x] T012 [US2] Wire the Open-questions parse + owner echo into the classifier
  and `render_view`: a required item that depends on an OPEN row (Status !=
  answered AND doc Gate status != CLEARED) -> `Blocked -- needs business
  definition`; the blocker names the row's `Who must answer` owner (verbatim,
  including an unrecognized owner) and quotes the question text verbatim, citing
  the path; openness is read from the STRUCTURED `Status` column only, never from
  scoring the question prose. (FR-006, FR-007)

**Checkpoint**: open decisions surface as owner-named gaps; answered ones do not; US1 + US2 green.

---

## Phase 5: User Story 3 - Missing/unreadable input surfaced, not fabricated (Priority: P2)

**Goal**: a missing page-intent or a missing committed input yields a document-level GAP naming the path; an unclassifiable item is a GAP, never a silent `Covered`.

**Independent Test**: run against `no_page_intent/` and `missing_source_map/`.

### Tests for User Story 3 (write first, must FAIL)

- [x] T013 [P] [US3] In `tests/unit/test_gap_detector.py`, add
  `test_no_page_intent_document_gap` (no page-intent -> document-level GAP naming
  the missing input, no fabricated required list, no "nothing blocks design")
  and `test_missing_source_map_not_covered` (page-intent present but
  `source-map.yaml` absent -> document-level GAP naming the path; a required
  dimension it could not check is reported as an unresolved GAP, NEVER `Covered`;
  V2). Also add `test_missing_metrics_dir` and `test_missing_questions_file`
  (US3 AS2: a missing `metrics/` directory or a missing `unresolved-questions.md`
  each yields a document-level GAP naming the path; the affected required items
  are unresolved GAPs, never `Covered`, and a missing questions file is never
  presented as "no open decisions"). Assert FAIL before T014. (FR-001, FR-013)

### Implementation for User Story 3

- [x] T014 [US3] Extend `build_gap_inventory`/`render_view` for input absence:
  populate `document_gaps[]` and render an "Inputs not available" section naming
  each missing/unreadable path; when page-intent is absent, emit the
  document-level GAP and classify nothing; when a committed input is absent, mark
  the items it would have classified as unresolved GAPs, never `Covered`. No
  fabricated items. (FR-001, FR-013)

**Checkpoint**: input-absence honest; all three stories functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Add the tool doc `docs/tools/dashboard-gap-detector.md` mirroring
  `docs/tools/blocker-explainer.md`: what it is, how to run, the scope wall, and
  the explicit boundaries against SL1 (vocabulary reuse, not the rule),
  `dashboard-design` (pre-design inventory vs the gated per-visual verb), and
  consumer-data-dictionary (design-coverage gap vs meaning-citation gap); what it
  will NOT do (no gate, no pass, no write, no score). (FR-007, FR-008)
- [x] T016 [P] [US-shared] Add the no-write proof test (SC-007): grep the module
  for zero write calls; a default run changes no tracked file (`git status`
  clean); `build_gap_inventory` triggers no DB/network import. (FR-009, FR-010)
- [x] T017 [P] [US-shared] Add the generic proof test (SC-010): run the SAME
  composer over the `mixed/` table and `second_table/` with no per-table branch;
  and the vocabulary-parity test (SC-002): assert the detector's status set
  equals `coverage_status._ENUM` (imported), proving it matches SL1 with no
  minted status. (FR-002, FR-014)
- [x] T018 Final gate: run `ruff format --check src tests` + `ruff check src
  tests` + `pytest tests/unit/test_gap_detector.py tests/unit/test_scorecard.py
  -q`; confirm `retail check` still exits as before and the rules-manifest count
  is UNCHANGED (no gate added, FR-008/SC-009), and SL1's output is unchanged
  after the `_ENUM` extraction (T004). Confirm output carries no numeric token
  (SC-003) and every status is in SL1's enum (SC-002). (FR-008, FR-011, SC-002,
  SC-003, SC-009)

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (1) -> Foundational (2) -> User Stories (3-5) -> Polish (6).
- Phase 2 BLOCKS all stories: T003 `_ENUM` extraction (+ T004 regression-lock)
  and the T006 classification core + T005 independent-oracle verifier are shared.

### Story dependencies

- US1 (P1): after Phase 2. The MVP.
- US2 (P1): after Phase 2; T012 shares the classifier + `render_view` with
  T006/T008 -> sequence after T008 (same file).
- US3 (P2): after Phase 2; T014 shares `build_*`/`render_view` -> sequence after
  T008/T012.

### Within each story

- Test first (must FAIL) -> implementation -> checkpoint.
- T003 extraction + T004 lock BEFORE T006 (the core imports the extracted enum).
  T006 before any `render_view` task.

### Parallel opportunities

- T001 fixtures [P] with T005 verifier authoring.
- T004 regression-lock [P] once T003 lands.
- Per-story TEST tasks (T007, T011, T013) [P] with each other; each precedes its
  own implementation.
- Polish T015/T016/T017 [P]; T018 is the final serial gate.
- NOTE: T008, T012, T014 all edit `render_view`/`build_gap_inventory` in one file
  -> NOT parallel; run in story order.

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 -> Phase 2 (incl. the T003 extraction + T004 lock) -> Phase 3 US1.
2. STOP and validate: `retail dashboard-gaps --table <t> --page-intent <path>`
   prints the correct per-item status inventory over `mixed/`; US1 +
   regression-lock green.

### Incremental delivery

- +US2 (open-decision ingestion) -> +US3 (input-absence honesty) -> Polish (tool
  doc, no-write + generic + vocabulary-parity proofs, full gate run +
  manifest-unchanged confirmation).

---

## Notes

- [P] = different files, no incomplete-task dependency.
- The verifier (T005) is TEST-only -- no `@register` rule, no manifest change
  (FR-008 forbids a gate).
- T003 is a behavior-preserving MOVE-refactor of the shipped SL1 `_ENUM`,
  regression-locked by T004 -- keeps SL1 output byte-identical and the CodeScene
  new-code-health gate green.
- The status verifier (V2) sits ON the real risk (an uncovered/undecided item
  classified `Covered`), with a HAND-DECLARED oracle independent of the code
  under test (spec 114/115 discipline) -- not mere ordering determinism.
- ASCII only, UTF-8 no BOM in every authored file; ASCII status strings
  (`Blocked -- missing field`, not the em-dash) (Principle IX / FR-015).
- NOTHING here is implemented in this slice: spec + plan + tasks only. No task is
  marked done; ratification is a human seam.
