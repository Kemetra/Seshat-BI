# L4 Value Proxy — design

- **Date:** 2026-06-26
- **Status:** SHIPPED 2026-06-26 (autonomous run; ranked item #4 from ADR-0013 / the autopilot
  final report). Implemented as `src/seshat/value_proxy.py` (driver-free) + `retail value-check`
  CLI handler + the `DiscountedTransactionRate` contract's `expected_value` block (the
  non-vacuous wiring: owner-approved 50.37% passes, the 33.55% floor-bug fires V-L4). 27 TDD
  tests; full suite 467 passed; `retail check` adds 0 findings; `dependencies = []` unchanged.
- **Builds on:** ADR-0007 (L1–L4 governance model), `retail validate` (feature 004 — the
  live-validator precedent), `metric_drift.py` (L3 — the contract-parsing precedent), and the
  M2 design doc §B (`2026-06-26-dax-fortification-m2-design.md`, which scoped this as
  DESIGN-ONLY pending a contract-schema decision — this doc makes that decision).
- **Method:** orientation over the four existing surfaces (`cli.py`, `validate.py`,
  `metric_drift.py`, the metric contracts) → this design → advisor adjudication → TDD.

## The gap L4 closes

The governance layers prove progressively deeper properties of a measure:

| Layer | Proves | Blind to |
|-------|--------|----------|
| **L1** | DAX *parses* (form) | wrong logic |
| **L2** (D1–D11) | DAX is *best-practice* (hygiene) | wrong row-set |
| **L3** (`metric_drift`) | DAX denominator *filter-set matches the contract* (structure) | wrong **value** |
| **L4** (this) | the live DB still returns the *approved number* (value) | — |

L3 can pass while the data silently drifts: a measure can keep the exact contract-declared
filter-set yet, after a reload, return 1,400,000 instead of the approved 1,552,071.00 (rows
dropped, a join changed, a source re-stated). **L4 is the value proxy: it re-computes the
measure's aggregate against the live gold table and asserts it still equals the contract's
approved value, within tolerance.** It is the live counterpart to L3's static structural check.

## Decision: the machine-readable contract block

The contracts already record the approved value — but only in **prose**
(`TotalSales.yaml` → `readiness.evidence: "...penny-exact total_spent sum = 1,552,071.00"`).
Prose is not a deterministic check substrate (the lesson `metric_drift` already learned:
*structure, never prose* — its own scouts inverted 33.55/50.37 reading prose). So L4 adds a
**machine-readable** block under the existing `definition`:

```yaml
# Primary (robust) example — a RATIO value, stable regardless of row count:
definition:
  additive: false            # (existing L3 fields unchanged)
  # ... numerator / denominator as today ...
  expected_value:            # NEW — the L4 block (optional; absent ⇒ skip)
    value: "0.5037"          # the approved ratio (quoted ⇒ Decimal-parsed from the STRING)
    tolerance_abs: "0.0001"  # absolute tolerance (Decimal); ratios are row-count-stable
    aggregation: ratio       # ratio ⇒ recompute numerator/denominator from the existing L3 blocks
    # gold_table + columns are read from the contract's existing binds_to

# Additive example (a single-aggregate value) — note the SNAPSHOT caveat below:
definition:
  expected_value:
    value: "1552071.00"      # quoted so yaml hands us a STRING, not a fragile float
    tolerance_abs: "0.00"    # 0 ⇒ penny-exact
    aggregation: sum         # sum | count | distinct_count | count_rows | average
    column: total_spent      # the gold column to aggregate (from binds_to.columns)
    # gold_table is read from the contract's existing binds_to.gold_table
```

> **Values are quoted strings on purpose.** `yaml.safe_load` parses an unquoted
> `1552071.00` to a binary **float**, which cannot represent every penny exactly. Quoting
> forces a string; L4 then `Decimal`-parses it (the same `Decimal(str(x))` discipline
> `validate.py` uses for reconciliation), so the penny comparison is exact.

