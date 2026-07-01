# Tasks: Assumption Ledger Rule (AL1)

**Feature**: `053-assumption-ledger-rule-al1`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/rule-contract.md](./contracts/rule-contract.md)

TDD is the repo default (RED -> GREEN -> refactor). Test tasks precede the
implementation they cover. All paths are repo-relative.

Scope guard (YAGNI / first step): add ONE registered static rule
(`src/retail/rules/assumptions.py`) that keys on the EXISTING contract shape
(`readiness.status: blocked` + `blocking_reasons` as the marker; a filled
non-placeholder `binds_to` as the settled binding), the wiring-id update
(33 -> 34), the regenerated manifest, and a firing test. Scan only
`mappings/<table>/metrics/*.yaml` instances. Import `yaml` LAZILY (no module-scope
import). Modify NO committed metric contract, template, or readiness file. Add NO
new dependency, executor, or severity tier. Advance NO readiness stage, grant NO
approval, touch NO F016. The marker/binding conventions are resolved by advisor
ruling (spec ## Clarifications, Session 2026-07-01); their governance MEANINGS are
open_for_human for optional override -- build on the advisor default, do NOT wait.

## Phase 1: Setup

- [ ] T001 Confirm the reusable lazy-yaml contract-read pattern in
  `src/retail/metric_drift.py::load_definition()` (the in-function `import yaml`) and
  the sibling rules' selection/exemption pattern in `src/retail/rules/publish_pack.py`
  (suffix match over `ctx.tracked_files`, exact-path template exclusion,
  `is_test_path()` skip). Decide AL1's read seam per research.md R1 (recommended: a
  private in-function lazy `import yaml` + tolerant `read_text("utf-8-sig")`, reusing
  the PATTERN not the module). Record the rule id `AL1` in a top-of-module docstring.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 Read `tests/unit/test_rules_wiring.py` to confirm `EXPECTED_RULE_IDS` is a
  frozenset whose length drives the count (no literal baseline; currently 33 ids),
  and read `docs/rules/rules-manifest.json` + the `manifest` subcommand in
  `src/retail/cli.py` to confirm the `retail manifest --repo .` regeneration path
  before adding an id. Confirm the generic contract shape in
  `templates/metric-contract.yaml` (the `readiness.status`/`blocking_reasons` and
  `binds_to.gold_table`/`columns` field paths, and the `<...>` placeholder form) that
  the marker + settled-binding predicates key off.

## Phase 3: User Story 1 -- A still-open assumption blocks a bound metric (P1)

**Goal**: A `blocked` contract (non-empty `blocking_reasons`) that ALSO carries a
filled `binds_to` produces one ERROR Finding; an honest blocked-unbound draft, a
`pass`+bound contract, and an empty tree produce none.

**Independent test**: Invoke the rule against synthetic generic metric-contract
source strings (blocked+bound / blocked+unbound / pass+bound / empty) and assert
Findings / no Findings per contract C1/C2/C3/C5.

- [ ] T003 [US1] Add `tests/unit/test_assumptions.py` with RED tests asserting
  contract C1 (a `blocked` contract with non-empty `blocking_reasons` AND a filled
  non-placeholder `binds_to.gold_table` + non-empty `binds_to.columns` -> one ERROR
  Finding naming the contract path) and C3 (a `pass`+bound contract -> no Finding).
  Use synthetic GENERIC contract strings + a fake `RuleContext` (generic labels only,
  e.g. `mappings/demo_table/metrics/DemoMetric.yaml`; no C086/pharmacy artifact).
- [ ] T004 [US1] Extend `tests/unit/test_assumptions.py` with RED tests for C2 (a
  `blocked` contract whose `binds_to` is still the `<...>` placeholder / empty ->
  NO Finding: honest open draft), C5 (a `RuleContext` with no
  `mappings/*/metrics/*.yaml` -> no Finding), and C6 (a tracked-but-unparseable
  contract -> a fail-loud ERROR Finding). Confirm no assertion depends on AL1 writing
  any file (Principle-V read-only, contract C7).
