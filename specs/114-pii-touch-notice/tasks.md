---
description: "Task list for Personal-Data-Touch Notice implementation"
---

# Tasks: Personal-Data-Touch Notice

**Input**: Design documents from `specs/114-pii-touch-notice/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED. The FR-011 verifier IS the feature's mechanical guarantee
(the reason this is a Python composer, not a skill), and the repo mandates TDD --
so test tasks are first-class, written before the code they verify.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)
- Paths are repo-relative; single-project layout (`src/retail`, `tests/unit`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: fixtures + module skeleton every story leans on.

- [x] T000 (ratify OPEN-2) Add the `deviation_ref` field to the source-map schema: document it in `templates/source-map.yaml` as a generic OPTIONAL column field (a kept-PII column names its governing deviation by exact `id`; Principle VII -- no C086 value baked in), and back-fill the worked-example fixture `mappings/retail_store_sales/source-map.yaml` so `customer_id` carries `deviation_ref: "RC4"`. Confirm `retail check` still exits 0 after the fixture edit.
- [x] T001 [P] Add PII-notice fixtures under `tests/unit/fixtures/pii_notice/`: `decided_kept/source-map.yaml` (a `pii:true, decision:keep` column with `deviation_ref: RC4` + the matching `defaults.deviations` disposition, modeled on retail_store_sales/customer_id), `decided_dropped/source-map.yaml` (a `pii:true, decision:drop` column with a drop `reason`), `undecided/source-map.yaml` (a `pii:true, decision:keep` column with NO `deviation_ref`), `mis_ref/source-map.yaml` (a kept-PII column whose `deviation_ref` points at RC-id X while a DIFFERENT deviation's prose mentions the column name -- proves join-by-ref-not-text, V7), `no_pii/source-map.yaml` (all `pii:false`), `inconsistent/source-map.yaml` (a `pii:true, decision:keep` column also present in drop signals). ASCII, UTF-8 no BOM.
- [x] T002 Create the composer module skeleton `src/retail/pii_notice.py` with the public signatures `build_pii_notice(repo_root, table) -> dict` and `render_markdown(notice) -> str` (bodies raise `NotImplementedError`), plus a private `_load_yaml_mapping(path)` copied from the `blocker_explainer.py` idiom (utf-8-sig read; None on OSError/UnicodeDecodeError/YAMLError). No DB/driver import at module load.

**Checkpoint**: schema+fixture carry `deviation_ref`; fixtures exist; module imports; `retail check` exit 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared verifier + resolution logic every story's tests use.

CRITICAL: no user-story test can assert faithfulness until the verifier exists.

- [x] T003 [US-shared] Write the reusable verifier helper `assert_notice_is_faithful(notice_text, source_map)` in `tests/unit/test_pii_notice.py` implementing V1 verbatim-substring, V2 completeness/never-omit, V3 never-clear (closed clearance denylist), V4 no-score, and V7 join-correctness (rendered-disposition-deviation-id == the column's `deviation_ref`; the `mis_ref` fixture proves join-by-ref-not-text; a no-`deviation_ref` kept-PII column renders GAP) per contracts/verifier.md. TEST helper only -- NO `@register` rule, NO manifest change (FR-007).
- [x] T004 Implement the disposition-resolution core in `src/retail/pii_notice.py`: enumerate `columns[]` where `pii is True`; for each, resolve `state` + `disposition` + `disposition_source` per data-model.md (drop -> own `reason`; keep -> the `reason` of the deviation whose `id` EXACTLY matches the column's `deviation_ref`; no/unmatched `deviation_ref` -> `undecided`; intra-file contradiction -> `inconsistent`). NEVER text-match column names in deviation prose. Return the PiiNotice dict incl. `no_pii`, `document_gap`, `read_only_proof: True`. `render_markdown` still stubbed.

**Checkpoint**: `build_pii_notice` returns a correct model for all fixtures; verifier helper importable.

---

## Phase 3: User Story 1 - Decided PII columns disclosed verbatim (Priority: P1) -- MVP

**Goal**: one verbatim disclosure sentence per DECIDED `pii:true` column (kept or dropped), citing its in-file locus.

**Independent Test**: run against the `decided_kept` fixture -> exactly one decided-kept line quoting the RC4 disposition verbatim, no GAP, no score.

### Tests for User Story 1 (write first, must FAIL)

- [x] T005 [P] [US1] In `tests/unit/test_pii_notice.py`, add `test_decided_kept_verbatim` and `test_decided_dropped_verbatim`: compose the notice for each fixture and run `assert_notice_is_faithful`; assert the decided line quotes the disposition character-for-character and cites the source locus (SC-002). Assert FAIL before T006.

### Implementation for User Story 1

- [x] T006 [US1] Implement `render_markdown` in `src/retail/pii_notice.py` for the DECIDED cases per contracts/composer.md: the header + read-only disclaimer, and one quoted, locus-cited disclosure line per decided_kept / decided_dropped finding. ASCII `--`/`->`, no glyphs, no numeric token.
- [x] T007 [US1] Add the CLI verb `src/retail/cli/commands/pii_notice.py` (`retail pii-notice --table <t> [--format text|json] [--write]`) mirroring `commands/blockers.py`; `--write` writes ONLY `mappings/<table>/pii-touch-notice.md`; always returns exit 0 (FR-007).
- [x] T008 [US1] Register + dispatch the `pii-notice` subcommand in `src/retail/cli/parser.py` and the CLI dispatch table (`src/retail/cli/__init__.py`), following the shipped `blockers`/`next` wiring.

**Checkpoint**: MVP -- `retail pii-notice --table retail_store_sales` prints the verbatim customer_id disclosure; US1 tests green.

---

## Phase 4: User Story 2 - Undecided PII column is an explicit GAP (Priority: P1)

**Goal**: a `pii:true` column with no recorded disposition renders as a GAP that reads "NOT cleared" -- never omitted, never implied clearance. (Safety-critical.)

**Independent Test**: run against the `undecided` fixture -> the column appears as one GAP line with "NOT cleared" framing and no clearance token.

### Tests for User Story 2 (write first, must FAIL)

- [x] T009 [P] [US2] In `tests/unit/test_pii_notice.py`, add `test_undecided_renders_gap_not_clearance`: assert the undecided column is PRESENT (V2 never-omit), rendered as a GAP with the "NOT cleared" framing, and contains no clearance-denylist token (V3); assert `assert_notice_is_faithful` passes. Assert FAIL before T010.

### Implementation for User Story 2

- [x] T010 [US2] Extend `render_markdown` for the `undecided` state: a `## Gaps` section line `GAP: <column> -- pii:true with NO recorded governance disposition (checked: ...). This column is NOT cleared; a named human decision is not recorded.` No clearance wording anywhere the composer authors.

