# DAX Fortification — Phase 1 (L3 widen + gate) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Widen the L3 contract↔DAX drift checker to recognize 4 more predicate spellings and guard additive measures, then promote it to a CI gate via a new `retail semantic-check` subcommand (drift=ERROR, escalate=WARNING) — without polluting the stdlib-only `retail check` core.

**Architecture:** L3 lives in the lazy module `src/seshat/metric_drift.py` (parses YAML, never in the `retail check` import chain). Phase 1 hardens that module, then adds a new CLI subcommand `retail semantic-check` that loads metric contracts + measure DAX, runs `check_measure_drift`, maps `Verdict` → `Finding`, and exits 1 on any drift. yaml is imported lazily inside the handler only.

**Tech Stack:** Python 3.13 (stdlib only for the core; `pyyaml` is a dev/optional dep used lazily), pytest, argparse CLI, GitHub Actions CI.

## Global Constraints

- **Python:** `requires-python >=3.13`; run all tests via the project venv: `./.venv/Scripts/python.exe -m pytest`.
- **Stdlib-only core:** `pyproject.toml` `dependencies = []`. The `retail.cli → retail.rules` import chain MUST import zero third-party packages. `yaml` is imported **lazily inside function bodies only**, never at module scope in `cli.py` or `metric_drift.py`.
- **L3 is NOT a registered rule:** never add an L3 "D9" to the registry or `EXPECTED_RULE_IDS`. It ships as a subcommand + lazy module only (ADR 0007).
- **Escalate ≠ drift:** `drift` → ERROR (fail CI); `escalate` → WARNING (never blocks); `pass`/`skip` → silent. Never pass-on-uncertain, never drift-on-uncertain.
- **Regex safety:** every new predicate regex uses `re.IGNORECASE | re.DOTALL` and routes its column capture through the existing `_strip_column_qualification` (bracket-notation `re.fullmatch`, `""` → escalate).
- **Locators:** repo-relative POSIX `path:line` (forward slashes).
- **Commits:** end every commit message with the Co-Authored-By trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **No attribution beyond that trailer** in code/docs.

---

## File Map

- `tests/unit/test_rules_wiring.py` — MODIFY (Task 1): fix G6 wiring symmetry.
- `src/seshat/metric_drift.py` — MODIFY (Tasks 2, 3): +4 predicates, +additive guard.
- `tests/unit/test_metric_drift.py` — MODIFY (Tasks 2, 3): predicate + additive tests.
- `src/seshat/semantic.py` — CREATE (Task 4): pure Verdict→Finding mapping + measure/contract pairing (kept out of cli.py so it is unit-testable and small).
- `tests/unit/test_semantic.py` — CREATE (Task 4): mapping + pairing tests.
- `src/seshat/cli.py` — MODIFY (Task 5): `semantic-check` parser + dispatch + `_run_semantic_check` handler (lazy imports).
- `tests/unit/test_cli_semantic.py` — CREATE (Task 5): subcommand + stdlib-guard tests.
- `.github/workflows/ci.yml` — MODIFY (Task 6): new gated step.

---

## Task 1: Fix the G6 wiring-test symmetry (precondition)

**Why:** G6 is registered (`src/seshat/rules/g6.py:49`) and imported (`src/seshat/rules/__init__.py:14`), so the live registry has 28 rules. But `EXPECTED_RULE_IDS` omits `"G6"` AND the reload loop / importability tuple omit `"g6"`. The suite passes only by omission symmetry. Phase 2 will edit these structures; fix the gap first so the wiring test actually validates all 28 rules.

**Files:**
- Modify: `tests/unit/test_rules_wiring.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a wiring test that includes `G6`/`g6` everywhere — later D-rule additions extend the same complete structures.

- [ ] **Step 1: Make the reload loop include `g6` so the test reflects reality (RED first)**

In `tests/unit/test_rules_wiring.py`, change the reload loop (currently line ~78):

```python
    for sub in ("git_meta", "sql", "dax", "pbir", "g6"):
        importlib.reload(importlib.import_module(f"retail.rules.{sub}"))
```

- [ ] **Step 2: Run the wiring test to verify it now FAILS (proves the latent gap)**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_rules_wiring.py::test_registered_rule_ids_match_expected_set -q --no-cov`
Expected: FAIL with `rule-id drift: missing=set(), unexpected={'G6'}` (G6 now enters `actual` but is not in `EXPECTED_RULE_IDS`).

