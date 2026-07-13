# DAX Engine Internals — Deep Dive

> *Why* DAX is fast or slow. This file gives the agent the mental model of the engine so it can
> explain a performance finding and choose between equivalent formulations — not just apply a
> rule. It is the "why" behind `dax-performance-notes.md` (the primer) and feeds the playbooks in
> `dax-performance-diagnostics.md`. Examples use the reference retail schema. Original teaching
> material; distilled from Definitive Guide Ch 17–19 (concepts only) — no book text, query plans,
> or sample model reproduced. For hands-on plan capture, use DAX Studio against your own model.

Concept cards in this file: **CC-013 (Storage vs Formula Engine + callbacks), CC-014 (VertiPaq
compression & cardinality).**

---

## CC-013 — Storage Engine vs Formula Engine (and CallbackDataID)

**What they are.** A DAX query is executed by two cooperating engines:

- **Storage Engine (SE / VertiPaq, or DirectQuery to a source).** Columnar, compressed,
  multi-threaded, cache-friendly. It performs fast scans, simple filters, and basic aggregations
  (sum, count, min/max, group-by). It speaks an internal query language (often shown as *xmSQL* in
  tools). It does **not** understand complex DAX logic.
- **Formula Engine (FE).** Single-threaded, no cache of its own (relies on the SE cache). It
  handles everything the SE cannot: complex expressions, iteration that can't be pushed down,
  control flow, and orchestration of context transitions. It requests data from the SE and
  combines it.

**The cooperation.** The FE asks the SE for "datacaches" (small result sets), then finishes the
computation. The fastest queries push almost all work into the SE and leave the FE little to do.

**CallbackDataID — the smell to watch.** When a piece of FE logic must be evaluated *per row
during an SE scan*, the SE "calls back" into the FE row by row. In a query plan this appears as a
`CallbackDataID`. Callbacks defeat the SE's speed advantage: the multi-threaded scan keeps pausing
to ask the single-threaded FE for an answer. A few are fine; many in a hot path is a red flag.

**Why it matters.** This is the single lens for *all* performance diagnosis: *"Is the time in the
SE or the FE, and are there callbacks?"* Optimization is mostly "move work from FE to SE" and
"remove callbacks."

**What pushes work to the (fast) SE.**
- Simple column aggregations: `SUM`, `COUNTROWS`, `MIN`, `MAX`, group-by on columns.
- Straight column filters (predicate filters), not `FILTER` over whole tables.
- Clean row expressions in iterators (`SUMX('Sales', qty*price)`).

**What forces the (slower) FE / callbacks.**
- Calling a measure inside an iterator (context transition per row — CC-003).
- Complex `IF`/`SWITCH` logic evaluated per row inside a scan.
- Functions the SE can't handle inline, forcing per-row callbacks.
- `FILTER` over a large table materialized in the FE.

**Common mistake.** Optimizing blind — rewriting formulas by guesswork without first checking
whether time is spent in the SE or FE. You can make a measure "cleverer" and slower.

**Retail example (conceptual).**
```dax
-- FE-heavy: per-row IF that calls a measure forces callbacks during the scan
High Margin Sales (slow) :=
SUMX ( 'Sales', IF ( [Margin %] > 0.3, 'Sales'[Quantity] * 'Sales'[Net Price] ) )

-- SE-friendly: push the arithmetic into a clean row expression; filter with a predicate
High Margin Sales (faster) :=
CALCULATE (
    SUMX ( 'Sales', 'Sales'[Quantity] * 'Sales'[Net Price] ),
    'Product'[Brand] IN VALUES ( 'Product'[Brand] )      -- example column filter; adjust to the real condition
)
```
The first calls a measure (`[Margin %]`) per fact row → context transition + callbacks. Restructure
so the condition is a column filter and the inner expression is pure column math.

**Analyzer candidate.** ARC-PERF-04 — per-row IF/measure inside an iterator forces callbacks
(needs query-plan input; `analyzer_v2`).

**Phases.** human guidance (analyzer_v2 once plan input is available).

---

## CC-014 — VertiPaq compression & cardinality

**What it is.** VertiPaq stores each **column** separately and compresses it. The dominant factor
in both **model size** and **scan speed** is **cardinality** — the number of *distinct values* in a
column. Fewer distinct values → better compression → smaller, faster scans.

