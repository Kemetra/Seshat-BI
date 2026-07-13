# SQL Performance Notes

> Correctness-oriented performance reasoning: sargability, filter-early, SELECT *, cross joins, grain across CTEs (SC-033..038). NOT execution-plan analysis (deferred -- see `../INDEX.md`). See `../references/source-map.md`.

## Slice 6 overview -- why this matters for Seshat BI

The agent doesn't run queries, so this slice is about **reasoning**, not benchmarking: recognizing
the shapes that are predictably slow or fragile and proposing a cheaper-but-equivalent form. It also
**consolidates the anti-patterns and analyzer-rule candidates** gathered across Slices 1-5 into a
promotion-ready view. Correctness (Slices 1-5) always comes first; this slice is the "make it
predictably efficient and maintainable" layer that supports validation throughput and silver/gold
build cost.

**The one-line mental model:** *touch the fewest rows and columns needed, as early as possible, and
let the engine keep its index/scan advantages.*

---

## Concept cards (continuing SC-001...032)

### SC-033 -- Sargability (let predicates use an index)
- **Definition.** A predicate is **sargable** if the engine can use an index/zone-map to satisfy it.
  Wrapping the column in a function (`YEAR(col)`, `UPPER(col)`) or a leading-wildcard `LIKE '%x'`
  defeats this.
- **Why it matters.** Non-sargable predicates force full scans even when an index exists -- a common,
  silent slowdown the agent can flag from the SQL text alone.
- **Common failure mode.** `WHERE EXTRACT(year FROM order_date) = 2025`; `WHERE LIKE '%phone'`.
- **Diagnostic question.** *"Is the column bare on one side of the predicate, or wrapped in a
  function?"*
- **Retail example.** Sargable: `WHERE order_date >= DATE '2025-01-01' AND order_date < DATE
  '2026-01-01'` instead of `WHERE YEAR(order_date) = 2025` (links SC-024, SARC-DATE-SARG-01).
- **Feeds.** SQL-AP-035 - SARC-SARG-01.

### SC-034 -- Filter early, reduce rows before joins & aggregation
- **Definition.** Apply the most selective row filters as early as possible so joins and aggregates
  process fewer rows.
- **Why it matters.** Work scales with row volume; cutting rows up front shrinks every downstream
  step. (Optimizers often push predicates down, but explicit early filtering is clearer and
  reliable across engines.)
- **Common failure mode.** Joining large tables in full, then filtering at the end; aggregating
  everything then discarding most of it.
- **Diagnostic question.** *"Can this filter run before the join/aggregate instead of after?"*
- **Retail example.** Filter `sales` to the reporting month in a CTE before joining dimensions,
  rather than joining all history then filtering.
- **Feeds.** SQL-AP-037 - SARC-FILTER-LATE-01.

### SC-035 -- Row-store vs column-store
- **Definition.** Row-stores (OLTP) read whole rows and favor selective point lookups; column-stores
  (analytics warehouses) read only the columns referenced and excel at scanning few columns over
  many rows.
- **Why it matters.** On a column-store, selecting only needed columns is a real performance lever
  (and `SELECT *` is a real cost). The agent should reason about which engine the workload targets.
- **Common failure mode.** Treating an analytic column-store like a row-store (or vice versa); wide
  `SELECT *` on a column-store.
- **Diagnostic question.** *"Is this an analytic column-store? Then read the fewest columns and
  expect scans, not seeks."*
- **Retail example.** On a warehouse, `SELECT order_date, net_price` scans 2 columns; `SELECT *`
  scans them all -- much more I/O for the same answer.
- **Feeds.** SQL-AP-033 - SARC-SELECTSTAR-01.

### SC-036 -- Avoid SELECT * in transformations
- **Definition.** Explicitly list the columns a transformation/view produces rather than `SELECT *`.
- **Why it matters.** `SELECT *` reads/stores unneeded columns (cost), breaks when upstream schema
  changes (fragility), and obscures the output **grain and contract** of the step.
- **Common failure mode.** `CREATE VIEW ... AS SELECT * FROM ...`; `SELECT *` feeding a downstream join
  that then fans out unnoticed.
