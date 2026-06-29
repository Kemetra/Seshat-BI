# Tasks: Rule Registry Snapshot Manifest (golden-file rule inventory)

**Input**: Design documents from `specs/043-rule-registry-snapshot-manifest-golden/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This feature IS a test (a golden-equality snapshot test) plus a generator. The
snapshot test is authored TEST-FIRST (it fails closed before the manifest is committed, passes
after). The generator is verified by determinism/idempotency assertions. No DB/network/Power BI.

**Organization**: Tasks are grouped by user story (US1 = drift guard, US2 = regeneration,
US3 = documented-count cleanup). The over-scope guard is load-bearing: NO new `@register`, NO new
`EXPECTED_RULE_ID`; the snapshot test is test-only, NOT a `retail check` rule.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included.

## Path Conventions

Single project. New code under `src/retail/` (CLI subcommand) and `tests/unit/`. The generated
artifact is `docs/rules/rules-manifest.json`. One `.gitattributes` line; two corrected lines in
`.specify/memory/constitution.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the source-of-truth seams and the home of the new artifact before authoring.

- [ ] T001 Confirm `registry.all_rules()` returns `tuple[RegisteredRule, ...]` with exactly
  `id` + `title` serializable fields (`rule` is a callable, not serialized), by reading
  `src/retail/registry.py` and `src/retail/core.py` (read-only).
- [ ] T002 Confirm the live registry count equals `len(EXPECTED_RULE_IDS)` (currently 33, in
  agreement) by reading `tests/unit/test_rules_wiring.py` -- the generator must read the live
  count, never bake a literal. (read-only; no change here)
- [ ] T003 Create the new `docs/rules/` directory home for the manifest (directory does not exist
  yet). No content yet.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The deterministic serialization contract that BOTH the generator and the snapshot
test depend on. Must land before either consumer.

- [ ] T004 Decide and document the single deterministic ordering (sort entries by `id`) and the
  serialization contract: list of `{"id", "title"}`, UTF-8 no-BOM, `\n` line endings, single
  trailing newline, stable key order within each entry. Record it as a module docstring on the
  generator. (Principle IX) [FR-003]
- [ ] T005 Add `.gitattributes` entry: `docs/rules/rules-manifest.json text eol=lf` so the
  committed bytes are stable across Windows (`core.autocrlf=true`) and Linux. [FR-010]

---

## Phase 3: User Story 1 -- Drift guard (Priority: P1)

**Goal**: A golden-equality snapshot test that fails closed when the committed manifest diverges
from the live registry. **Independent test**: mutate a title in code without regenerating ->
test fails with actionable message; regenerate -> passes.

- [ ] T006 [US1] Author `tests/unit/test_rules_manifest_snapshot.py` (marked
  `@pytest.mark.unit`) TEST-FIRST: it derives the expected manifest data from the live
  `all_rules()` (importing `retail.rules` for the registration side effect), reads the committed
  `docs/rules/rules-manifest.json` as UTF-8, normalizes line endings, parses JSON, and asserts
  equality. At this point the file does not exist yet -> the test fails closed (RED). [FR-004, FR-005]
- [ ] T007 [US1] Make the failure message actionable: on mismatch, report drifted/missing/
  unexpected ids (and changed titles) and instruct the developer to regenerate with the
  generator and commit the manifest in the same change. [FR-006]
- [ ] T008 [US1] Assert (in the same test module or `test_rules_wiring.py` neighborhood, read-only
  on wiring) that this work added NO new `EXPECTED_RULE_ID` and registered NO new rule -- the
  snapshot test is test-only, not a `retail check` rule. [FR-007, SC-004]

---

## Phase 4: User Story 2 -- Regeneration generator (Priority: P2)

**Goal**: A one-command generator that writes the manifest deterministically from the live
registry. **Independent test**: run twice -> byte-identical; run when already in sync -> no diff.

- [ ] T009 [US2] Implement the generator function in `src/retail/` that takes `all_rules()` and
  returns the ordered manifest data (list of `{"id", "title"}` sorted by `id`), plus a serializer
  that writes UTF-8 no-BOM, `\n`, trailing newline to `docs/rules/rules-manifest.json`. Generated
  from the live registry, never a hand-typed literal. [FR-001, FR-002, FR-003, FR-008]
- [ ] T010 [US2] Wire the generator behind a `retail manifest` CLI subcommand in
  `src/retail/cli.py` (reusing the already-imported `all_rules()` and the `sub.add_parser(...)`
  seam; the `gen` DAX subcommand is the placement precedent). No `--check` mode (YAGNI). [FR-001]
- [ ] T011 [US2] Run the generator to PRODUCE the committed `docs/rules/rules-manifest.json`; the
  snapshot test from Phase 3 now passes (GREEN). [US1 + US2 join here]
- [ ] T012 [US2] Add a determinism/idempotency unit assertion: generating twice yields
  byte-identical output, and generating when already in sync produces no diff. [SC-002]

---

## Phase 5: User Story 3 -- Documented-count cleanup (Priority: P3)

**Goal**: Retire the stale hand-typed count in the live constitution body and cite the manifest.

- [ ] T013 [US3] Correct the stale "26 rules" text on `.specify/memory/constitution.md` lines
  377 + 381 ONLY -- update to match the live registry and reference the generated manifest as the
  source of truth. Leave historical Sync-Impact-comment occurrences of older counts UNCHANGED. [FR-009]
- [ ] T014 [P] [US3] Update count references in `docs/glossary.md` (line 100, already 33) and
  `docs/roadmap/roadmap.md` to cite/link the manifest as the source of truth (no count drift). [SC-003]

---

## Phase 6: Verification

**Purpose**: Confirm the gate is unchanged and the feature is cross-platform stable.

- [ ] T015 Run `retail check` -> exit 0 and confirm the registered rule count is UNCHANGED
  (no new rule, no new `EXPECTED_RULE_ID`). [SC-004]
- [ ] T016 Run `pytest -m unit` -> the snapshot test passes on a clean checkout; confirm no
  line-ending flakiness (simulate a CRLF checkout / verify normalization). [SC-001, SC-005]

---

## Dependencies

- Phase 2 (T004 serialization contract) blocks Phase 3 and Phase 4.
- Phase 3 (T006 snapshot test) is authored RED before Phase 4 produces the manifest (T011 turns
  it GREEN). This is the test-first ordering.
- Phase 5 is independent of the code path and can proceed once US1 confirms the manifest exists.
- T014 is `[P]` with T013 (different files).

## Out of Scope (YAGNI)

- No new `@register` rule; no new `EXPECTED_RULE_ID`; no change to `retail check` behavior.
- No `retail manifest --check` CI mode (the snapshot test covers drift).
- No severity/family/count fields. No rewrite of historical constitution comments.
- No DB/network/Power BI; no dependency on F016 or F031-F033.