> **`expected_value` on an ADDITIVE measure is a point-in-time SNAPSHOT assertion.** A
> `tolerance_abs: 0` sum holds only while the dataset is frozen; it will (correctly) fire
> the instant the source grows more rows. That is fine for a frozen reconciled dataset
> (this repo's gold is penny-reconciled and static), but the row-count-stable RATIO is the
> better default demonstration. The growing-source answer is relative/percent tolerance —
> listed under YAGNI-excluded for v1.

- **Optional & backward-compatible:** a contract with no `expected_value` block ⇒ `skip`
  (exactly like L3 skips a contract with no `denominator`). No existing contract changes
  behavior; L4 only activates where an owner has recorded an expected value.
- **`aggregation` reuses the L3 vocabulary** (`sum`/`count`/`distinct_count`/`average`/
  `count_rows`, mirroring `metric_drift._BASE_AGG_FUNC`) — one source of truth for agg names.
- **`tolerance_abs`** is an *absolute* tolerance (a Decimal). `0` means penny-exact. Only
  absolute tolerance in v1 — relative/percent tolerance is YAGNI until a contract needs it.

## Architecture — mirror `validate.py` exactly (the "breaks headless" objection dissolved)

The M2 judge marked L4 DESIGN-ONLY partly because it "needs psycopg2 + live DB; breaks
headless." The `validate.py` precedent shows the resolution: **the module is driver-free.**

```
src/seshat/value_proxy.py            # NEW — stdlib-only at import time, driver-free
  @dataclass(frozen=True) ExpectedValue(value, tolerance_abs, aggregation, column, gold_table)
  parse_expected_value(definition, binds_to) -> ExpectedValue | None   # pure; None ⇒ skip
  check_expected_value(runner: QueryRunner, name, expected) -> list[Finding]   # pure
        # builds SELECT <AGG>(<col>) FROM <gold_table>, compares |actual - value| <= tol
  # reuses retail.validate.QueryRunner (the Protocol) + retail.identifiers quoting

src/seshat/cli.py                    # NEW subcommand `value-check` (mirrors `validate`)
  _run_value_check(args):
    - resolve_dsn (reused from validate) ; lazy _ensure_driver ; lazy _make_runner
    - load contracts from --metrics-dir (reuse the semantic-check discovery + confinement)
    - for each contract with an expected_value block: recompute, compare, emit Finding
    - deferred mode (no DSN / no driver) ⇒ clear actionable message, return 1 (like validate)
```

- **`value_proxy.py` imports NO driver** — it runs against the `QueryRunner` Protocol
  (reused from `validate.py`), so `retail check` and CI never load psycopg2. The
  `dependencies = []` core invariant is untouched. Tests inject a fake runner; the real
  psycopg2 runner is the *same* `make_psycopg2_runner` the validate path already builds.
- **Not a static rule, not a readiness stage:** `value-check` is a live subcommand like
  `validate`/`semantic-check` — it never runs in the `retail check` gate, adds no rule to the
  31-rule registry, and moves no readiness stage. (ADR-0013 rubric; hard rules #8/#9.)
- **SQL safety:** identifiers (table, column) are quoted via the existing
  `retail.identifiers.quote_identifier` / `quote_qualified_identifier` — the same hardened
  path `validate.py` uses. No string-formatted user values into SQL beyond quoted identifiers
  (the aggregation is chosen from a fixed whitelist, never interpolated from contract text).

## Findings & severity

| Outcome | Severity | rule_id | Meaning |
|---------|----------|---------|---------|
| live aggregate within tolerance of contract value | (none) | — | pass; no finding |
| live aggregate **outside** tolerance | **ERROR** | `V-L4` | a real value regression — the approved number no longer holds (like `validate`'s penny-mismatch ERROR) |
| live query returns no rows / NULL / unparseable | **ERROR** | `V-L4` | cannot compute the value — treated as a defect, not a pass |
| contract has no `expected_value` block | (skip) | — | nothing to check (no finding, logged) |
| malformed `expected_value` (bad agg, missing column) | **ERROR** | `V-L4` | fail-closed — a malformed check is a defect, never a silent skip |

Severity rationale mirrors `validate.py`: a *proven* value defect is ERROR (it blocks),
unlike the static L1–L2 WARNINGs which flag *suspect* patterns.

## Authority boundary (unchanged)

L4 is an **advisory engine behind the live gate**: it re-computes and compares, it does NOT
approve. A passing L4 does not move Semantic Model Ready to `pass` (a named human does, per
ADR-0008 / Principle V). A failing L4 surfaces a regression for a human to act on; it never
edits the model or the contract. No numeric *confidence score* is emitted (hard rule #9) —
only a deterministic within/outside-tolerance verdict.

## What this design deliberately excludes (YAGNI)

- **Relative/percent tolerance** — absolute only in v1; add when a contract needs it.
- **Per-side numerator/denominator value assertions** — v1's `aggregation: ratio`
  recomputes the *overall* ratio (numerator-count / denominator-count from the existing L3
  `numerator`/`denominator` filter blocks) and compares it to one `value`. Asserting the
  numerator and denominator *each* against their own expected value separately is a
  follow-up; v1 checks the single ratio result.
- **A `source-map`-driven multi-table sweep** — v1 iterates metric contracts (which already
  name their `gold_table`), reusing the semantic-check discovery, not the validate
  source-map loader.
- **Auto-updating the contract value** — L4 only *checks*; it never writes the approved
  number (that is a human/contract-authoring action).

## Test plan (TDD — RED first)

- `parse_expected_value`: present block ⇒ `ExpectedValue`; absent ⇒ `None` (skip); malformed
  (bad agg, missing column, non-numeric value) ⇒ raises/None routed to an ERROR.
- `check_expected_value` against a **fake `QueryRunner`**: exact match ⇒ no finding; within
  tolerance ⇒ no finding; outside tolerance ⇒ one `V-L4` ERROR with the gap; no-rows/NULL ⇒
  ERROR; tolerance boundary (|gap| == tolerance) ⇒ pass (inclusive).
- SQL shape: the built SQL aggregates the quoted column from the quoted gold table (assert
  via the fake runner capturing the SQL).
- CLI `value-check`: no DSN ⇒ actionable error + return 1 (no connect); driver missing ⇒
  install hint + return 1; a fake runner path proves a mismatch returns 1 and a match
  returns 0. **No real DB is touched in the suite** (same discipline as the validate tests).
- Core invariants: `value_proxy.py` import pulls no driver; `dependencies = []` unchanged;
  31-rule registry unchanged; `retail check` unaffected.