- **Diagnostic question.** *"Does this step declare exactly the columns (and grain) it outputs?"*
- **Retail example.** A silver view should `SELECT order_line_id, order_id, product_key, quantity,
  net_price` -- not `SELECT *` -- so its contract is explicit.
- **Feeds.** SQL-AP-033 - SARC-SELECTSTAR-01.

### SC-037 -- Join order & cardinality intuition
- **Definition.** The result size of a join chain is driven by cardinalities; the smallest, most
  selective sets should drive the work. Modern optimizers usually reorder joins, but they rely on
  **cardinality estimates** that bad stats or skew can mislead.
- **Why it matters.** Helps the agent predict which joins explode and reason about why a plan might
  be slow -- and reinforces verifying cardinality (SC-010) before joining.
- **Common failure mode.** Assuming join order doesn't matter at all; joining two large tables
  before filtering either.
- **Diagnostic question.** *"Which table is smallest/most selective, and does the query let it
  reduce the set early?"*
- **Retail example.** Filter `sales` to one month first, then join `product`/`store` -- far fewer
  fact rows flow into the joins.
- **Feeds.** SQL-AP-037 - SARC-FILTER-LATE-01.

### SC-038 -- Ambiguous grain across a CTE stack
- **Definition.** In a stack of CTEs, each step can change the grain (a join fans out, a GROUP BY
  collapses). If grain isn't tracked, a later step silently operates on the wrong grain.
- **Why it matters.** The most common correctness-and-readability failure in real pipeline SQL:
  five CTEs deep, nobody can say what one row means. This is where fan-out and double-counting hide.
- **Common failure mode.** CTEs named `step1`, `step2`... with no stated grain; an aggregate in CTE 4
  that's wrong because CTE 2 fanned out.
- **Diagnostic question.** *"For each CTE, can I state its grain in one sentence? Where does the
  grain change?"*
- **Retail example.** Comment each CTE: `-- grain: one row per order line`, `-- grain: one row per
  (store, day)` -- making the grain transition explicit and reviewable.
- **Feeds.** SQL-AP-036 - SARC-CTE-GRAIN-01.

---

## How to reason about a slow/fragile query (the routine)

1. **Correctness first.** Confirm grain and that no fan-out inflated the result (Slices 1-2) -- never
   optimize a wrong query.
2. **Rows: filter early.** Push the most selective predicates before joins/aggregates (SC-034).
3. **Columns: read only what's needed.** Drop `SELECT *`, especially on column-stores (SC-035/036).
4. **Predicates: keep them sargable.** Bare columns, no leading-wildcard `LIKE`, range over function
   (SC-033).
5. **Joins: reduce before combining.** Let the smallest/most selective set drive; verify cardinality
   (SC-037, SC-010).
6. **Grain: track it through the CTE stack** so optimization doesn't accidentally change results
   (SC-038).

| Symptom | Likely cause | Lever |
|---|---|---|
| Full scan despite a filter | non-sargable predicate (SC-033) | bare column + range predicate |
| Huge intermediate result | filter applied late (SC-034) | push filter before join/aggregate |
| Slow wide query on a warehouse | `SELECT *` on a column-store (SC-035/036) | select only needed columns |
| One join explodes | cardinality/skew, unfiltered large tables (SC-037) | filter early; verify keys (SC-010) |
| "Which CTE broke the number?" | untracked grain in a CTE stack (SC-038) | declare grain per CTE |

## Slice 6 mini-playbook

- **"Query is slow but correct"** -> run the routine above; biggest lever is usually rows-before-joins
  and dropping `SELECT *`.
- **"Index exists but isn't used"** -> non-sargable predicate (SC-033); unwrap the column.
- **"Can't tell if a deep query is right"** -> grain not tracked across CTEs (SC-038); annotate each.
- **Stop & note** that exact tuning (indexes, partitioning, distribution keys) is engine-specific and
  belongs to a later, engine-aware phase -- this slice is reasoning, not tuning.

## Feeds

- Concepts: SC-033...SC-038 (extend SC-010 cardinality, SC-024 sargable dates, SC-005 grain).
- Anti-patterns: SQL-AP-033...SQL-AP-037.
- Analyzer candidates: SARC-SELECTSTAR-01, SARC-CROSSJOIN-01, SARC-SARG-01, SARC-CTE-GRAIN-01,
  SARC-FILTER-LATE-01.
