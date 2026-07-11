# DAX Generator (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, stdlib-pure DAX Generator that turns a metric contract's structured `definition` block into a verified best-practice DAX measure, refusing to emit anything it cannot prove correct.

**Architecture:** A new lazy module `src/seshat/dax_gen.py` (mirroring `metric_drift.py`'s stdlib-pure-import discipline) emits canonical DAX for two `kind`s (`base`, `ratio`), then runs a fail-closed pipeline: validate shape → emit DAX → L3 semantic verify (`check_measure_drift`) → D1–D11 form verify. `metric_drift.check_measure_drift` is extended additively with a `kind: base` branch (the only new reader of the `aggregation` field; the `kind`-absent path stays byte-identical). A `retail generate` CLI subcommand wraps the engine with a stdout-verified-only, never-mutate-the-model contract.

**Tech Stack:** Python 3 (stdlib only in core; `yaml` lazy in loaders), `argparse` CLI, `pytest` (table-driven `parametrize`, no new test deps), `ruff`/`black`.

**Spec:** `docs/superpowers/specs/2026-06-26-dax-generator-design.md` (approved).

## Global Constraints

- **Stdlib-only core invariant:** `dax_gen.py` and the `kind: base` extension MUST NOT be importable from the `retail check` core chain (`retail.cli → retail.rules`). `import yaml` is lazy, ONLY inside contract loaders. A subprocess test asserts `import retail.rules` pulls in neither `dax_gen` nor `yaml`.
- **Zero-regression:** `check_measure_drift` with `kind` absent behaves byte-identically to today. Existing `tests/unit/test_metric_drift.py` tests pass UNCHANGED. The `kind: base` branch is the ONLY new reader of `definition["aggregation"]`.
- **Fail-closed:** `pass` is the only acceptable round-trip result. `drift | escalate | skip | uncertainty | unsupported shape` → `GenResult(ok=False)`. On refusal, `dax is None` AND `tmdl_block is None`.
- **Never mutate truth:** no write under `powerbi/**` (checked on the RESOLVED path); refuse to overwrite an existing `--out` file; no DB; no LLM; no free-form DAX; only `kind ∈ {base, ratio}`.
- **Define/check boundary:** the generator reads the `definition` block ONLY for semantics. `formula_intent` reaches ONLY the `///` doc comment via a separate `doc_intent` param — never generation/verification.
- **Vocabulary:** contract-side aggregation names are lowercase with underscores as in committed contracts: `sum`, `count`, `distinct_count`, `average`, `count_rows`. (Maps to DAX `SUM`/`COUNT`/`DISTINCTCOUNT`/`AVERAGE`/`COUNTROWS`.)
- **Extensibility invariant (guard, not wall):** every Phase-1 narrowing is a refusal guard; lifting it later must be purely additive (a new `kind`, whitelist entry, ratio-side branch, or verifier branch) and must not break public signatures or existing contracts.
- **Filter ops:** reuse the EXISTING tight whitelist `{is_true, is_not_null}` and the EXISTING canonical spellings (`is_true → col = TRUE()`; `is_not_null → NOT(ISBLANK(col))`).
- **Style:** type annotations on every signature; `@dataclass(frozen=True)` DTOs; functions <50 lines; ASCII-only output (no Unicode glyphs).
- **Commits:** unsigned commits are authorized for THIS feature's commits (1Password signing key unavailable this session — user-authorized `--no-gpg-sign`). Message form `<type>: <desc>` + the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/seshat/dax_gen.py` (NEW) | The engine: `GenResult` DTO, `generate_measure()`, shape validators, DAX emit templates, the verify pipeline, `load_contract()`. Lazy `yaml` in `load_contract` only. |
| `src/seshat/metric_drift.py` (MODIFY) | Add `_check_base_drift()` + a `kind` dispatch at the top of `check_measure_drift`. Additive; `kind`-absent path untouched. |
| `src/seshat/cli.py` (MODIFY) | Add `generate` subparser + `_run_generate()` handler (lazy import of `dax_gen`). |
| `templates/metric-contract.yaml` (MODIFY) | Document the additive `definition.kind` schema in COMMENTS ONLY. No real contract changes. |
| `tests/unit/test_dax_gen.py` (NEW) | Round-trip, D-rule cleanliness, refusals, sum-type invariant, doc_intent isolation, CLI behavior, `--out` guards. |
| `tests/unit/test_metric_drift.py` (MODIFY) | Zero-regression assertion, `kind: base` verify with HAND-AUTHORED fixtures, stdlib guard. |
| `tests/fixtures/contracts/*.yaml` (NEW) | Base/ratio/refusal contract fixtures for CLI tests. |

**Commit cadence:** one commit per task (each task ends green).

---

## Task 1: `GenResult` sum-type DTO

**Files:**
- Create: `src/seshat/dax_gen.py`
- Test: `tests/unit/test_dax_gen.py`

**Interfaces:**
- Produces: `GenResult` (frozen dataclass) with fields `ok: bool`, `dax: str | None = None`, `tmdl_block: str | None = None`, `reason: str | None = None`, `warnings: tuple[str, ...] = ()`. Constructors: `GenResult.success(dax, tmdl_block, warnings=())` and `GenResult.refuse(reason)`. `__post_init__` enforces the sum-type invariant (raises `ValueError` on violation).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_dax_gen.py
"""Unit tests for the DAX Generator (src/seshat/dax_gen.py).

Phase 1: kind:base + kind:ratio, generate -> verify -> refuse. The headline
property is the round-trip: every emitted measure re-verifies as `pass`.
"""

import pytest

from retail.dax_gen import GenResult

pytestmark = pytest.mark.unit


def test_genresult_success_populates_outputs_only():
    r = GenResult.success(dax="SUM(T[c])", tmdl_block="measure X = SUM(T[c])")
    assert r.ok is True
    assert r.dax == "SUM(T[c])"
    assert r.tmdl_block == "measure X = SUM(T[c])"
    assert r.reason is None


def test_genresult_refuse_has_none_outputs():
    r = GenResult.refuse("unsupported kind 'foo'")
    assert r.ok is False
    assert r.dax is None
    assert r.tmdl_block is None
    assert r.reason == "unsupported kind 'foo'"


def test_genresult_rejects_ok_without_dax():
    with pytest.raises(ValueError):
        GenResult(ok=True, dax=None, tmdl_block=None)


def test_genresult_rejects_refusal_with_dax():
    with pytest.raises(ValueError):
        GenResult(ok=False, dax="SUM(T[c])", reason="x")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.dax_gen'` (or ImportError on `GenResult`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/seshat/dax_gen.py
"""DAX Generator (Phase 1): contract `definition` -> verified DAX measure.

The INVERSE of metric_drift.check_measure_drift: that answers "does this DAX
match this contract?"; this answers "what DAX matches this contract?", then
feeds its own output back through the checker. Fail-closed: `pass` is the only
acceptable round-trip; anything else is a refusal (no DAX/TMDL emitted).

Stdlib-only at import time (mirrors metric_drift.py). `yaml` is imported lazily
ONLY in load_contract(); this module is never in the `retail check` core chain.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GenResult", "generate_measure", "load_contract"]


@dataclass(frozen=True)
class GenResult:
    """A sum type: EITHER (ok=True, dax, tmdl_block) OR (ok=False, reason).

    On refusal, dax and tmdl_block are None -- a caller cannot fish an
    unverified partial out of a refusal.
    """

    ok: bool
    dax: str | None = None
    tmdl_block: str | None = None
    reason: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.ok:
            if self.dax is None or self.tmdl_block is None:
                raise ValueError("ok GenResult must populate dax and tmdl_block")
            if self.reason is not None:
                raise ValueError("ok GenResult must not carry a reason")
        else:
            if self.dax is not None or self.tmdl_block is not None:
                raise ValueError("refusal GenResult must not carry dax/tmdl_block")
            if not self.reason:
                raise ValueError("refusal GenResult must carry a reason")

    @classmethod
    def success(
        cls, dax: str, tmdl_block: str, warnings: tuple[str, ...] = ()
    ) -> "GenResult":
        return cls(ok=True, dax=dax, tmdl_block=tmdl_block, warnings=warnings)

    @classmethod
    def refuse(cls, reason: str) -> "GenResult":
        return cls(ok=False, reason=reason)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dax_gen.py tests/unit/test_dax_gen.py
git commit --no-gpg-sign -m "feat: GenResult sum-type DTO for DAX generator

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Base-measure shape validation + DAX emit

**Files:**
- Modify: `src/seshat/dax_gen.py`
- Test: `tests/unit/test_dax_gen.py`

**Interfaces:**
- Consumes: `GenResult` (Task 1).
- Produces:
  - `_AGG_TO_DAX: dict[str, str]` = `{"sum": "SUM", "count": "COUNT", "distinct_count": "DISTINCTCOUNT", "average": "AVERAGE", "count_rows": "COUNTROWS"}`.
  - `_qualify(table: str, column: str | None) -> str` — render a column ref: `'gold fct_sales_rss'[col]` (dotted `gold.x` → space form `'gold x'`; bracket the column). For `count_rows`, table-only.
  - `_emit_predicate(f: dict) -> str | None` — `{column, op}` → canonical DAX spelling, or `None` for an unknown op.
  - `_emit_base(defn: dict) -> tuple[str | None, str | None]` — returns `(dax, None)` on success or `(None, reason)` on a shape refusal. Validates: aggregation in whitelist; `source.table` is `gold.*`; column REQUIRED for sum/count/distinct_count/average, FORBIDDEN for count_rows; filter ops known. Emits bare aggregation if no filter, else `CALCULATE(agg, pred, ...)`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/unit/test_dax_gen.py
from retail.dax_gen import _emit_base


def test_emit_base_sum_no_filter():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "gold.fct_sales_rss", "column": "total_spent"}}
    )
    assert reason is None
    assert dax == "SUM('gold fct_sales_rss'[total_spent])"


def test_emit_base_count_rows_no_column():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss"}}
    )
    assert reason is None
    assert dax == "COUNTROWS('gold fct_sales_rss')"


def test_emit_base_with_filter_wraps_calculate():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss"},
         "filter": [{"column": "discount_applied", "op": "is_true"}]}
    )
    assert reason is None
    assert dax == (
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE())"
    )


def test_emit_base_sum_without_column_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "gold.fct_sales_rss"}}
    )
    assert dax is None
    assert "column" in reason


def test_emit_base_count_rows_with_column_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.fct_sales_rss", "column": "x"}}
    )
    assert dax is None
    assert "count_rows" in reason


def test_emit_base_non_gold_table_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "sum",
         "source": {"table": "silver.fct", "column": "c"}}
    )
    assert dax is None
    assert "gold" in reason


def test_emit_base_unknown_aggregation_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "median",
         "source": {"table": "gold.t", "column": "c"}}
    )
    assert dax is None
    assert "aggregation" in reason


def test_emit_base_unknown_filter_op_refuses():
    dax, reason = _emit_base(
        {"kind": "base", "aggregation": "count_rows",
         "source": {"table": "gold.t"},
         "filter": [{"column": "c", "op": "is_weird"}]}
    )
    assert dax is None
    assert "op" in reason or "filter" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -k emit_base -v`
Expected: FAIL — `ImportError: cannot import name '_emit_base'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/seshat/dax_gen.py (after GenResult)

_AGG_TO_DAX: dict[str, str] = {
    "sum": "SUM",
    "count": "COUNT",
    "distinct_count": "DISTINCTCOUNT",
    "average": "AVERAGE",
    "count_rows": "COUNTROWS",
}
_NEEDS_COLUMN = {"sum", "count", "distinct_count", "average"}
# canonical predicate spellings -- MUST match the spellings metric_drift recognizes
_OP_TO_DAX = {
    "is_true": "{col} = TRUE()",
    "is_not_null": "NOT(ISBLANK({col}))",
}


def _qualify(table: str, column: str | None) -> str:
    """`gold.fct_sales_rss`,`col` -> `'gold fct_sales_rss'[col]`; table-only if no col.

    The committed TMDL uses a space-joined single-quoted table name
    (`'gold fct_sales_rss'`), matching what metric_drift parses. A dotted
    `schema.table` is rendered with the dot replaced by a space.
    """
    tbl = "'" + table.replace(".", " ") + "'"
    return f"{tbl}[{column}]" if column else tbl


def _emit_predicate(f: dict) -> str | None:
    col = f.get("column")
    op = f.get("op")
    tmpl = _OP_TO_DAX.get(op) if op else None
    if not col or tmpl is None:
        return None
    return tmpl.format(col=f"'__TBL__'[{col}]")  # table injected by caller


def _emit_base(defn: dict) -> tuple[str | None, str | None]:
    agg = defn.get("aggregation")
    if agg not in _AGG_TO_DAX:
        return None, f"unsupported aggregation {agg!r}"
    source = defn.get("source") or {}
    table = source.get("table")
    column = source.get("column")
    if not isinstance(table, str) or not table.startswith("gold."):
        return None, f"source.table must be a gold.* table, got {table!r}"
    if agg == "count_rows":
        if column:
            return None, "count_rows must not specify source.column (table only)"
    elif not column:
        return None, f"aggregation {agg!r} requires source.column"

    func = _AGG_TO_DAX[agg]
    inner = f"{func}({_qualify(table, column)})"

    filters = defn.get("filter") or []
    if not filters:
        return inner, None

    preds: list[str] = []
    tbl = "'" + table.replace(".", " ") + "'"
    for f in filters:
        col = f.get("column")
        op = f.get("op")
        tmpl = _OP_TO_DAX.get(op) if op else None
        if not col or tmpl is None:
            return None, f"unrecognized filter op {op!r} on column {col!r}"
        preds.append(tmpl.format(col=f"{tbl}[{col}]"))
    return f"CALCULATE({inner}, {', '.join(preds)})", None
```

> Note: the standalone `_emit_predicate` helper is kept for Task 4's ratio sides; the inline loop in `_emit_base` uses the table-qualified form directly. If `_emit_predicate` proves unused after Task 4, delete it (YAGNI) in Task 4's commit.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py -k emit_base -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dax_gen.py tests/unit/test_dax_gen.py
git commit --no-gpg-sign -m "feat: base-measure shape validation + DAX emit

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Extend `check_measure_drift` with the `kind: base` verify branch (independent fixtures)

**Files:**
- Modify: `src/seshat/metric_drift.py` (add `_check_base_drift` + a `kind` dispatch at the top of `check_measure_drift`)
- Test: `tests/unit/test_metric_drift.py` (add base cases with HAND-AUTHORED DAX + zero-regression assertion)

**Interfaces:**
- Consumes: existing `Verdict`, `Filter`, `_outer_call`, `_split_balanced`, `_recognize_filter`, `_strip_column_qualification` from `metric_drift.py`.
- Produces: `_check_base_drift(dax_expr: str, definition: dict) -> Verdict`. Recognizes `AGG(col)` and `CALCULATE(AGG(col_or_table), preds...)`; compares the emitted aggregation function + filter-set to the contract. `pass` on match; `drift` on filter/aggregation mismatch; `escalate` on any unrecognized shape. `check_measure_drift` dispatches: `definition.get("kind") == "base"` → `_check_base_drift`; otherwise the EXISTING ratio path UNCHANGED.

> **Why hand-authored DAX (the anti-circularity rule):** the ratio path is trusted because `check_measure_drift` is independently validated against verbatim committed DAX (`DAX_DISCOUNTED`). The base branch is NEW, so it must earn the same trust from HUMAN-WRITTEN fixtures here — NOT from generator output. The generator round-trip (Task 5) then validates the generator against this now-trusted checker. The base parser shares only the trusted leaf helpers with the rest of the module; it does NOT import the generator.

- [ ] **Step 1: Write the failing test (hand-authored fixtures + regression)**

```python
# append to tests/unit/test_metric_drift.py

# --- kind:base verify (HAND-AUTHORED DAX -- never generator output) ----------
# A base measure IS its own contract, so we check its aggregation + filter-set
# against the definition directly (the referenced-measure opacity rule does not
# apply: there is no referenced measure here).

DEF_BASE_REVENUE = {
    "kind": "base",
    "aggregation": "sum",
    "source": {"table": "gold.fct_sales_rss", "column": "total_spent"},
}
DAX_BASE_REVENUE = "SUM('gold fct_sales_rss'[total_spent])"  # hand-written

DEF_BASE_DISC_TXN = {
    "kind": "base",
    "aggregation": "count_rows",
    "source": {"table": "gold.fct_sales_rss"},
    "filter": [{"column": "discount_applied", "op": "is_true"}],
}
DAX_BASE_DISC_TXN = (  # hand-written
    "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
    "'gold fct_sales_rss'[discount_applied] = TRUE())"
)


def test_base_pass_matches_contract():
    assert check_measure_drift(DAX_BASE_REVENUE, DEF_BASE_REVENUE).status == "pass"


def test_base_pass_with_filter():
    assert check_measure_drift(DAX_BASE_DISC_TXN, DEF_BASE_DISC_TXN).status == "pass"


def test_base_drift_wrong_filter_column():
    # contract says discount_applied; DAX filters a different column -> drift
    bad = (
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[returned] = TRUE())"
    )
    assert check_measure_drift(bad, DEF_BASE_DISC_TXN).status == "drift"


def test_base_drift_missing_filter():
    bad = "COUNTROWS('gold fct_sales_rss')"  # contract requires a filter
    assert check_measure_drift(bad, DEF_BASE_DISC_TXN).status == "drift"


def test_base_drift_wrong_aggregation():
    bad = "COUNT('gold fct_sales_rss'[total_spent])"  # contract says sum
    assert check_measure_drift(bad, DEF_BASE_REVENUE).status == "drift"


def test_base_escalate_unrecognized_shape():
    bad = "SUMX('gold fct_sales_rss', [x] * [y])"  # not an AGG(col) shape
    assert check_measure_drift(bad, DEF_BASE_REVENUE).status == "escalate"


def test_base_escalate_unknown_predicate():
    bad = (
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "LEN('gold fct_sales_rss'[discount_applied]) <> 0)"
    )
    assert check_measure_drift(bad, DEF_BASE_DISC_TXN).status == "escalate"


# --- ZERO-REGRESSION: kind-absent path is byte-identical + sole new reader ---
def test_kind_absent_ratio_path_unchanged():
    # the existing committed ratio still passes exactly as before
    assert check_measure_drift(DAX_DISCOUNTED, DEF_DISCOUNTED).status == "pass"
    assert check_measure_drift(DAX_AVG, DEF_AVG).status == "pass"


def test_aggregation_unread_on_kind_absent_path():
    # mutating `aggregation` on a kind-absent ratio contract must NOT change the
    # verdict -- proves the base branch is the ONLY new reader of `aggregation`.
    import copy

    mutated = copy.deepcopy(DEF_DISCOUNTED)
    mutated["denominator"]["aggregation"] = "this_value_is_never_read"
    before = check_measure_drift(DAX_DISCOUNTED, DEF_DISCOUNTED)
    after = check_measure_drift(DAX_DISCOUNTED, mutated)
    assert before == after
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_metric_drift.py -k base -v`
Expected: FAIL — base cases return `escalate`/`skip` (the `kind` branch does not exist yet); regression tests PASS already.

- [ ] **Step 3: Write minimal implementation**

```python
# in src/seshat/metric_drift.py

# add to the TOP of check_measure_drift, before the existing `if not definition...`:
def check_measure_drift(dax_expr: str, definition: dict[str, Any] | None) -> Verdict:
    """... (existing docstring; append:) If definition.kind == "base", verify the
    base measure's aggregation + filter-set against its own contract."""
    if definition and definition.get("kind") == "base":
        return _check_base_drift(dax_expr, definition)
    # ----- existing ratio path BELOW, UNCHANGED -----
    if not definition or "denominator" not in definition:
        return Verdict("skip", "contract has no structured `definition.denominator`")
    # ... rest unchanged ...
```

```python
# add this new function near the other helpers in metric_drift.py

# AGG name -> the single DAX function the generator emits for it (mirror of dax_gen)
_BASE_AGG_FUNC = {
    "sum": "SUM",
    "count": "COUNT",
    "distinct_count": "DISTINCTCOUNT",
    "average": "AVERAGE",
    "count_rows": "COUNTROWS",
}


def _check_base_drift(dax_expr: str, definition: dict[str, Any]) -> Verdict:
    """Verify a kind:base measure's aggregation + filter-set vs its contract.

    Recognizes exactly two shapes (mirroring the generator's emit templates):
      AGG( <col-or-table> )                          -> no filter
      CALCULATE( AGG( <col-or-table> ), p1, p2, ... ) -> wrapped + filters
    ESCALATE for anything else; never guesses. The base measure is its OWN
    contract, so its aggregation IS checked (unlike a referenced measure).
    """
    expr = dax_expr.strip()
    agg = definition.get("aggregation")
    want_func = _BASE_AGG_FUNC.get(agg) if agg else None
    if want_func is None:
        return Verdict("escalate", f"contract aggregation {agg!r} not recognized")

    # _contract_filters reads side["filter"]; wrap the base filter list in that shape.
    contract_filters = _contract_filters({"filter": definition.get("filter", [])})
    if contract_filters is None:
        return Verdict("escalate", "contract filter is malformed or uses an unknown op")

    inner = _outer_call(expr, "CALCULATE")
    if inner is None:
        # bare aggregation, no filter
        if not _is_agg_call(expr, want_func):
            return Verdict("escalate", "measure is not a recognized AGG(col) shape")
        dax_filters: frozenset[Filter] = frozenset()
    else:
        parts = _split_balanced(inner)
        if parts is None or not parts:
            return Verdict("escalate", "CALCULATE arguments unbalanced")
        if not _is_agg_call(parts[0].strip(), want_func):
            return Verdict("escalate", "CALCULATE inner is not a recognized AGG(col)")
        recognized: set[Filter] = set()
        for p in (x for x in parts[1:] if x.strip()):
            f = _recognize_filter(p)
            if f is None:
                return Verdict("escalate", f"unrecognized predicate: {p!r}")
            recognized.add(f)
        dax_filters = frozenset(recognized)

    if dax_filters == contract_filters:
        return Verdict("pass", "base aggregation + filter-set matches the contract")
    return Verdict(
        "drift",
        f"filter-set {sorted((f.column, f.op) for f in dax_filters)} "
        f"!= contract {sorted((f.column, f.op) for f in contract_filters)}",
    )


def _is_agg_call(expr: str, func: str) -> bool:
    """True if `expr` is exactly `FUNC( ... )` at the top level (paren-balanced)."""
    return _outer_call(expr, func) is not None
```

> Implementation note for the worker: `test_base_drift_wrong_aggregation` expects **`drift`** (not `escalate`) when the DAX uses a *different but known* aggregation (e.g. `COUNT` where the contract wants `SUM`). The skeleton above would return `escalate` (because `_is_agg_call(expr, want_func)` is False). So add a pre-check BEFORE the escalate path: if `expr` (or the CALCULATE inner) is a recognized `AGG(...)` whose function is some *other* `_BASE_AGG_FUNC` value ≠ `want_func`, return `Verdict("drift", ...)`. An expression that is no recognized aggregation at all (e.g. `SUMX(...)`) still → `escalate`. Implement to satisfy the tests exactly as written.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_metric_drift.py -v`
Expected: PASS — all new base cases + both regression tests + ALL pre-existing tests green.

- [ ] **Step 5: Commit**

```bash
git add src/seshat/metric_drift.py tests/unit/test_metric_drift.py
git commit --no-gpg-sign -m "feat: kind:base verify branch in check_measure_drift (additive, zero-regression)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Ratio-measure shape validation + DAX emit

**Files:**
- Modify: `src/seshat/dax_gen.py`
- Test: `tests/unit/test_dax_gen.py`

**Interfaces:**
- Consumes: `_emit_base` internals (`_AGG_TO_DAX`, `_qualify`, `_OP_TO_DAX`) from Task 2.
- Produces: `_emit_side(side: dict) -> tuple[str | None, str | None]` (an inline aggregation, reusing base-emit logic) and `_emit_ratio(defn: dict) -> tuple[str | None, str | None]` → `DIVIDE(num, den)` or a refusal.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/unit/test_dax_gen.py
from retail.dax_gen import _emit_ratio


def test_emit_ratio_inline_count_rows():
    dax, reason = _emit_ratio({
        "kind": "ratio",
        "numerator": {"aggregation": "count_rows",
                      "source": {"table": "gold.fct_sales_rss"},
                      "filter": [{"column": "discount_applied", "op": "is_true"}]},
        "denominator": {"aggregation": "count_rows",
                        "source": {"table": "gold.fct_sales_rss"},
                        "filter": [{"column": "discount_applied", "op": "is_not_null"}]},
    })
    assert reason is None
    assert dax == (
        "DIVIDE("
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE()), "
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "NOT(ISBLANK('gold fct_sales_rss'[discount_applied]))))"
    )


def test_emit_ratio_refuses_bad_side():
    dax, reason = _emit_ratio({
        "kind": "ratio",
        "numerator": {"aggregation": "sum", "source": {"table": "gold.t"}},  # no column
        "denominator": {"aggregation": "count_rows", "source": {"table": "gold.t"}},
    })
    assert dax is None
    assert "column" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -k emit_ratio -v`
Expected: FAIL — `ImportError: cannot import name '_emit_ratio'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/seshat/dax_gen.py

def _emit_side(side: dict) -> tuple[str | None, str | None]:
    """A ratio side is an inline aggregation -- identical rules to a base body."""
    return _emit_base(side)  # same shape/validation; returns (dax, reason)


def _emit_ratio(defn: dict) -> tuple[str | None, str | None]:
    num = defn.get("numerator")
    den = defn.get("denominator")
    if not isinstance(num, dict) or not isinstance(den, dict):
        return None, "ratio requires numerator and denominator objects"
    num_dax, num_reason = _emit_side(num)
    if num_reason is not None:
        return None, f"numerator: {num_reason}"
    den_dax, den_reason = _emit_side(den)
    if den_reason is not None:
        return None, f"denominator: {den_reason}"
    return f"DIVIDE({num_dax}, {den_dax})", None
```

> If `_emit_predicate` (Task 2) is now unused, delete it in this commit (YAGNI).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py -k emit_ratio -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dax_gen.py tests/unit/test_dax_gen.py
git commit --no-gpg-sign -m "feat: ratio-measure shape validation + DAX emit

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: TMDL block builder + the full `generate_measure` pipeline (round-trip)

**Files:**
- Modify: `src/seshat/dax_gen.py`
- Test: `tests/unit/test_dax_gen.py`

**Interfaces:**
- Consumes: `_emit_base`, `_emit_ratio`, `GenResult`; `metric_drift.check_measure_drift` (lazy import inside the function); the D-rules + `RuleContext` (lazy import).
- Produces:
  - `_build_tmdl_block(name, dax, format_string, display_folder, doc_intent) -> str` — a TMDL measure block with `///` doc line, `measure Name = <dax>`, `formatString`, `displayFolder`.
  - `_run_d_rules(tmdl_block, name) -> tuple[list[str], list[str]]` — stage the block under a temp SemanticModel path, build a `RuleContext`, run D1–D11; return `(errors, warnings)` as formatted strings.
  - `generate_measure(definition, *, name, format_string=None, display_folder=None, doc_intent=None) -> GenResult` — the 4-step fail-closed pipeline.

- [ ] **Step 1: Write the failing test (the round-trip property)**

```python
# append to tests/unit/test_dax_gen.py
from retail.dax_gen import generate_measure
from retail.metric_drift import check_measure_drift

BASE_REVENUE = {
    "kind": "base", "aggregation": "sum",
    "source": {"table": "gold.fct_sales_rss", "column": "total_spent"},
}
RATIO_DISC = {
    "kind": "ratio",
    "numerator": {"aggregation": "count_rows", "source": {"table": "gold.fct_sales_rss"},
                  "filter": [{"column": "discount_applied", "op": "is_true"}]},
    "denominator": {"aggregation": "count_rows", "source": {"table": "gold.fct_sales_rss"},
                    "filter": [{"column": "discount_applied", "op": "is_not_null"}]},
}


@pytest.mark.parametrize("name,defn", [
    ("TotalRevenue", BASE_REVENUE),
    ("DiscountedRate", RATIO_DISC),
])
def test_generate_roundtrips_to_pass(name, defn):
    r = generate_measure(defn, name=name, doc_intent="meaning of the measure")
    assert r.ok is True, r.reason
    # THE CORE PROPERTY: the emitted DAX re-verifies as pass against the same contract
    assert check_measure_drift(r.dax, defn).status == "pass"


def test_generated_tmdl_passes_d_rules():
    r = generate_measure(BASE_REVENUE, name="TotalRevenue", doc_intent="total money")
    assert r.ok is True
    # PascalCase name (D1), has displayFolder (D2), has /// doc (D11), uses DIVIDE not / where relevant
    assert "/// " in r.tmdl_block
    assert "displayFolder" in r.tmdl_block
    assert "measure TotalRevenue" in r.tmdl_block


def test_generate_refuses_unknown_kind():
    r = generate_measure({"kind": "wormhole"}, name="X")
    assert r.ok is False
    assert r.dax is None and r.tmdl_block is None
    assert "kind" in r.reason


def test_generate_refuses_bad_pascalcase_name():
    r = generate_measure(BASE_REVENUE, name="total_revenue")  # D1 ERROR
    assert r.ok is False
    assert r.dax is None and r.tmdl_block is None


def test_doc_intent_isolation_same_dax_diff_comment():
    a = generate_measure(BASE_REVENUE, name="Rev", doc_intent="intent A")
    b = generate_measure(BASE_REVENUE, name="Rev", doc_intent="intent B")
    assert a.dax == b.dax                     # identical semantics
    assert a.tmdl_block != b.tmdl_block       # differ only in the /// comment
    assert "intent A" in a.tmdl_block and "intent B" in b.tmdl_block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -k "generate or doc_intent" -v`
Expected: FAIL — `ImportError: cannot import name 'generate_measure'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/seshat/dax_gen.py

_DEFAULT_FORMATS = {  # presentation default by aggregation/kind
    "sum": "#,0", "count": "#,0", "distinct_count": "#,0",
    "average": "#,0.00", "count_rows": "#,0", "ratio": "0.0%",
}


def _default_format(definition: dict) -> str:
    if definition.get("kind") == "ratio":
        return _DEFAULT_FORMATS["ratio"]
    return _DEFAULT_FORMATS.get(definition.get("aggregation"), "#,0")


def _build_tmdl_block(
    name: str, dax: str, format_string: str, display_folder: str, doc_intent: str
) -> str:
    """A TMDL measure block. /// doc is documentation only (from doc_intent)."""
    doc = (doc_intent or name).replace("\n", " ").strip()
    return (
        f"/// {doc}\n"
        f"measure {name} = {dax}\n"
        f"\tformatString: {format_string}\n"
        f'\tdisplayFolder: {display_folder}\n'
    )


def _run_d_rules(tmdl_block: str, name: str) -> tuple[list[str], list[str]]:
    """Stage the block under a temp SemanticModel path and run D1-D11."""
    import tempfile
    from pathlib import Path

    from .core import RuleContext, Severity
    from .runner import _format  # "[sev] id msg (loc)"
    from . import rules as _rules_pkg  # noqa: F401  fire @register
    from .registry import all_rules

    # A minimal TMDL table wrapper so parse_tmdl finds the measure.
    table_text = f"table T\n\tmeasure stub = 0\n\n{_indent_measure(tmdl_block)}"
    errors: list[str] = []
    warnings: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rel = "Model.SemanticModel/definition/tables/T.tmdl"
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(table_text, encoding="utf-8")
        ctx = RuleContext(repo_root=root, tracked_files=(rel,))
        for reg in all_rules():
            if not reg.id.startswith("D"):
                continue
            for f in reg.rule(ctx):
                line = _format(f)
                (errors if f.severity is Severity.ERROR else warnings).append(line)
    return errors, warnings


def _indent_measure(block: str) -> str:
    """Indent a measure block one tab so it nests under `table T`."""
    return "\n".join(("\t" + ln if ln.strip() else ln) for ln in block.splitlines())


def generate_measure(
    definition: dict,
    *,
    name: str,
    format_string: str | None = None,
    display_folder: str | None = None,
    doc_intent: str | None = None,
) -> GenResult:
    """Contract definition -> verified DAX measure. Fail-closed at every step."""
    if not name:
        raise ValueError("generate_measure requires a measure name")

    # STEP 1+2: validate shape + emit DAX
    kind = definition.get("kind") if isinstance(definition, dict) else None
    if kind == "base":
        dax, reason = _emit_base(definition)
    elif kind == "ratio":
        dax, reason = _emit_ratio(definition)
    else:
        return GenResult.refuse(f"unsupported kind {kind!r} (expected base|ratio)")
    if reason is not None:
        return GenResult.refuse(reason)

    # STEP 3: semantic verify (L3) -- BEFORE form. pass is the only acceptable result.
    from .metric_drift import check_measure_drift

    v = check_measure_drift(dax, definition)
    if v.status != "pass":
        return GenResult.refuse(f"L3 {v.status}: {v.detail}")

    # STEP 4: build TMDL block + form verify (D1-D11)
    fmt = format_string or _default_format(definition)
    folder = display_folder or "Measures"
    block = _build_tmdl_block(name, dax, fmt, folder, doc_intent or "")
    errors, warnings = _run_d_rules(block, name)
    if errors:
        return GenResult.refuse("D-rule ERROR(s): " + "; ".join(errors))
    return GenResult.success(dax=dax, tmdl_block=block, warnings=tuple(warnings))
```

> Worker note (verified): `runner._format(finding) -> str` (`src/seshat/runner.py:60`) and `registry.all_rules() -> tuple[RegisteredRule, ...]` (`src/seshat/registry.py:18`) both exist with these exact signatures. `_format` emits `"[sev] id msg (loc)"`. The temp-TMDL wrapper must parse under `parse_tmdl`; if D2/D11 need specific structure, adjust `_build_tmdl_block` until `test_generated_tmdl_passes_d_rules` is green. The D-rule iteration filters `reg.id.startswith("D")` — confirm whether C1 should also run (it scans `.pbir`/M sources, not measure blocks, so it is correctly excluded).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py -v`
Expected: PASS — round-trip (both params), D-rule cleanliness, refusals, doc_intent isolation.

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dax_gen.py tests/unit/test_dax_gen.py
git commit --no-gpg-sign -m "feat: generate_measure pipeline + TMDL builder + round-trip property

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `load_contract` (lazy yaml) + stdlib-only import guard

**Files:**
- Modify: `src/seshat/dax_gen.py`
- Test: `tests/unit/test_dax_gen.py` (loader); `tests/unit/test_metric_drift.py` (extend the existing stdlib guard)

**Interfaces:**
- Produces: `load_contract(path: str) -> dict` — returns the whole parsed contract (caller reads `definition`/`name`/`formula_intent`). Lazy `import yaml` inside.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/unit/test_dax_gen.py
import subprocess
import sys
from pathlib import Path

from retail.dax_gen import load_contract


def test_load_contract_reads_definition(tmp_path: Path):
    p = tmp_path / "c.yaml"
    p.write_text(
        'name: "Rev"\nformula_intent: "money"\n'
        "definition:\n  kind: base\n  aggregation: sum\n"
        "  source:\n    table: gold.t\n    column: c\n",
        encoding="utf-8",
    )
    data = load_contract(str(p))
    assert data["name"] == "Rev"
    assert data["definition"]["kind"] == "base"


def test_dax_gen_import_is_stdlib_only():
    # importing dax_gen must NOT pull yaml at import time (lazy in load_contract)
    code = (
        "import sys; import retail.dax_gen; "
        "assert 'yaml' not in sys.modules, 'yaml imported at module scope'"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
```

```python
# append to tests/unit/test_metric_drift.py  (extend the core-chain guard)
import subprocess
import sys


def test_retail_rules_pulls_neither_dax_gen_nor_yaml():
    code = (
        "import sys; import retail.rules; "
        "assert 'retail.dax_gen' not in sys.modules, 'dax_gen leaked into core'; "
        "assert 'yaml' not in sys.modules, 'yaml leaked into core'"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -k "load_contract or stdlib" tests/unit/test_metric_drift.py -k "pulls_neither" -v`
Expected: FAIL — `ImportError: cannot import name 'load_contract'` (loader test); the core-chain guard may already pass (dax_gen not yet imported anywhere) — keep it as a regression lock.

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/seshat/dax_gen.py
def load_contract(path: str) -> dict:
    """Read a metric contract YAML and return the whole parsed mapping.

    Lazy `import yaml` (dev/optional dep) -- the ONLY yaml touch in this module,
    kept out of the `retail check` core chain (the stdlib-only invariant).
    """
    from pathlib import Path

    import yaml  # lazy

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"contract {path} is not a YAML mapping")
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py tests/unit/test_metric_drift.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/dax_gen.py tests/unit/test_dax_gen.py tests/unit/test_metric_drift.py
git commit --no-gpg-sign -m "feat: load_contract (lazy yaml) + stdlib-only import guards

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `retail generate` CLI subcommand (stdout-verified-only, never-mutate-model)

