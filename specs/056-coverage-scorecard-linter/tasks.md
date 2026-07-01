# Tasks: Coverage Scorecard Linter (SL1)

**Feature**: `056-coverage-scorecard-linter`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/rule-contract.md](./contracts/rule-contract.md)

TDD is the repo default (RED -> GREEN -> refactor). Test tasks precede the
implementation they cover. All paths are repo-relative.

Scope guard (YAGNI / first step): add ONE registered static rule modeled on PP1
(`src/retail/rules/publish_pack.py`), the wiring-id update, the regenerated manifest,
and a firing test. Scan only `mappings/<table>/**/*coverage-scorecard.md` instances;
EXCLUDE the explicit template path and `tests/` fixtures. Modify NO committed
scorecard, template, or readiness file. Add NO new dependency, executor, or severity
tier. The registry id (`SL1`) and the severity posture are RECOMMENDATIONS pending
human ratification (spec ## Clarifications) -- use the working id `SL1` and leave a
note; do NOT invent a readiness stage; do NOT populate or adjudicate any coverage
status.

## Phase 1: Setup

- [ ] T001 Read `src/retail/rules/publish_pack.py` (PP1) to confirm the shape to
  mirror: `ctx.tracked_files` iteration, explicit-path + `is_test_path()` exclusion,
  section-anchored positional table parse with non-greedy `[^|]*` middle cells,
  `encoding="utf-8-sig"` read, fail-loud-on-`OSError`, ERROR-only Findings, and the
  "slot present, never grant" Principle-V module-docstring posture. Record the working
  rule id `SL1` (pending ratification per spec ## Clarifications) in a top-of-module
  comment. Decide the reuse seam per research.md R1 (recommended: local rule-specific
  patterns, no shared-helper extraction).

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 Read `skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`
  to confirm the closed five-value status enum, the four-column header
  `| KPI | Contract | Coverage status | Blocker ... |`, the `> Table:` title anchor,
  and the em-dash `--` placeholder + `contracts/<file>.md` contract-cell form. Read
  `tests/unit/test_rules_wiring.py` to confirm `EXPECTED_RULE_IDS` is a frozenset whose
  length drives the snapshot count (live baseline 38 ids; no literal count), and
  confirm the `manifest` subcommand in `src/retail/cli.py` regenerates
  `docs/rules/rules-manifest.json`. Note the dash-normalization requirement (en-dash /
  em-dash / `--` all parse) per research.md R2.

## Phase 3: User Story 1 -- Catch a malformed filled scorecard (P1)

**Goal**: A bad enum, a missing blocker, an unresolved Covered contract, or a
percentage token each produces a Finding; a well-formed scorecard does not.

**Independent test**: Invoke the rule against synthetic generic scorecard strings +
a fake `RuleContext` and assert Findings / no Findings per contract C1-C5.

- [ ] T003 [US1] Add `tests/unit/test_scorecard.py` with RED tests asserting contract
  C1 (status outside the enum -> one Finding naming file+row) and C5 (a fully
  well-formed generic scorecard -> no Finding). Use synthetic generic scorecard
  strings + a fake `RuleContext` (generic labels only; no domain artifact).
- [ ] T004 [US1] Extend `tests/unit/test_scorecard.py` with RED tests for C2 (a
  `Blocked -- ...` row with empty / bare-`--` blocker -> one Finding), C3 (a `Covered`
  row citing a non-resolving `contracts/<file>.md` -> one Finding), C3b (a `Planned` /
  `Out of scope` row with `--` contract -> no Finding), C4 (a number-then-`%` token ->
  one Finding), and C4b (a `%` inside a KPI name with no adjacent digit -> no Finding).
- [ ] T005 [US1] Create `src/retail/rules/scorecard.py` modeled on PP1: define the
  closed status-enum constant (the five generic statuses -- recommended membership,
  comment that final membership is confirmed at ratify), the local regex patterns
  (four-column header/row, `> Table:` anchor, `contracts/<file>.md`, number-then-`%`),
  and the `@register("SL1", ...)`ed checker that selects only tracked
  `mappings/**/*coverage-scorecard.md` (excluding the explicit template path and
  `is_test_path()` fixtures), reads each instance's text, and emits a `Severity.ERROR`
  Finding for each: status outside the enum (C1), Blocked-- row with no named blocker
  (C2), Covered row with a non-resolving contract path (C3), or a number-then-`%`
  token (C4). Apply dash normalization before enum comparison. Make T003/T004 GREEN.
- [ ] T006 [US1] Run `pytest -m unit tests/unit/test_scorecard.py` and `retail check`;
  confirm tests pass and `retail check` reports zero new Findings on the current tree
  (no filled scorecard instance is committed -> the rule silent-passes by absence,
  contract C7).

## Phase 4: User Story 2 -- Pass a well-formed scorecard, never fire on the template (P1)

**Goal**: The generic template (and its illustrative worked example) is never scanned;
committed `tests/` fixtures are never scanned.

**Independent test**: Run the rule against the real template path and a `tests/`
fixture path -> zero Findings.

- [ ] T007 [US2] Add RED/GREEN tests to `tests/unit/test_scorecard.py` for C6 (the
  explicit template path -> no Finding; a `tests/` fixture path -> no Finding) and C9
  (a stray four-column table outside the anchored status table contributes no rows).
  Extend the T005 exclusion / anchoring if not already covered. Add C8 (an unreadable
  selected instance -> a fail-loud ERROR Finding).

## Phase 5: User Story 3 -- Genuinely wired, not just listed (P2)

**Goal**: The id is in the registry, the regenerated manifest, and the wiring expected
set, AND the rule is exercised firing (close the wiring-latent-gap).

**Independent test**: The snapshot/wiring test passes with the new id; a direct test
observes the rule fire on a known-bad fixture.

- [ ] T008 [US3] Add the working id `SL1` to `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py` (with a one-line comment), keeping the set the
  single source of truth; do NOT introduce any literal baseline count.
- [ ] T009 [US3] Regenerate `docs/rules/rules-manifest.json` via
  `retail manifest --repo .` so it contains the new id; verify it is the only intended
  diff.
- [ ] T010 [US3] Run `pytest -m unit tests/unit/test_rules_wiring.py`; confirm the live
  registry id set equals `EXPECTED_RULE_IDS`, `len(all_rules()) ==
  len(EXPECTED_RULE_IDS)`, and the rule submodule is auto-discovered by `pkgutil`.
- [ ] T011 [US3] Confirm `tests/unit/test_scorecard.py` includes at least one test that
  invokes the rule directly on a known-bad fixture and asserts a non-empty Finding set
  (the rule FIRES, not merely registers -- SC-006, contract C11); add it if not already
  covered by T003/T004.

## Phase 6: Polish & Cross-Cutting

- [ ] T012 [P] Add a test/inspection note for C10/C12: no code path adjudicates
  coverage truth, grants a readiness stage, or writes a status (Principle V); and the
  rule, its enum constant, and every fixture contain only generic labels -- no table /
  column / KPI name, and no inlined worked-example answers.
- [ ] T013 [P] Run `ruff` and the full `pytest -m unit` suite; confirm ASCII / UTF-8 no
  BOM (`--` / `->`, no glyphs) in all new files and that no new third-party dependency,
  network call, or DB access was introduced (SC-008, contract C14).
- [ ] T014 [P] Confirm the spec's Open-for-human items (the roadmap-stage placement and
  the Principle-V structure-only boundary confirmation) and the reversible advisor
  recommendations (working id `SL1`, severity = ERROR) remain recorded and
  unanswered/unconfirmed; do NOT self-assign a readiness stage, a ratified id, or
  self-grant any approval.

## Dependencies

- T001, T002 (Setup/Foundational) before all story phases.
- US1 (T003-T006) is the MVP; US2 (T007) depends on the rule existing (T005). US3
  (T008-T011) depends on the rule existing (T005).
- T003/T004 (RED) before T005 (GREEN). T008/T009 before T010.
- Polish (T012-T014) last.

## Parallel opportunities

- T012, T013, T014 are independent ([P]).
- Within US1, T003 and T004 edit the same test file -> run sequentially.

## MVP scope

User Story 1 (T001-T006) alone delivers the protective value: a malformed committed
coverage scorecard fails the gate. US2 (template/fixture exclusion + anchoring +
fail-loud) and US3 (wiring integrity + firing) harden false-positive resistance,
safety, and registry symmetry.