- [ ] **Step 3: Add `"G6"` to `EXPECTED_RULE_IDS` and `"g6"` to the importability tuple**

In `tests/unit/test_rules_wiring.py`, add `"G6"` into the `EXPECTED_RULE_IDS` frozenset next to the other G-family ids:

```python
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",  # git hygiene
        "G6",  # PBIP parameter hygiene (no real host/value in committed params)
```

And update the importability tuple (currently line ~17):

```python
    for sub in ("git_meta", "sql", "dax", "pbir", "g6"):
        mod = importlib.import_module(f"retail.rules.{sub}")
        assert mod is not None
```

- [ ] **Step 4: Run the wiring test to verify it PASSES (now validates all 28 rules)**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_rules_wiring.py -q --no-cov`
Expected: PASS (4 passed). `len(all_rules()) == len(EXPECTED_RULE_IDS) == 28`.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS (308 passed — the prior 307 plus the now-validated G6 path; 0 failed).

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_rules_wiring.py
git commit -m "test: fix G6 wiring-test symmetry gap (validate all 28 rules)

G6 was registered + imported but absent from EXPECTED_RULE_IDS and the
reload/importability tuples, so the wiring test passed by omission
symmetry without validating G6. Add G6/g6 everywhere.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Widen the L3 predicate whitelist (+4 spellings)

**Why:** Today only `NOT(ISBLANK(col))` → is_not_null and `col = TRUE()` → is_true are recognized; everything else escalates. Add 4 tight, type-knowledge-free equivalents so common valid spellings get a confident verdict instead of escalating.

**Files:**
- Modify: `src/seshat/metric_drift.py` (the predicate regexes ~lines 67-75 and `_recognize_filter` ~lines 172-188)
- Test: `tests/unit/test_metric_drift.py`

**Interfaces:**
- Consumes: existing `_strip_column_qualification(colref) -> str` (returns bare column or `""`), `Filter(column, op)`.
- Produces: `_recognize_filter(pred: str) -> Filter | None` now also recognizes `col <> BLANK()`, `ISBLANK(col)=FALSE()` (→ is_not_null) and `TRUE() = col`, `col <> FALSE()` (→ is_true).

- [ ] **Step 1: Write failing tests for the 4 new spellings (all must `pass`, not escalate)**

Add to `tests/unit/test_metric_drift.py` (after the existing escalate tests):

```python
# --- WIDENED predicate whitelist: 4 new recognized spellings -----------------


def test_is_not_null_via_ne_blank_passes() -> None:
    """`col <> BLANK()` is the recognized-equivalent of NOT(ISBLANK(col))."""
    dax = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), CALCULATE([TransactionCount], "
        "'gold fct_sales_rss'[discount_applied] <> BLANK()))"
    )
    v = check_measure_drift(dax, DEF_DISCOUNTED)
    assert v.status == "pass", v


def test_is_not_null_via_isblank_eq_false_passes() -> None:
    """`ISBLANK(col) = FALSE()` is the recognized-equivalent of NOT(ISBLANK(col))."""
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "ISBLANK('gold fct_sales_rss'[total_spent]) = FALSE()))"
    )
    v = check_measure_drift(dax, DEF_AVG)
    assert v.status == "pass", v


def test_is_true_via_true_eq_col_passes() -> None:
    """`TRUE() = col` is the order-flipped recognized-equivalent of col = TRUE()."""
    contract = {
        "additive": False,
        "numerator": {"aggregation": "count_rows", "filter": []},
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        },
    }
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "TRUE() = 'gold fct_sales_rss'[discount_applied]))"
    )
    v = check_measure_drift(dax, contract)
    assert v.status == "pass", v


def test_is_true_via_ne_false_passes() -> None:
    """`col <> FALSE()` is the recognized-equivalent of col = TRUE()."""
    contract = {
        "additive": False,
        "numerator": {"aggregation": "count_rows", "filter": []},
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        },
    }
    dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "'gold fct_sales_rss'[discount_applied] <> FALSE()))"
    )
    v = check_measure_drift(dax, contract)
    assert v.status == "pass", v
```

- [ ] **Step 2: Run the new tests to verify they FAIL (currently escalate)**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov -k "ne_blank or isblank_eq_false or true_eq_col or ne_false"`
Expected: FAIL (4 failed) — current code escalates these spellings, so `v.status == "escalate"`, not `"pass"`.