**Why it matters.** It explains the recurring advice "split datetime," "reduce precision," "use
integer surrogate keys," and "drop unused columns." Model design decisions made here pay off in
every query.

**Deeper behavior.**
- Compression techniques (value/dictionary/run-length encoding) all degrade as distinct values
  rise. A near-unique column barely compresses.
- **Datetime is the classic offender:** a full-precision datetime column is almost unique → split
  into a `Date` column and (if needed) a `Time` column, or drop the time part.
- High-precision decimals add cardinality; round when the business allows.
- Relationship and filter columns should be low-cardinality integers where possible (surrogate
  keys beat long text keys).
- Unused columns still occupy memory — remove them from the model, not just from visuals.
- **`DISTINCTCOUNT` internals:** distinct counting is heavier than summing because the SE must
  track unique values; its cost scales with the cardinality of the counted column and the shape of
  the surrounding filter. "Related distinct count" across relationships is especially sensitive —
  test alternatives (bridge vs `TREATAS`) on real data.

**Cache & parallelism (brief).** The SE caches datacaches within and across queries; identical
sub-scans can hit the cache. SE scans are parallelized across segments; FE work is not. Don't
write formulas that needlessly vary filters and defeat the cache.

**Common mistake.** Storing a high-cardinality calculated column (a concatenated business key, a
full-precision timestamp) and then wondering why the model is huge and slow.

**Retail example.**
```text
'Sales'[OrderDateTime]  (1.6M distinct values)   → poor compression, large column
    split into:
'Sales'[OrderDate]      (~3,650 distinct values)  → compresses well, supports the Date relationship
'Sales'[OrderTime]      (~86,400 distinct, optional / drop if unused)
```

**Analyzer candidate.** ARC-MODEL-02 — high-cardinality calculated column (needs model metadata;
extends AR-PERF-004). Already staged.

**Phases.** model_review, analyzer (with model metadata).

---

## How internals map to the levers you can pull

| You observe… | Engine reason | Lever (see playbooks) |
|---|---|---|
| Slow measure over big fact | measure iterated at fact grain → transitions/callbacks (CC-013) | iterate dimension / column math |
| High FE %, many CallbackDataIDs | logic not pushed to SE (CC-013) | simplify filter, remove per-row IF/measure |
| Huge model / slow scans | high-cardinality columns (CC-014) | split datetime, reduce precision, drop columns |
| Slow distinct count | DISTINCTCOUNT + complex filter (CC-014) | reduce cardinality; test bridge vs TREATAS |
| Fast-but-wrong vs slow-but-right | over-aggressive ALL / missing KEEPFILTERS | fix correctness first, then optimize |

---

## Agent reasoning questions (Slice 3 — engine internals)

1. *"A measure is slow; the plan shows mostly SE time and no callbacks. Rewrite the DAX?"*
   → Time is already in the fast engine. **Likely a cardinality/volume issue, not formula logic —
   look at the model (CC-014), not a DAX rewrite.**
2. *"Many CallbackDataIDs appear. What category of cause?"*
   → FE logic running per row during the scan. **Per-row IF/measure inside an iterator; simplify or
   hoist (CC-013).** Candidate ARC-PERF-04.
3. *"Model is 4 GB for ~10M fact rows. First thing to inspect?"*
   → Cardinality dominates size. **Find the highest-cardinality columns (datetime, keys); split or
   drop (CC-014).** Candidate ARC-MODEL-02.
4. *"`DISTINCTCOUNT` of customers is slow. Options?"*
   → It's inherently heavier than SUM and filter-shape sensitive. **Reduce key cardinality; test
   bridge vs TREATAS propagation on real data (CC-014).**

---

## Links — companion files

- `dax-performance-diagnostics.md` (this slice) — the triage workflow and 8 playbooks that operate
  on these concepts.
- `dax-performance-notes.md` — the introductory primer (levers, rules of thumb); this file is its
  "why."
- `dax-evaluation-context-deep-dive.md` — CC-003 context transition, the cost of which is explained
  here.
- `patterns/analyzer-rule-candidates.json` — ARC-PERF-04 (callbacks) to be staged with this slice.