- [ ] T005 [US1] Create `src/retail/rules/assumptions.py`: implement the read seam
  from T001 (private lazy `import yaml`; no module-scope yaml/DB/network import),
  define the marker predicate (`readiness.status == "blocked"` AND non-empty
  `blocking_reasons`) and the settled-binding predicate (a `binds_to.gold_table` with
  no `<...>` placeholder AND a non-empty `binds_to.columns` with at least one
  non-placeholder entry), and implement the `@register("AL1", ...)`ed checker that
  selects only tracked `mappings/*/metrics/*.yaml` (excluding
  `templates/metric-contract.yaml` and `is_test_path()` fixtures), and emits one
  `Severity.ERROR` Finding per contract where marker AND binding coexist, converting
  a read/parse error into a fail-loud Finding. AL1 writes nothing. Make T003/T004
  GREEN.
- [ ] T006 [US1] Run `pytest -m unit tests/unit/test_assumptions.py` and
  `retail check`; confirm tests pass and `retail check` reports zero new AL1 Findings
  on the current tree (the five committed contracts under
  `mappings/retail_store_sales/metrics/` are `status: pass` -> AL1 is green today,
  fires only on a blocked+bound contract -- a GENUINE pass, contract C1/C5).

## Phase 4: User Story 2 -- The rule is registered and drift-guarded (P1)

**Goal**: `AL1` is wired into the gate and the wiring test fails closed on drift.

- [ ] T007 [US2] Add `"AL1"` to `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py` (33 -> 34, AL1 the sole addition), with a short
  inline comment (e.g. `# AL1: assumption ledger -- blocked+bound contract`). Run
  `pytest -m unit tests/unit/test_rules_wiring.py`; confirm the registered id set
  equals `EXPECTED_RULE_IDS` and `len == 34`.
- [ ] T008 [US2] Regenerate the rule manifest: `retail manifest --repo .`; then run
  `pytest -m unit tests/unit/test_rules_manifest_snapshot.py` and confirm the snapshot
  includes AL1 and matches the live registry (contract C8).

## Phase 5: User Story 3 -- The rule stays generic and static (P2)

**Goal**: AL1 excludes the generic template, holds the B1/B3 import boundary, and
inlines no C086 specific.

- [ ] T009 [US3] Add a test (in `tests/unit/test_assumptions.py`) asserting contract
  C4: given the generic `templates/metric-contract.yaml` in the tracked set, AL1
  scans nothing there (it is excluded) -> no Finding; and a `tests/` fixture path is
  skipped via `is_test_path()`. Run `pytest -m unit tests/unit/test_assumptions.py`.
- [ ] T010 [US3] Run the full unit suite and the static gate:
  `pytest -m unit` and `retail check`. Confirm the B1/B3 import-boundary rules pass
  with `assumptions.py` present (no module-scope DB/network/yaml import), and grep the
  new module + any touched generic artifact for C086/pharmacy literals
  (dataset path, measure name, discount-status ruling) -- confirm none (contract
  C9/C10).

## Phase 6: Polish

- [ ] T011 Confirm every authored file is ASCII + UTF-8 without BOM (`--`, `->`, no
  glyphs; rule IX), the module docstring cites the resolved Clarifications
  (C1/C2/C3) and the Principle-V read-only boundary, and no numeric score/threshold
  appears anywhere (rule #9). Final `ruff check` + `pytest -m unit` + `retail check`
  all green.

## Dependencies / ordering

- T001, T002 (setup/foundational) precede all implementation.
- Phase 3 (T003 RED -> T005 GREEN -> T006 verify) is the core; T003/T004 before T005.
- Phase 4 (T007/T008) after the rule exists (the wiring test needs AL1 registered).
- Phase 5 (T009/T010) after the rule + wiring.
- T011 last.

## Out of scope (do NOT do)

- No new marker token in any file (the marker is the EXISTING `blocked` mechanism).
- No edit to any committed metric contract, template, or readiness state.
- No readiness-stage advance, approval grant, DAX evaluation, or DB/network connection.
- No gating on the unshipped T1.2 define-half (AL1 ships standalone, C3).
- No F016 / F031-F033 / live-runtime touch.