- [ ] **Step 3: Add the 4 regexes and recognition branches in `metric_drift.py`**

After the existing `_RE_IS_TRUE` block (~line 75), add:

```python
# `<colref> <> BLANK ( )`  -> is_not_null  (recognized-equivalent of NOT(ISBLANK))
_RE_NE_BLANK = re.compile(
    r"^(?P<col>.+?)\s*<>\s*BLANK\s*\(\s*\)$", re.IGNORECASE | re.DOTALL
)
# `ISBLANK ( <colref> ) = FALSE ( )`  -> is_not_null
_RE_ISBLANK_EQ_FALSE = re.compile(
    r"^ISBLANK\s*\(\s*(?P<col>.+?)\s*\)\s*=\s*FALSE\s*\(\s*\)$",
    re.IGNORECASE | re.DOTALL,
)
# `TRUE ( ) = <colref>`  -> is_true  (order-flipped form of col = TRUE())
_RE_TRUE_EQ = re.compile(
    r"^TRUE\s*\(\s*\)\s*=\s*(?P<col>.+?)$", re.IGNORECASE | re.DOTALL
)
# `<colref> <> FALSE ( )`  -> is_true
_RE_NE_FALSE = re.compile(
    r"^(?P<col>.+?)\s*<>\s*FALSE\s*\(\s*\)$", re.IGNORECASE | re.DOTALL
)
```

Then in `_recognize_filter` (~lines 172-188), add the new branches BEFORE the final `return None`. Each routes its capture through `_strip_column_qualification` (so a non-bracket capture → `""` → falls through to escalate):

```python
    m = _RE_NE_BLANK.match(pred)
    if m:
        col = _strip_column_qualification(m.group("col"))
        if col:
            return Filter(column=col, op="is_not_null")
    m = _RE_ISBLANK_EQ_FALSE.match(pred)
    if m:
        col = _strip_column_qualification(m.group("col"))
        if col:
            return Filter(column=col, op="is_not_null")
    m = _RE_TRUE_EQ.match(pred)
    if m:
        col = _strip_column_qualification(m.group("col"))
        if col:
            return Filter(column=col, op="is_true")
    m = _RE_NE_FALSE.match(pred)
    if m:
        col = _strip_column_qualification(m.group("col"))
        if col:
            return Filter(column=col, op="is_true")
    return None
```

- [ ] **Step 4: Run the new tests to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov -k "ne_blank or isblank_eq_false or true_eq_col or ne_false"`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full metric_drift suite to confirm the existing escalate test still holds**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov`
Expected: PASS. NOTE: the existing `test_unrecognized_predicate_escalates` uses `col <> BLANK()` as its "unknown" example — it will now be RECOGNIZED, so this test must be updated. Change its DAX to a still-unrecognized spelling (`LEN(col) <> 0`) and keep the escalate assertion:

```python
def test_unrecognized_predicate_escalates() -> None:
    """An unknown predicate spelling is NOT guessed -- it escalates to a human.

    `LEN(col) <> 0` is semantically is_not_null for text but needs type knowledge;
    it is intentionally NOT in the recognized whitelist -> escalate.
    """
    unknown = (
        "DIVIDE(CALCULATE([TransactionCount], 'gold fct_sales_rss'[discount_applied] "
        "= TRUE()), CALCULATE([TransactionCount], "
        "LEN('gold fct_sales_rss'[discount_applied]) <> 0))"
    )
    v = check_measure_drift(unknown, DEF_DISCOUNTED)
    assert v.status == "escalate", v
```

Re-run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov`
Expected: PASS (all metric_drift tests).

- [ ] **Step 6: Commit**

```bash
git add src/seshat/metric_drift.py tests/unit/test_metric_drift.py
git commit -m "feat: widen L3 predicate whitelist (+4 recognized spellings)

Recognize col<>BLANK(), ISBLANK(col)=FALSE() (is_not_null) and
TRUE()=col, col<>FALSE() (is_true). Each routes its column capture
through _strip_column_qualification; all patterns IGNORECASE|DOTALL.
Escalate-by-default preserved for everything else.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Additive-measure escalate guard

**Why:** `check_measure_drift` never reads `definition['additive']`. A measure marked `additive: true` would be wrongly run through ratio/denominator logic. Escalate it instead.