**Files:**
- Modify: `src/seshat/cli.py`
- Test: `tests/unit/test_dax_gen.py`
- Create (fixtures): `tests/fixtures/contracts/base_revenue.yaml`, `tests/fixtures/contracts/ratio_disc.yaml`, `tests/fixtures/contracts/refuse_no_column.yaml`

**Interfaces:**
- Consumes: `dax_gen.load_contract`, `dax_gen.generate_measure` (lazy import in the handler).
- Produces: a `generate` subparser (`--contract` required; `--out`; `--format tmdl|json`) and `_run_generate(args) -> int` returning the exit code. Wired into `main()` dispatch.

- [ ] **Step 1: Write the failing tests + create fixtures**

Create `tests/fixtures/contracts/base_revenue.yaml`:
```yaml
name: "TotalRevenue"
formula_intent: "the total money taken across all transactions"
definition:
  kind: base
  aggregation: sum
  source:
    table: gold.fct_sales_rss
    column: total_spent
```
Create `tests/fixtures/contracts/ratio_disc.yaml`:
```yaml
name: "DiscountedRate"
formula_intent: "share of transactions that had a discount, among known-status"
definition:
  kind: ratio
  numerator:
    aggregation: count_rows
    source: {table: gold.fct_sales_rss}
    filter: [{column: discount_applied, op: is_true}]
  denominator:
    aggregation: count_rows
    source: {table: gold.fct_sales_rss}
    filter: [{column: discount_applied, op: is_not_null}]
```
Create `tests/fixtures/contracts/refuse_no_column.yaml`:
```yaml
name: "Broken"
formula_intent: "a sum with no column -> must refuse"
definition:
  kind: base
  aggregation: sum
  source: {table: gold.fct_sales_rss}
```

