# 0007 -- Layered DAX governance; the contract<->DAX drift check is a SKILL layer, not a static rule

- **Date:** 2026-06-25
- **Status:** Accepted (L2 adapter is a separate spike, F038; L1/L4 deferred)

> **Addendum (2026-06-26, F040 DAX Fortification):** Since this ADR was written,
> L2 was extended with home-grown lexical rules **D9, D10, D11** (date literals,
> FILTER(ALL) anti-pattern, measure docs), and **L3 was promoted to a CI gate** via
> the `retail semantic-check` subcommand (drift=ERROR, escalate=WARNING). The
> registry is now **31 rules** (not 28). The decision below to keep L3 OUT of the
> registered `retail check` chain still holds — `semantic-check` is a separate
> subcommand + lazy module, never a `D9` rule. References to "28 rules" / "no D9"
> in the body are the historical state at authoring time; current count is 31.
- **Context:** DAX is the analytical backbone -- the number a business user reads --
  and it was the LEAST-governed layer. `retail check` (D1-D8) proves DAX *form*
  (PascalCase, DIVIDE, display folders, no bidirectional, gold-only). `retail validate`
  (RC16) reconciles *column sums* silver<->gold. NEITHER sees a measure that is valid,
  best-practice-clean DAX yet computes the WRONG number because its denominator/filter
  logic is wrong. That gap let the `DiscountedTransactionRate` bug through (denominator
  = all transactions / 33.55% vs the approved known-status / 50.37%; see ADR-adjacent
  correction 2026-06-25). This ADR records the layered approach and the placement
  decision for the layer that closes that specific gap.

## Decision

### 1. DAX governance is LAYERED; each layer is a different engine + trust level

| Layer | Catches | Engine | Owner |
|-------|---------|--------|-------|
| L1 syntax/parse | invalid DAX (arity, parens, unknown functions) | a DAX parser | deferred (TBD) |
| L2 best-practice | the generic "hard rules of DAX" (~80 BPA rules) | **optional** Tabular Editor BPA adapter (F038) OR home-grown D-rules | external/optional |
| **L3 contract drift** | **wrong denominator/filter vs the approved contract (the 50.37 class)** | **`retail.metric_drift` + the `retail-semantic-check` skill** | **Tower BI** |
| L4 value | wrong NUMBER | SQL/DuckDB proxy vs the contract's expected value | Tower BI |

This ADR builds **L3**. L2 is the separate F038 spike (optional, proven-headless, never
a blocking core dep). L1 and L4 are deferred.

### 2. Tower BI owns business truth; external engines are advisory only

The metric **contract** is the SOLE arbiter of a measure's correct denominator/filter
direction -- never the DAX shape, never prose inference, never an external tool. (A
2026-06-25 design workflow's own scout agents INVERTED 33.55%/50.37% by reading the
prose/DAX -- proof that inference is unsafe and that a deterministic, contract-anchored
comparison is required.) Tabular Editor/BPA (F038), if ever adopted, is advisory and
generic-only; it cannot decide a contract, denominator, blank/unknown handling, or any
approval.

### 3. L3 is a SKILL-layer check (a lazy module), NOT a static `retail check` D-rule

The drift check reads the contract YAML to know the approved filter-set. A static rule
in `src/seshat/rules/dax.py` would be **eagerly imported by the `retail check` core
chain** (`retail.cli -> retail.rules -> dax`). An `import yaml` there would:

- **ImportError on a bare `dependencies = []` install** (yaml is a dev/optional dep) --
  the gate fails opaquely before any rule runs; AND
- **pass CI anyway**, because the only stdlib guard
  (`test_validate_module_stays_stdlib_only`) covered `retail.validate`, not
  `retail.core` / `retail.rules`.

