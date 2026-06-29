# Implementation Plan: Text/JSON Output Equivalence Property Test

**Branch**: `045-output-parity` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/045-output-parity/spec.md`

## Summary

Add a stdlib-only, test-only property test (`tests/unit/test_runner_output_parity.py`, greenfield)
that proves the two `retail check` output paths agree. For shared SYNTHETIC `RegisteredRule`
fixtures it asserts (a) the order-insensitive multiset (`collections.Counter`) of
`(rule_id, severity, message, locator)` tuples reconstructed from `run()`'s text stdout equals the
multiset from `run_json()`'s JSON `findings` array, and (b) `run()` and `run_json()` return the
IDENTICAL exit code (1 iff any ERROR present, else 0). Today the two SEPARATE code paths
(`run()` iterates rules inline and prints `_format` lines; `run_json()` routes through `_collect`
-> `_exit_code` -> `json.dumps`) are kept in agreement only by a docstring convention about rule
purity; this converts that convention into a tested invariant. It adds NO new registered rule and
NO new `EXPECTED_RULE_ID`, modifies NO production code (`src/retail/runner.py`, `src/retail/core.py`
are untouched), and is C086-agnostic. It is meta-infrastructure that hardens the existing static
gate; it advances no readiness stage.

## Technical Context

**Language/Version**: Python 3.13 (repo interpreter; CI runs 3.13, local may be 3.12). Stdlib-only
for this feature (`collections.Counter`, `json`, `re` or simple string parsing, `pathlib`).

**Primary Dependencies**: NONE new. Reads `retail.core` (`Finding`, `RegisteredRule`, `RuleContext`,
`Severity`) and `retail.runner` (`run`, `run_json`). Test uses `pytest` + the `capsys` fixture
(both already in the repo). MUST NOT import `retail.rules` or `psycopg2`.

**Storage**: None. The test builds in-memory synthetic findings; it reads stdout via `capsys`.

**Testing**: `pytest` unit test, marked `@pytest.mark.unit`, mirroring `tests/unit/test_runner.py`.

**Target Platform**: CI + local dev on Windows (`core.autocrlf=true`) and Linux. The test compares
in-memory structures and captured stdout; line-ending normalization on the text split keeps it
cross-platform stable.

**Project Type**: Single project (existing `src/retail` + `tests/unit`). This feature adds exactly
one file under `tests/unit/`.

**Performance Goals**: N/A -- a handful of synthetic findings; runs in milliseconds.

**Constraints**: stdlib-only; no DB/network/Power BI dependency; reads but never modifies
`run()`/`run_json()` output (B2 byte-for-byte text contract); treats `Finding` as immutable
(frozen dataclass) and compares via a freshly built `Counter`, never by in-place re-sort;
generic-only fixtures (Principle VII).

**Scale/Scope**: One new test file. No production change, no new rule, no new `EXPECTED_RULE_ID`,
no `.gitattributes` change (the test reads no committed text artifact). No more.

## Constitution Check

*GATE: Must pass before implementation.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS. The exit code IS the contract; this test
  hardens the guarantee that the text and JSON paths agree on that exit code, reinforcing (never
  weakening) the non-zero-exit gate. It adds NO new `EXPECTED_RULE_ID` and is not itself a `retail
  check` rule -- it is a pytest assertion sitting beside the runner, not inside the gate.
- **Principle V (Agent Stops at Judgment Calls)**: PASS. No grain/PII/rollup/identity decision is
  embedded; the one Principle-V item (roadmap promotion) is reserved for the owner in the spec's
  Clarifications block and is NOT answered here.
- **Principle VII (C086 Is An Example)**: PASS. Fixtures use only generic placeholder ids/messages/
  locators; no billing codes, insurance/PII columns, or pharmacy rule ids flow in.
- **Principle VIII (Static-First Governance)**: PASS. The test is stdlib-only, CI-able, with no
  DB/network/Power BI dependency; it executes synthetic in-memory rules and reads stdout. It does
  NOT import `retail.rules` (it does not need the real registry) and does NOT import `psycopg2`.
- **Principle IX (Secrets & Reproducibility / Windows-safe text)**: PASS. No secrets. The text
  reconstruction splits on line boundaries and ignores a trailing blank line, so a trailing newline
  or CRLF round-trip does not produce a spurious empty finding. No committed text artifact is read,
  so there is no on-disk byte-stability concern for this feature.
- **Hard rule #7 (generic only)**: PASS. Synthetic, generic fixtures only.
- **Hard rule #9 (no fabricated confidence/score)**: PASS. The test asserts an exact equivalence
  (Counter equality + exit-code equality); it emits no numeric confidence/health score.
- **Coding-style / immutability**: PASS. `Finding` is treated as immutable; the order-insensitive
  comparison is a freshly constructed `Counter`, not an in-place mutation or re-sort.

No violations -> Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/045-output-parity/
  spec.md          # Stage 2 output (specify)
  plan.md          # This file (stage 4 output)
  tasks.md         # Stage 4 output (tasks)
  analysis.md      # Stage 5 output (analyze report; repo convention)
  plan-review.md   # Stage 6 output (adversarial plan-review)
  checklists/
    requirements.md   # Stage 2 quality checklist
```

No `research.md` / `data-model.md` / `quickstart.md` / `contracts/` are produced: this feature is a
single self-contained unit test over confirmed in-process seams; there is nothing to research, no
new data model, and no external contract.

### Source Code (repository root)

```text
src/retail/
  core.py          # READ-ONLY: Finding, Finding.to_dict, FindingDict, Severity, RegisteredRule, RuleContext
  runner.py        # READ-ONLY: run, run_json, _collect, _format, _exit_code (the dual paths under test)

tests/unit/
  test_runner.py                    # READ-ONLY sibling: the capsys + synthetic-RegisteredRule pattern this mirrors
  test_rules_wiring.py              # READ-ONLY: EXPECTED_RULE_IDS must stay unchanged (over-scope guard)
  test_runner_output_parity.py      # NEW: the parity property test (the only file this feature creates)
```

**Structure Decision**: Single project. The feature adds exactly one file,
`tests/unit/test_runner_output_parity.py`, beside the existing `tests/unit/test_runner.py`. No
production source changes; `src/retail/runner.py` and `src/retail/core.py` are read-only references.

## Complexity Tracking

> No Constitution Check violations -- this section intentionally left empty.