```python
# append to tests/unit/test_dax_gen.py
CONTRACTS = Path(__file__).parent.parent / "fixtures" / "contracts"


def _run_cli(*argv):
    return subprocess.run(
        [sys.executable, "-m", "retail.cli", *argv],
        capture_output=True, text=True,
    )


def test_cli_generate_success_stdout_tmdl():
    r = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"))
    assert r.returncode == 0
    assert "measure TotalRevenue" in r.stdout
    assert r.stderr.strip() == ""


def test_cli_generate_refusal_stdout_empty_stderr_reason():
    r = _run_cli("generate", "--contract", str(CONTRACTS / "refuse_no_column.yaml"))
    assert r.returncode == 1
    assert r.stdout.strip() == ""          # stdout = verified-only
    assert "refused" in r.stderr.lower()


def test_cli_generate_json_format():
    r = _run_cli("generate", "--contract", str(CONTRACTS / "ratio_disc.yaml"),
                 "--format", "json")
    assert r.returncode == 0
    import json
    obj = json.loads(r.stdout)
    assert obj["ok"] is True and obj["dax"].startswith("DIVIDE(")


def test_cli_out_refuses_powerbi_path(tmp_path: Path):
    # an --out resolving under powerbi/ is refused (resolved-path check)
    target = "powerbi/Model.SemanticModel/x.tmdl"
    r = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"),
                 "--out", target)
    assert r.returncode == 1
    assert "powerbi" in r.stderr.lower()


def test_cli_out_refuses_traversal_into_powerbi(tmp_path: Path):
    r = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"),
                 "--out", "../powerbi/sneak.tmdl")
    assert r.returncode == 1
    assert "powerbi" in r.stderr.lower()


def test_cli_out_writes_then_refuses_overwrite(tmp_path: Path):
    out = tmp_path / "m.tmdl"
    r1 = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"),
                  "--out", str(out))
    assert r1.returncode == 0 and out.exists()
    r2 = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"),
                  "--out", str(out))
    assert r2.returncode == 1
    assert "exist" in r2.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_dax_gen.py -k cli -v`
