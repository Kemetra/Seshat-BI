# Aggregation and Grain at Scale

Aggregation changes grain (`PY-CN-052`); at scale it is also a shuffle, and some operations
that are trivial in pandas (exact distinct count) become expensive. Correctness rules are
borrowed; this file adds the distributed concerns. Schema:
`references/retail-bigdata-schema.md`.

---

## BD-CN-042 — Declare grain and additivity first (unchanged)

Everything from the Python layer applies: state the **target grain** as "one row per ___"
before grouping (`PY-CN-052`), classify each measure's **additivity** (`PY-CN-053`), never
sum a non-additive measure, and compute averages as weighted (`PY-CN-054`). Distribution
changes *how* the aggregation runs, never *whether* these rules hold.

## BD-CN-043 — Groupby is a shuffle; partial aggregation tames it

A distributed groupby shuffles rows so each key's rows co-locate. Good engines do
**partial (map-side) aggregation** first: each partition pre-aggregates locally, then only
the small partial results are shuffled and combined. This is why **additive** measures are
cheap at scale (sum-of-sums) and why APIs that allow a combiner are preferred over ones
that force all raw rows through the shuffle.

**Reasoning rule:** favor aggregations expressible as a combine (sum, count, min, max) over
ones that must see every row at once.

## BD-CN-044 — Additivity enables tree aggregation; non-additivity blocks it

Additive measures combine hierarchically (partition → node → global) without error.
Non-additive measures (ratios, averages, distinct counts) **cannot** be combined from
sub-results — they must be recomputed from base data at the target grain (`PY-CN-056`).
At scale this matters doubly: trying to "sum up" partial ratios is both wrong and defeats
partial aggregation.

## BD-CN-045 — Distinct count is expensive; know exact vs approximate

Exact distinct count (`nunique`, `COUNT(DISTINCT ...)`) requires gathering all distinct
values for a key — a heavy, often skewed shuffle. At scale there are two honest options:

- **Exact** — correct but costly; use when the number must reconcile precisely (financial
  counts).
- **Approximate** (e.g. HyperLogLog-based `approx_count_distinct`) — fast and
  memory-light, with a small, bounded error; use for exploration, trends, and dashboards
  that tolerate ~1–2% error.

**Best practice (BD-BP-006):** choose exact vs approximate deliberately and record which —
never silently ship an approximate count where an exact one is expected
(`validation-and-reconciliation-at-scale.md`).

## BD-CN-046 — Distinct counts are still non-additive

Whether exact or approximate, distinct counts cannot be summed across groups (`PY-CN-056`):
distinct customers in north + south ≠ total distinct customers. Compute at the target grain
from base rows. (HyperLogLog sketches *can* be merged, but that is a deliberate technique,
not naive summing.)

## BD-CN-047 — Skew hits groupby too

A skewed group key concentrates a group's rows on one task (BD-CN-037), so a heavy-hitter
key (flagship store, bot session) makes one aggregation task a straggler. The same fixes
apply: AQE, or salt the hot key and combine the partial aggregates. Additive partial
aggregation already softens groupby skew more than join skew.

## BD-CN-048 — Null group keys still drop rows (verify at scale)

Rows with a null group key are excluded from groups by default (`PY-CN-057`); at scale you
verify this with a distributed reconciliation, not a glance — the grouped additive total
must equal the ungrouped total (`PY-CN-058`). A gap means dropped null keys or upstream
fan-out.

## BD-CN-049 — Reconcile the aggregation by control total (distributed)

The conservation law (`PY-CN-058`) is the cheapest correctness test and it works at scale:
the sum of an additive measure after groupby must equal its sum before, computed as
distributed aggregates. Reconcile before handoff (`validation-and-reconciliation-at-scale.md`).

## BD-PB-004 — Playbook: sums look too big after grouping (at scale)

1. Confirm target grain declared and measure additivity classified (BD-CN-042).
2. Rule out upstream fan-out from a prior join (BD-CN-009 / `joins-and-skew.md`).
3. Confirm no non-additive measure was summed (BD-CN-044).
4. Check distinct-count semantics and exact-vs-approx choice (BD-CN-045/046).
5. Reconcile grouped total to ungrouped total (BD-CN-049).
6. Verdict on `checklists/aggregation-grain-checklist.md`.

---

### Ends on

`checklists/aggregation-grain-checklist.md` — an **aggregation-grain verdict** with the
before/after total reconciliation and the exact-vs-approximate decision recorded.