That is a governance hole masquerading as green. So L3 lives in a SEPARATE lazy module,
`src/seshat/metric_drift.py`, mirroring `validate_targets.py`: `import yaml` is lazy
(inside the loader only), and the module is NEVER in the `retail check` core import
chain. The `retail-semantic-check` skill imports it lazily to render per-measure
verdicts. It is explicitly **NOT** registered as a `D9` rule and **NOT** added to
`EXPECTED_RULE_IDS` (doing so would re-create the hole).

New guards lock this in (`tests/unit/test_metric_drift.py`):
- `metric_drift` has no module-scope `import yaml` (lazy only).
- A clean subprocess `import retail.rules` pulls NEITHER `metric_drift` NOR `yaml` into
  `sys.modules` -- proving the core chain stays stdlib-only.

### 4. L3 is WARNING + ESCALATE-by-default, not a hard ERROR gate

DAX has many equivalent predicate spellings; confident parsing is where bugs are born
(cf. the S8-over-broad lesson -- an ERROR rule that false-positives blocks valid work).
So `metric_drift` recognizes a TIGHT whitelist of canonical predicates
(`NOT(ISBLANK(col))` -> `is_not_null`, `[col] = TRUE()` -> `is_true`) and **escalates
anything else** -- an unknown predicate, a non-DIVIDE measure, unbalanced parens, a
malformed contract. ESCALATE is the DEFAULT branch: never pass-on-uncertain (reopens
the false negative), never drift-on-uncertain (the false positive). The verdict is
`pass | drift | escalate | skip` (skip = the contract has no structured `definition`
yet -- backward-compatible). Whether L3 is ever PROMOTED to a CI-gated ERROR is a
deferred owner decision, not assumed here.

### 5. The structured contract `definition` block (what L3 compares against)

A metric contract MAY carry an optional, machine-readable `definition`:

```yaml
definition:
  additive: false
  numerator:   { aggregation: count_rows, filter: [{column: discount_applied, op: is_true}] }
  denominator: { aggregation: count_rows, filter: [{column: discount_applied, op: is_not_null}] }
```

L3 splits a `DIVIDE(num, den)` measure (balanced-paren), normalizes a SYNTACTIC empty
`CALCULATE([M])` to the bare ref, strips column qualification
(`'tbl'[col]` -> `col`), extracts the denominator filter-set with the recognized-op
whitelist, and asserts it equals `definition.denominator.filter`. The base measure-ref
(e.g. `[TransactionCount]`) is treated as OPAQUE -- L3 does not re-derive its
aggregation (that is the base measure's own contract's concern). Absence of the block
= `skip`, so contracts adopt it incrementally.

## Consequences

- The 50.37-vs-33.55 class is now catchable, contract-anchored, deterministically,
  with no DAX engine and no external dependency. Piloted GREEN on BOTH ratio measures
  (`DiscountedTransactionRate`, `AvgTransactionValue` -- the same-shape collision: same
  wrapped denominator, different filter column) and RED on the original all-transactions
  bug, the wrong-column denominator, and the empty-`CALCULATE()` evasion.
- The `retail check` core stays stdlib-only and unchanged (28 rules, no D9); the new
  guards prevent a future maintainer from silently reopening the hole.
- L3 under-claims by design (escalates the unrecognized) rather than over-claims -- the
  correct bias for a governance layer.

## See also

- The module + tests: `src/seshat/metric_drift.py`, `tests/unit/test_metric_drift.py`.
- The skill that surfaces it: `.claude/skills/retail-semantic-check/SKILL.md`.
- The L2 optional adapter spike: `specs/038-tabular-editor-bpa-adapter/spec.md`.
- The contract correction that motivated L3: `mappings/retail_store_sales/metrics/DiscountedTransactionRate.yaml`,
  `unresolved-questions.md` Q2.
- The stdlib precedent it mirrors: `src/seshat/validate_targets.py`; the invariant test
  it extends: `tests/unit/test_validate_targets.py::test_validate_module_stays_stdlib_only`.