Expected: FAIL — `retail generate` is not a known subcommand (argparse error / nonzero with usage on stderr).

- [ ] **Step 3: Write minimal implementation**

```python
# in src/seshat/cli.py _build_parser(), add after the existing subparsers:
    gen = sub.add_parser(
        "generate",
        help="generate a verified best-practice DAX measure from a metric contract",
    )
    gen.add_argument("--contract", required=True, metavar="PATH",
                     help="metric contract YAML (reads its `definition` block)")
    gen.add_argument("--out", default=None, metavar="PATH",
                     help="write the verified TMDL block to a NEW standalone file "
                          "(never under powerbi/; refuses to overwrite)")
    gen.add_argument("--format", dest="fmt", choices=("tmdl", "json"),
                     default="tmdl", help="output format on success")
```

```python
# add the handler (lazy imports keep dax_gen/yaml out of `retail check`):
def _run_generate(args) -> int:
    import json
    from pathlib import Path

    from .dax_gen import generate_measure, load_contract

    try:
        contract = load_contract(args.contract)
    except Exception as e:  # unreadable / malformed YAML
        print(f"[error] cannot read contract: {e}", file=sys.stderr)
        return 1

    name = contract.get("name")
    if not name:
        print("[error] contract has no `name`", file=sys.stderr)
        return 1

    result = generate_measure(
        contract.get("definition") or {},
        name=name,
        doc_intent=contract.get("formula_intent"),
    )
    if not result.ok:
        print(f"[refused] {name}: {result.reason}", file=sys.stderr)
        return 1

    # --out guard: resolve first, refuse powerbi/**, refuse overwrite
    if args.out:
        out = Path(args.out).resolve()
        powerbi = (Path.cwd() / "powerbi").resolve()
        if out == powerbi or powerbi in out.parents:
            print(f"[refused] --out resolves under powerbi/: {out}", file=sys.stderr)
            return 1
        if out.exists():
            print(f"[refused] --out file already exists: {out}", file=sys.stderr)
            return 1
        out.write_text(result.tmdl_block, encoding="utf-8")
        return 0

    if args.fmt == "json":
        print(json.dumps({"ok": True, "dax": result.dax,
                          "tmdl_block": result.tmdl_block,
                          "warnings": list(result.warnings)}))
    else:
        print(result.tmdl_block)
    return 0
```