**Checkpoint**: undecided PII never masquerades as cleared; US1 + US2 green.

---

## Phase 5: User Story 3 - Missing/unreadable input is surfaced, not fabricated (Priority: P2)

**Goal**: a missing/unreadable `source-map.yaml` (or absent `columns` block) yields one document-level GAP, never an empty "no PII" notice; an all-`pii:false` table states plainly no PII is flagged.

**Independent Test**: point at a table dir with no `source-map.yaml` -> one document-level GAP naming the path; run against `no_pii` -> the explicit no-PII statement.

### Tests for User Story 3 (write first, must FAIL)

- [x] T011 [P] [US3] In `tests/unit/test_pii_notice.py`, add `test_missing_source_map_document_gap`, `test_no_pii_statement`, and `test_inconsistent_gaps_both_loci` (FR-010). Assert FAIL before T012.

### Implementation for User Story 3

- [x] T012 [US3] Extend `build_pii_notice`/`render_markdown` for `document_gap` (missing/unreadable/columns-absent -> one document-level GAP), the `no_pii` statement, and the `inconsistent` state (GAP naming both in-file loci). No fabricated findings.

**Checkpoint**: all three stories independently functional; every fixture covered.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T013 [P] Add the generic output template `templates/handoff/pii-touch-notice.md` (copy-me shape, Principle VII; no C086 column names baked in), companion to `answerability-summary.md`.
- [x] T014 [P] Add the tool doc `docs/tools/pii-touch-notice.md` mirroring `docs/tools/blocker-explainer.md` (what it is, run, the scope wall, what it will NOT do).
- [x] T015 [P] [US-shared] Add the read-only proof test (V5, SC-005): run `--write` against a temp copy of a table dir; assert only `pii-touch-notice.md` changed and `build_pii_notice` triggers no DB/network import.
- [x] T016 [P] [US-shared] Add the generic proof test (V6, SC-006): run the SAME composer over `retail_store_sales` and a second fixture table with no per-table branch.
- [x] T017 Run `quickstart.md` end-to-end against `retail_store_sales`; confirm the customer_id verbatim disclosure and zero GAP/score. Run `ruff format --check src tests` + `ruff check src tests` + `pytest tests/unit/test_pii_notice.py -q`; confirm `retail check` still exits 0 and the rules manifest count is UNCHANGED (proves no gate was added, FR-007).

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> User Stories (3-5) -> Polish (6).
- Phase 2 BLOCKS all stories (the verifier + resolution core are shared).

### Story dependencies

- US1 (P1): after Phase 2. The MVP.
- US2 (P1): after Phase 2; extends `render_markdown` (shares T006's function, so
  sequence T006 -> T010 to avoid a same-file conflict).
- US3 (P2): after Phase 2; extends `build_pii_notice`/`render_markdown`
  (sequence after T006/T010 for the same reason).

### Within each story

- Test first (must FAIL) -> implementation -> checkpoint.
- Resolution core (T004) before any render (T006/T010/T012).

### Parallel opportunities

- T001 fixtures are [P] with T003 verifier helper authoring.
- The per-story TEST tasks (T005, T009, T011) are [P] with each other (distinct
  test functions), but each precedes its own implementation task.
- Polish tasks T013/T014/T015/T016 are [P] (distinct files); T017 is the final
  serial gate.
- NOTE: T006, T010, T012 all edit `render_markdown` in one file -> NOT parallel;
  run in story-priority order.

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational -> Phase 3 US1.
2. STOP and validate: `retail pii-notice --table retail_store_sales` shows the
   verbatim customer_id disclosure; US1 tests green.

### Incremental delivery

- +US2 (undecided GAP, the safety half) -> +US3 (input-absence robustness) ->
  Polish (template, doc, read-only + generic proofs, full gate run).

---

## Notes

- [P] = different files, no incomplete-task dependency.
- The verifier (T003) is TEST-only -- no `@register` rule, no manifest change
  (FR-007 forbids a gate).
- ASCII only, UTF-8 no BOM in every authored file (Principle IX).
- Commit after each task or logical group; each checkpoint is independently
  testable.
