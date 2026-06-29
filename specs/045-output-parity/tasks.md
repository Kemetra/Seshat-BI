# Tasks: Text/JSON Output Equivalence Property Test

**Input**: Design documents from `specs/045-output-parity/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This feature IS a test (a property test over the two output paths). It is authored
TEST-FIRST in the sense that the assertions encode the invariant directly; there is no separate
implementation to write because the production code under test (`run`/`run_json`) already exists
and is NOT modified. No DB/network/Power BI.

**Organization**: Tasks are grouped by user story (US1 = findings-multiset parity, US2 = exit-code
parity, US3 = generic/no-gate-change guardrails). The over-scope guard is load-bearing: NO new
`@register`, NO new `EXPECTED_RULE_ID`, NO change to `src/retail/runner.py` or `src/retail/core.py`;
the parity test is test-only, NOT a `retail check` rule.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included.

## Path Conventions

Single project. The ONLY new file is `tests/unit/test_runner_output_parity.py`. Read-only
references: `src/retail/runner.py`, `src/retail/core.py`, `tests/unit/test_runner.py`,
`tests/unit/test_rules_wiring.py`.

---

## Phase 1: Setup (Confirm Seams)

**Purpose**: Confirm the load-bearing seams and the mirrored test pattern before authoring.

- [ ] T001 Confirm the dual output paths in `src/retail/runner.py` (read-only): `run()` iterates
  rules inline and prints `_format(finding)` per line (lines 84-98); `run_json()` routes through
  `_collect` -> `_exit_code` -> `json.dumps({"findings":[...], "exit_code":N}, indent=2)` (lines
  101-117). Note the stable text shape `"[{severity.value}] {rule_id} {message} ({locator})"`
  (`_format`, lines 61-65) -- this is the format the inverse reconstruction reads.
- [ ] T002 Confirm `Finding.to_dict()` / `FindingDict` pin exactly the four fields `rule_id`,
  `severity` (as `.value`), `message`, `locator` in `src/retail/core.py` (read-only) -- the
  equivalence key.
- [ ] T003 Confirm the mirrored pattern in `tests/unit/test_runner.py` (read-only): synthetic
  `RegisteredRule(id=..., rule=fn, title=...)` fixtures + `capsys` stdout capture + a local
  `_ctx()` helper returning `RuleContext(repo_root=Path("."), tracked_files=())`. Reuse this shape.

---

## Phase 2: US1 -- Findings-multiset parity (Priority: P1)

**Goal**: Prove the text and JSON paths agree on the multiset of findings.

- [ ] T004 [US1] Create `tests/unit/test_runner_output_parity.py` with module imports limited to
  stdlib (`collections.Counter`, `json`) + `retail.core` (`Finding`, `RegisteredRule`,
  `RuleContext`, `Severity`) + `retail.runner` (`run`, `run_json`). MUST NOT import `retail.rules`
  or `psycopg2`. Add a `_ctx()` helper mirroring `test_runner.py`.
- [ ] T005 [US1] Add a shared fixture builder returning a tuple of SYNTHETIC `RegisteredRule` stubs
  whose rules yield generic findings covering EVERY severity (ERROR, WARNING, INFO) AND at least
  one rule yielding MULTIPLE findings. Ids/messages/locators MUST be generic placeholders (e.g.
  `R1`, `R2`, `"first message"`, `"a.txt:1"`) -- NO C086/pharmacy specifics, and NO message/locator
  containing `") ("` or unescaped brackets (so the inverse parse is unambiguous; FR-006).
- [ ] T006 [US1] Add a `_parse_text_findings(text)` helper that splits captured stdout on line
  boundaries, ignores a trailing blank line, and reconstructs each line into a
  `(rule_id, severity, message, locator)` tuple by inverting the
  `"[{sev}] {rule_id} {message} ({locator})"` format. Build a `Counter` of those tuples. (Relies on
  the fixture constraint from T005; does NOT attempt to be robust against adversarial free text.)
- [ ] T007 [US1] Add a `_json_findings_counter(out)` helper that `json.loads` the captured JSON,
  reads the `findings` array, and builds a `Counter` of `(rule_id, severity, message, locator)`
  tuples from each entry's four fields.
- [ ] T008 [US1] Add `test_text_and_json_findings_multisets_match(capsys)`: run `run(rules, ctx)`,
  drain stdout, build the text Counter; run `run_json(rules, ctx)`, build the JSON Counter; assert
  the two Counters are EQUAL. Treats `Finding` as immutable -- no in-place sort/mutation.
- [ ] T009 [US1] Add `test_findings_parity_empty_rule_set(capsys)`: with a rule set that yields no
  findings, both paths produce an empty Counter and they are equal (trivial-but-explicit case).

---

## Phase 3: US2 -- Exit-code parity (Priority: P1)

**Goal**: Prove the text and JSON paths return the identical exit code.

- [ ] T010 [US2] Add `test_text_and_json_exit_codes_match` parametrized over fixture sets:
  (a) at least one ERROR present -> both return 1; (b) WARNING/INFO only -> both return 0;
  (c) empty -> both return 0. For each, assert `run(rules, ctx) == run_json(rules, ctx)` and that
  the value matches gate semantics (1 iff any `Severity.ERROR`). Use `capsys` to drain stdout
  between the two calls so output does not bleed across assertions.

---

## Phase 4: US3 -- Generic / no-gate-change guardrails (Priority: P2)

**Goal**: Confirm the test stays test-only, generic-only, and changes no production surface.

- [ ] T011 [P] [US3] Self-review the new test file: imports are stdlib + `retail.core` +
  `retail.runner` ONLY (no `retail.rules`, no `psycopg2`, no network); fixtures contain no
  C086/pharmacy ids, billing codes, insurance/PII columns, or worked-example locators (FR-011).
- [ ] T012 [P] [US3] Verify `tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS` is UNCHANGED and
  `src/retail/runner.py` / `src/retail/core.py` are byte-for-byte unchanged after this work
  (over-scope guard FR-008/FR-009; `git diff` shows only the one new test file).

---

## Phase 5: Verification

- [ ] T013 Run `pytest tests/unit/test_runner_output_parity.py -q` -> all green. Run twice ->
  deterministic (no flakiness; SC-002).
- [ ] T014 Run the full `tests/unit` suite -> still green (the new file adds no regression and does
  not alter the runner; SC-003).
- [ ] T015 Confirm the new file is ASCII, UTF-8 without BOM, and the only changed production-tree
  artifact (SC-003/SC-004).

---

## Dependencies

- T001-T003 (setup, read-only) precede authoring.
- T004 precedes T005-T010 (same file).
- T005 precedes T006-T010 (fixtures feed every assertion).
- T008/T009 (US1) and T010 (US2) are independent assertions within the same file and may be written
  in any order after T005-T007.
- T011-T012 (US3 guardrails) and T013-T015 (verification) run last.

## Out of Scope (YAGNI)

- A real-registry tmp-repo fixture driving `all_rules()` through `run()` (Q1: synthetic only).
- A general-purpose robust inverse-of-`_format` parser handling adversarial messages (Q2: fixtures
  are constrained to be unambiguous instead).
- Any change to `run()`/`run_json()`/`_format` output or signatures (B2 text contract preserved).
- Any new registered rule, `EXPECTED_RULE_ID`, or `retail check` surface change.
- Any DB/network/Power BI/executor wiring (Principle VIII; F016/F031-F033 not assumed).