```python
# in main()/dispatch, route the new command:
    if args.command == "generate":
        return _run_generate(args)
```

> Worker note (verified): `main(argv) -> int` (`src/seshat/cli.py:90`) returns an int exit code; `__main__` does `sys.exit(main())`, and `[project.scripts]` maps `retail = "retail.cli:main"`. So `python -m seshat.cli generate ...` is the correct invocation used by `_run_cli`, and the `generate` dispatch must `return _run_generate(args)` in the same int-returning style as the existing `check`/`validate`/`semantic-check` branches.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_dax_gen.py -k cli -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/seshat/cli.py tests/unit/test_dax_gen.py tests/fixtures/contracts/
git commit --no-gpg-sign -m "feat: retail generate CLI (stdout-verified-only, never-mutate-model)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: `--out` symlink path-traversal guard (platform-safe)

**Files:**
- Test: `tests/unit/test_dax_gen.py`
- (No new source if Task 7's resolved-path check already covers symlinks — this task PROVES it and skips safely on Windows without symlink privilege.)

**Interfaces:**
- Consumes: the Task 7 CLI.

- [ ] **Step 1: Write the failing/guarding test**

```python
# append to tests/unit/test_dax_gen.py
import os


def test_cli_out_refuses_symlink_into_powerbi(tmp_path: Path):
    # a symlink whose target resolves under powerbi/ must be refused.
    # Skip ONLY the symlink case where the OS denies symlink creation
    # (Windows without privilege) -- the ../powerbi and absolute cases never skip.
    powerbi = (Path.cwd() / "powerbi")
    powerbi.mkdir(exist_ok=True)
    link = tmp_path / "link.tmdl"
    try:
        os.symlink(powerbi / "real.tmdl", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform/CI")
    r = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"),
                 "--out", str(link))
    assert r.returncode == 1
    assert "powerbi" in r.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails (or skips) appropriately**

Run: `python -m pytest tests/unit/test_dax_gen.py -k symlink -v`
Expected: PASS or SKIP. If FAIL (symlink resolved past the guard), strengthen `_run_generate`: resolve `out` with `Path(args.out).resolve(strict=False)` and also check `out.parent.resolve()` against `powerbi`.

- [ ] **Step 3: Strengthen implementation only if needed**

```python
# if the symlink test failed, in _run_generate replace the resolve line:
        out = Path(args.out).resolve(strict=False)
        powerbi = (Path.cwd() / "powerbi").resolve()
        out_parent = out.parent.resolve()
        if out == powerbi or powerbi in out.parents or powerbi in out_parent.parents \
                or out_parent == powerbi:
            print(f"[refused] --out resolves under powerbi/: {out}", file=sys.stderr)
            return 1
```

- [ ] **Step 4: Run test to verify it passes/skips**

Run: `python -m pytest tests/unit/test_dax_gen.py -k "cli or symlink" -v`
Expected: PASS/SKIP; the `../powerbi` and absolute-path cases (Task 7) still PASS.

- [ ] **Step 5: Commit**

```bash
git add src/seshat/cli.py tests/unit/test_dax_gen.py
git commit --no-gpg-sign -m "test: platform-safe symlink path-traversal guard for --out

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Document the `definition.kind` schema in the contract template (comments only)

**Files:**
- Modify: `templates/metric-contract.yaml` (COMMENTS ONLY — append a documentation block; change no placeholder values, add no real `definition`).

**Interfaces:** none (documentation).

- [ ] **Step 1: Add the documentation block**

Append to `templates/metric-contract.yaml` (after the existing content), as a comment block:
```yaml
# =============================================================================
# OPTIONAL: definition.kind (F-DAXGEN, additive) -- consumed by `retail generate`
# =============================================================================
# `formula_intent` above stays plain-language INTENT. The OPTIONAL `definition`
# block below is IMPLEMENTATION-side structure that the DAX Generator reads to
# emit + verify a measure. It is NOT required for a contract to be valid, and a
# contract WITHOUT it behaves exactly as today. Vocabulary is lowercase:
#   sum | count | distinct_count | average | count_rows   (-> DAX SUM/COUNT/
#   DISTINCTCOUNT/AVERAGE/COUNTROWS). Filters reuse the tight op whitelist
#   {is_true, is_not_null}. gold.* tables only.
#
# definition:                       # kind:base example
#   kind: base
#   aggregation: sum                # column REQUIRED (except count_rows = table only)
#   source: {table: gold.fct_x, column: amount}
#   filter: [{column: flag, op: is_true}]   # optional
#
# definition:                       # kind:ratio example (inline sides only)
#   kind: ratio
#   numerator:   {aggregation: count_rows, source: {table: gold.fct_x},
#                 filter: [{column: flag, op: is_true}]}
#   denominator: {aggregation: count_rows, source: {table: gold.fct_x},
#                 filter: [{column: flag, op: is_not_null}]}
#
# The generator REFUSES to emit anything it cannot verify (`retail generate`
# round-trips its own output through the L3 drift check + D1-D11). A contract
# with no `definition` is simply not generatable yet -- author one when ready.
# =============================================================================
```

- [ ] **Step 2: Verify the template still parses as YAML**

Run: `python -c "import yaml; yaml.safe_load(open('templates/metric-contract.yaml', encoding='utf-8').read()); print('OK')"`
Expected: `OK` (the appended block is all comments — no structural change).

- [ ] **Step 3: Commit**

```bash
git add templates/metric-contract.yaml
git commit --no-gpg-sign -m "docs: document optional definition.kind schema for retail generate (comments only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Full-suite verification + coverage gate

**Files:** none (verification only).

- [ ] **Step 1: Format + lint**

Run: `ruff format --check src/ tests/ && ruff check src/ tests/`
Expected: clean (no diffs, no lint errors). If `ruff format --check` fails, run `ruff format src/ tests/` and re-commit.

- [ ] **Step 2: Full unit suite (zero-regression proof)**

Run: `python -m pytest -m unit -q`
Expected: all pass — the pre-existing 349 tests PLUS the new `test_dax_gen.py` and extended `test_metric_drift.py`, 0 failures.

- [ ] **Step 3: Coverage on the new module**

Run: `python -m pytest -m unit --cov=retail.dax_gen --cov-report=term-missing -q`
Expected: `dax_gen.py` coverage ≥90%. If below, add targeted tests for the uncovered lines (likely error branches) — do not lower the bar.

- [ ] **Step 4: Confirm the stdlib invariant one more time**

Run: `python -c "import sys; import retail.rules; assert 'retail.dax_gen' not in sys.modules and 'yaml' not in sys.modules; print('core stays stdlib-only')"`
Expected: `core stays stdlib-only`.

- [ ] **Step 5: Final commit (if any formatting/coverage tests were added)**

```bash
git add -A
git commit --no-gpg-sign -m "test: full-suite green + dax_gen coverage gate (>=90%)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Validation Commands (summary)

| When | Command |
|------|---------|
| Per task | `python -m pytest tests/unit/test_dax_gen.py -v` (and `test_metric_drift.py` for Tasks 3, 6) |
| Lint/format | `ruff format --check src/ tests/ && ruff check src/ tests/` |
| Full regression | `python -m pytest -m unit -q` (must stay green, baseline 349 + new) |
| Coverage | `python -m pytest -m unit --cov=retail.dax_gen --cov-report=term-missing -q` (≥90%) |
| Stdlib invariant | `python -c "import sys; import retail.rules; assert 'retail.dax_gen' not in sys.modules and 'yaml' not in sys.modules"` |

## Definition of Done

- [ ] All 10 tasks committed, each green at commit time.
- [ ] `ruff format --check` + `ruff check` clean.
- [ ] `pytest -m unit` fully green (349 baseline + new, 0 failures).
- [ ] `dax_gen.py` coverage ≥90%.
- [ ] Stdlib-only invariant holds (`retail.rules` pulls in neither `dax_gen` nor `yaml`).
- [ ] Round-trip property proven for base + ratio; base verify validated by hand-authored fixtures.
- [ ] Zero-regression proven (existing ratio tests pass unchanged; `aggregation`-unread assertion green).
- [ ] No write under `powerbi/**`; `--out` refuses traversal + overwrite; stdout-verified-only across both formats.