**Files:**
- Modify: `src/seshat/metric_drift.py` (`check_measure_drift`, after the existing `skip` check ~line 213)
- Test: `tests/unit/test_metric_drift.py`

**Interfaces:**
- Consumes: `check_measure_drift(dax_expr, definition) -> Verdict`.
- Produces: same signature; now returns `escalate` when `definition.get("additive") is not False`.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_metric_drift.py`:

```python
def test_additive_measure_escalates() -> None:
    """An additive measure's denominator filter-set logic does not apply -> escalate."""
    additive_def = {
        "additive": True,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    v = check_measure_drift(DAX_AVG, additive_def)
    assert v.status == "escalate", v
    assert "additive" in v.detail.lower()


def test_missing_additive_flag_escalates() -> None:
    """A definition that omits `additive` is treated as not-confirmed-ratio -> escalate."""
    no_flag_def = {
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    v = check_measure_drift(DAX_AVG, no_flag_def)
    assert v.status == "escalate", v
```

- [ ] **Step 2: Run the new tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov -k "additive"`
Expected: FAIL (2 failed) — current code ignores `additive`, so `DAX_AVG` against this denominator returns `pass`/`drift`, not `escalate`.

- [ ] **Step 3: Add the guard in `check_measure_drift`**

In `src/seshat/metric_drift.py`, immediately AFTER the existing skip check (the block that returns `Verdict("skip", ...)` when there is no `definition` or no `"denominator"`), add:

```python
    # Additive measures are not ratios; denominator filter-set logic does not apply.
    # Require an explicit `additive: false` to proceed; True or absent -> escalate.
    if definition.get("additive") is not False:
        return Verdict(
            "escalate",
            "additive measure (or `additive` unset); "
            "denominator filter-set logic does not apply",
        )
```

- [ ] **Step 4: Run the new tests to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov -k "additive"`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full metric_drift suite (the 2 shipped measures set additive: False, so they still pass)**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py -q --no-cov`
Expected: PASS (all, including `test_shipped_discounted_rate_passes` / `test_shipped_avg_transaction_value_passes`).

- [ ] **Step 6: Commit**

```bash
git add src/seshat/metric_drift.py tests/unit/test_metric_drift.py
git commit -m "feat: escalate additive measures in L3 drift check

check_measure_drift now requires an explicit additive: false; a measure
marked additive (or with the flag unset) escalates rather than being
wrongly evaluated as a ratio. Non-breaking: both shipped measures set
additive: false.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Pure semantic-check core (`semantic.py`) — pairing + Verdict→Finding

**Why:** Keep the pairing logic (measure DAX ↔ contract) and the Verdict→Finding mapping in a small, unit-testable module separate from `cli.py`. This module is stdlib-only at import (it does NOT import yaml — the caller passes already-loaded definitions), and it is NEVER imported by `retail.rules`.

**Files:**
- Create: `src/seshat/semantic.py`
- Test: `tests/unit/test_semantic.py`

**Interfaces:**
- Consumes: `from .core import Finding, Severity`; `from .metric_drift import Verdict, check_measure_drift`.
- Produces:
  - `verdict_to_finding(measure_name: str, locator: str, verdict: Verdict) -> Finding | None` — `drift`→ERROR Finding, `escalate`→WARNING Finding, `pass`/`skip`→None.
  - `MeasurePair` (frozen dataclass: `name: str`, `dax: str`, `locator: str`, `definition: dict | None`).
  - `run_semantic_pairs(pairs: Iterable[MeasurePair]) -> tuple[list[Finding], int]` — returns `(findings, exit_code)`; exit_code is 1 iff any ERROR finding.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_semantic.py`:

```python
"""Unit tests for the L3 semantic-check core (src/seshat/semantic.py)."""

from __future__ import annotations

import pytest

from retail.core import Severity
from retail.metric_drift import Verdict
from retail.semantic import MeasurePair, run_semantic_pairs, verdict_to_finding

pytestmark = pytest.mark.unit

DEF_AVG = {
    "additive": False,
    "numerator": {"aggregation": "sum", "filter": []},
    "denominator": {
        "aggregation": "count_rows",
        "filter": [{"column": "total_spent", "op": "is_not_null"}],
    },
}
DAX_AVG = (
    "DIVIDE([TotalSales], CALCULATE([TransactionCount], NOT(ISBLANK("
    "'gold fct_sales_rss'[total_spent]))))"
)


def test_verdict_drift_maps_to_error_finding() -> None:
    f = verdict_to_finding("M", "path.tmdl:3", Verdict("drift", "wrong denominator"))
    assert f is not None
    assert f.severity is Severity.ERROR
    assert f.rule_id == "L3"
    assert "M" in f.message
    assert f.locator == "path.tmdl:3"


def test_verdict_escalate_maps_to_warning_finding() -> None:
    f = verdict_to_finding("M", "path.tmdl:3", Verdict("escalate", "unknown predicate"))
    assert f is not None
    assert f.severity is Severity.WARNING


def test_verdict_pass_maps_to_none() -> None:
    assert verdict_to_finding("M", "p:1", Verdict("pass", "ok")) is None


def test_verdict_skip_maps_to_none() -> None:
    assert verdict_to_finding("M", "p:1", Verdict("skip", "no definition")) is None


def test_run_pairs_clean_passes_exit_zero() -> None:
    pairs = [MeasurePair("AvgTransactionValue", DAX_AVG, "p.tmdl:1", DEF_AVG)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert findings == []
    assert exit_code == 0


def test_run_pairs_drift_exits_one() -> None:
    buggy_def = {
        "additive": False,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "discount_applied", "op": "is_not_null"}],
        },
    }
    pairs = [MeasurePair("AvgTransactionValue", DAX_AVG, "p.tmdl:1", buggy_def)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert exit_code == 1
    assert any(f.severity is Severity.ERROR for f in findings)


def test_run_pairs_escalate_warns_but_exits_zero() -> None:
    escalate_def = {
        "additive": False,
        "denominator": {
            "aggregation": "count_rows",
            "filter": [{"column": "total_spent", "op": "is_not_null"}],
        },
    }
    escalate_dax = (
        "DIVIDE([TotalSales], CALCULATE([TransactionCount], "
        "LEN('gold fct_sales_rss'[total_spent]) <> 0))"
    )
    pairs = [MeasurePair("AvgTransactionValue", escalate_dax, "p.tmdl:1", escalate_def)]
    findings, exit_code = run_semantic_pairs(pairs)
    assert exit_code == 0  # WARNING does not fail the gate
    assert any(f.severity is Severity.WARNING for f in findings)
```

- [ ] **Step 2: Run the tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_semantic.py -q --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'retail.semantic'`.

- [ ] **Step 3: Create `src/seshat/semantic.py`**

```python
"""L3 semantic-check core: pair measures with contracts, map Verdicts to Findings.

Stdlib-only at IMPORT time (it does NOT import yaml -- the caller loads contract
definitions and passes them in). Like metric_drift, this module is NEVER imported by
retail.rules; it is used only by the `retail semantic-check` CLI handler.

Verdict -> severity mapping (the gating posture, ADR 0007):
  drift    -> ERROR   (fails the gate)
  escalate -> WARNING (surfaced, does NOT fail the gate -- human review)
  pass     -> None    (silent)
  skip     -> None    (silent; contract has no structured definition yet)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .core import Finding, Severity
from .metric_drift import Verdict, check_measure_drift

__all__ = ["MeasurePair", "verdict_to_finding", "run_semantic_pairs"]

# Stable tag for L3 findings (NOT a registered rule id -- see ADR 0007).
_L3_TAG = "L3"


@dataclass(frozen=True)
class MeasurePair:
    """One measure paired with its contract definition.

    name:       measure name (== contract `name` == YAML stem).
    dax:        the measure's DAX expression (from TMDL).
    locator:    repo-relative POSIX `path:line` of the measure.
    definition: the contract's `definition` block, or None (-> skip).
    """

    name: str
    dax: str
    locator: str
    definition: dict | None


def verdict_to_finding(
    measure_name: str, locator: str, verdict: Verdict
) -> Finding | None:
    """Map a Verdict to a Finding, or None for pass/skip (no finding)."""
    if verdict.status == "drift":
        severity = Severity.ERROR
    elif verdict.status == "escalate":
        severity = Severity.WARNING
    else:  # pass | skip
        return None
    return Finding(
        rule_id=_L3_TAG,
        severity=severity,
        message=f"measure '{measure_name}': {verdict.detail}",
        locator=locator,
    )


def run_semantic_pairs(pairs: Iterable[MeasurePair]) -> tuple[list[Finding], int]:
    """Run the drift check over every pair; return (findings, exit_code).

    exit_code is 1 iff any ERROR finding (a drift), else 0. escalate/WARNING never
    fails the gate.
    """
    findings: list[Finding] = []
    for pair in pairs:
        verdict = check_measure_drift(pair.dax, pair.definition)
        finding = verdict_to_finding(pair.name, pair.locator, verdict)
        if finding is not None:
            findings.append(finding)
    exit_code = 1 if any(f.severity is Severity.ERROR for f in findings) else 0
    return findings, exit_code
```

- [ ] **Step 4: Run the tests to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_semantic.py -q --no-cov`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/semantic.py tests/unit/test_semantic.py
git commit -m "feat: add L3 semantic-check core (pairing + Verdict->Finding)

src/seshat/semantic.py maps drift->ERROR, escalate->WARNING, pass/skip->
none, and runs the drift check over measure/contract pairs returning
(findings, exit_code). Stdlib-only at import; never imported by
retail.rules.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `retail semantic-check` subcommand (cli.py) + stdlib guard

**Why:** Expose L3 as a CI-gating subcommand. The handler loads metric contracts (lazy yaml), pairs each with its measure's DAX from TMDL (via the existing `parse_tmdl`), runs `run_semantic_pairs`, prints findings, and returns the exit code. yaml + semantic + metric_drift are imported INSIDE the handler only.

**Files:**
- Modify: `src/seshat/cli.py` (parser ~after line 70; dispatch ~after line 105; new `_run_semantic_check`)
- Test: `tests/unit/test_cli_semantic.py`

**Interfaces:**
- Consumes: `from .semantic import MeasurePair, run_semantic_pairs`; `from .metric_drift import load_definition`; `from .tmdl import parse_tmdl, iter_model_files` (already exists); `from .runner import build_context, _format`.
- Produces: `main(["semantic-check", "--repo", X, "--metrics-dir", Y]) -> int` (0 clean / WARNING-only, 1 on any drift).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_cli_semantic.py`:

```python
"""Tests for `retail semantic-check` subcommand + its stdlib-purity guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main

pytestmark = pytest.mark.unit


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# A minimal repo: one measure in TMDL + one matching contract with a definition.
_TMDL = """\
table 'gold fct_sales_rss'

\tmeasure AvgTransactionValue = DIVIDE([TotalSales], CALCULATE([TransactionCount], NOT(ISBLANK('gold fct_sales_rss'[total_spent]))))
\t\tdisplayFolder: Sales
"""

_CONTRACT_CLEAN = """\
name: "AvgTransactionValue"
definition:
  additive: false
  numerator: {aggregation: sum, filter: []}
  denominator:
    aggregation: count_rows
    filter:
      - column: total_spent
        op: is_not_null
"""

_CONTRACT_DRIFT = """\
name: "AvgTransactionValue"
definition:
  additive: false
  numerator: {aggregation: sum, filter: []}
  denominator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_not_null
"""


def _make_repo(tmp_path: Path, contract: str) -> Path:
    _write(
        tmp_path
        / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        _TMDL,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    return tmp_path


def test_semantic_check_clean_exits_zero(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    code = main(
        ["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"]
    )
    assert code == 0


def test_semantic_check_drift_exits_one(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_DRIFT)
    code = main(
        ["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "L3" in out
    assert "AvgTransactionValue" in out


def test_cli_does_not_import_yaml_or_metric_drift_at_module_scope() -> None:
    """cli.py must keep yaml + L3 modules out of its module scope (stdlib core)."""
    import retail.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.lstrip()
        is_top_level = line == stripped  # column 0 == module scope
        if is_top_level and (
            stripped.startswith("import yaml")
            or stripped.startswith("from yaml")
            or stripped.startswith("from .metric_drift")
            or stripped.startswith("from .semantic")
            or stripped.startswith("import retail.metric_drift")
            or stripped.startswith("import retail.semantic")
        ):
            raise AssertionError(f"cli.py imports L3/yaml at module scope: {line!r}")
```

- [ ] **Step 2: Run the tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_cli_semantic.py -q --no-cov`
Expected: FAIL — `main(["semantic-check", ...])` is unknown (argparse error / returns 2), so the exit-code assertions fail. (The stdlib-guard test passes trivially now; keep it — it locks the invariant once the handler is added.)

- [ ] **Step 3: Add the parser branch in `_build_parser` (after the `validate` block, before `return parser`)**

In `src/seshat/cli.py`, before `return parser` (currently line 71):

```python
    # L3 semantic / contract<->DAX drift gate (feature: DAX fortification Phase 1).
    # Parses metric-contract YAML (lazy yaml inside the handler) -- NOT in the
    # stdlib-only `retail check` core chain.
    semantic = sub.add_parser(
        "semantic-check",
        help="L3 contract<->DAX denominator drift on committed metric contracts",
    )
    semantic.add_argument("--repo", default=".", help="repo root to check")
    semantic.add_argument(
        "--metrics-dir",
        dest="metrics_dir",
        default="mappings",
        metavar="DIR",
        help="root dir holding <dataset>/metrics/<Measure>.yaml contracts",
    )
```

- [ ] **Step 4: Add the dispatch branch in `main` (after the `validate` branch, before `return 0`)**

In `src/seshat/cli.py`, after the `if args.command == "validate": return _run_validate(args)` block (line 105), add:

```python
    if args.command == "semantic-check":
        return _run_semantic_check(args)
```

- [ ] **Step 5: Add the `_run_semantic_check` handler (lazy imports inside)**

Append to `src/seshat/cli.py` (before the `if __name__ == "__main__":` guard):

```python
def _run_semantic_check(args) -> int:
    """Run the L3 contract<->DAX drift gate.

    Lazy imports (yaml via load_definition, plus semantic + metric_drift) live
    INSIDE this handler so the stdlib-only `retail check` import chain never pulls
    them. Pairs each committed measure (from TMDL) with its contract definition
    (mappings/<dataset>/metrics/<name>.yaml) and reports drift (ERROR) / escalate
    (WARNING). Returns 1 iff any drift.
    """
    from .metric_drift import load_definition
    from .runner import _format, build_context
    from .semantic import MeasurePair, run_semantic_pairs
    from .tmdl import iter_model_files, parse_tmdl

    repo = Path(args.repo)
    ctx = build_context(repo)

    # 1. Index contract definitions by measure name (YAML stem == measure name).
    definitions: dict[str, dict | None] = {}
    metrics_root = repo / args.metrics_dir
    if metrics_root.is_dir():
        for contract_path in sorted(metrics_root.glob("*/metrics/*.yaml")):
            name = contract_path.stem
            try:
                definitions[name] = load_definition(str(contract_path))
            except (OSError, ValueError) as exc:
                print(
                    f"error: could not load contract {contract_path}: {exc}",
                    file=sys.stderr,
                )
                return 1

    # 2. Pair each committed measure with its contract definition (if any).
    pairs: list[MeasurePair] = []
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for measure in table.measures:
            if measure.name in definitions:
                pairs.append(
                    MeasurePair(
                        name=measure.name,
                        dax=measure.expression,
                        locator=f"{rel}:{measure.line}",
                        definition=definitions[measure.name],
                    )
                )

    # 3. Run the drift check; print findings; return the exit code.
    findings, exit_code = run_semantic_pairs(pairs)
    for finding in findings:
        print(_format(finding))
    if exit_code == 0 and not findings:
        print("retail semantic-check: no drift (0 findings).", file=sys.stderr)
    return exit_code
```

- [ ] **Step 6: Run the tests to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_cli_semantic.py -q --no-cov`
Expected: PASS (3 passed).

- [ ] **Step 7: Run the stdlib-invariant subprocess test (must stay green)**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_metric_drift.py::test_importing_retail_rules_does_not_pull_metric_drift -q --no-cov`
Expected: PASS — `retail.rules` still pulls neither metric_drift nor yaml (the new imports are all inside `_run_semantic_check`).

- [ ] **Step 8: Commit**

```bash
git add src/seshat/cli.py tests/unit/test_cli_semantic.py
git commit -m "feat: add 'retail semantic-check' CLI subcommand (L3 gate)

New subcommand pairs committed measures (TMDL) with metric-contract
definitions (mappings/*/metrics/*.yaml), runs the drift check, prints
findings, and exits 1 on drift. yaml/semantic/metric_drift imported
lazily inside the handler so the stdlib-only check core stays pure;
a guard test asserts cli.py has no module-scope L3/yaml import.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: CI gating step (`.github/workflows/ci.yml`)

**Why:** Make drift fail the build. Run `retail semantic-check` as a SEPARATE step (yaml installed) after the stdlib-only `retail check` step, so the check job never imports yaml.

**Files:**
- Modify: `.github/workflows/ci.yml` (add a step after the existing `retail check` step ~line 53)

**Interfaces:**
- Consumes: the installed `retail` console script + `pyyaml` (dev extra).
- Produces: a CI step that fails the job on any L3 drift.

- [ ] **Step 1: Inspect the current CI to find the exact step + install context**

Run: `./.venv/Scripts/python.exe -c "print(open('.github/workflows/ci.yml').read())"`
Confirm: the job installs the dev extra (`pip install -e '.[dev]'`, which includes `pyyaml`) and has a "Retail governance check" step running `retail check ...` around line 34-53. Note the exact step name + indentation.

- [ ] **Step 2: Add the semantic-check step immediately after the `retail check` step**

In `.github/workflows/ci.yml`, after the existing governance-check step, add (match the file's existing indentation):

```yaml
      - name: Retail semantic-check (L3 contract<->DAX drift)
        run: retail semantic-check --repo .
```

(No `--commit-range` — L3 reads committed TMDL + contracts, not git diffs. `pyyaml` is already present via the dev extra the job installs.)

- [ ] **Step 3: Validate the YAML parses**

Run: `./.venv/Scripts/python.exe -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('ci.yml OK')"`
Expected: `ci.yml OK`

- [ ] **Step 4: Smoke-test the command locally against the real repo (must be clean)**

Run: `./.venv/Scripts/python.exe -m retail.cli semantic-check --repo .`
Expected: exit 0 — the two shipped measures (`AvgTransactionValue`, `DiscountedTransactionRate`) match their approved contracts; the other 3 contracts have no `definition` block → skip (silent). Stderr: "no drift (0 findings)."

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: gate on L3 contract<->DAX drift (retail semantic-check)

Separate CI step after 'retail check' runs 'retail semantic-check';
drift fails the build. Kept distinct so the stdlib-only check job never
imports yaml.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Full-suite verification + coverage gate

**Why:** Confirm the whole change is green under the project's normal invocation (with coverage), not just the targeted `--no-cov` runs.

**Files:** none (verification only).

- [ ] **Step 1: Run the entire suite with coverage (the project default `addopts`)**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS — prior 307 + G6 path + new metric_drift/semantic/cli tests, 0 failed. Coverage report prints; `metric_drift.py`, `semantic.py`, and the new `cli.py` handler should show high coverage (the new lines are exercised by Tasks 2-5 tests).

- [ ] **Step 2: Run ruff + black to confirm style compliance**

Run: `./.venv/Scripts/python.exe -m ruff check src/seshat/metric_drift.py src/seshat/semantic.py src/seshat/cli.py tests/unit/test_semantic.py tests/unit/test_cli_semantic.py tests/unit/test_metric_drift.py tests/unit/test_rules_wiring.py`
Then: `./.venv/Scripts/python.exe -m black --check src/seshat/ tests/unit/`
Expected: both clean (no errors, no reformatting needed). If black reports changes, run without `--check`, re-run the suite, and amend the relevant commit.

- [ ] **Step 3: Final confirmation message**

Phase 1 complete: L3 recognizes 6 predicate spellings (was 2), escalates additive measures, and gates CI on drift via `retail semantic-check` — with the stdlib-only `retail check` core proven unchanged (subprocess invariant test green).

---

## Self-Review Notes (author)

- **Spec coverage:** Unit 0 (Task 1), predicate widening §1a (Task 2), additive guard §1b (Task 3), Verdict→Finding §1e (Task 4), subcommand §1d (Task 5), CI §1f (Task 6), stdlib invariant (Tasks 4-5 guards + Task 5 step 7), testing conventions (every task's TDD cycle). Measure-shape §1c is "no change" — correctly no task.
- **Type consistency:** `MeasurePair(name, dax, locator, definition)`, `verdict_to_finding(measure_name, locator, verdict)`, `run_semantic_pairs(pairs) -> (findings, exit_code)`, `Verdict(status, detail)`, `Finding(rule_id, severity, message, locator)` — used identically across Tasks 4 and 5.
- **Pre-existing-test impact called out:** Task 2 Step 5 explicitly fixes `test_unrecognized_predicate_escalates` (its old `col <> BLANK()` example becomes recognized).
- **No placeholders:** every code/test step shows the real content.
