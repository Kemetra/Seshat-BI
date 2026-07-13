# BI Agent Training Set

> A graded question bank for teaching and evaluating the BI agent's DAX reasoning. It turns the
> concept cards (`CC-xxx`), playbooks (`PB-xxx`), and rules (`BP/AP/AR/ARC`) into testable items.
> Each item has a **prompt**, the **expected reasoning** (the chain we want the agent to show),
> the **expected answer** (the conclusion), **concept/rule links**, and a **difficulty**. A
> machine-gradeable twin lives in `agent-training-set.json`. All examples use the reference retail
> schema (`references/retail-schema.md`). Original teaching material — no book text reproduced.

## How to use this set

- **Teaching:** have the agent read a concept file, then answer the items for that category with
  *visible reasoning*, and compare to "expected reasoning."
- **Evaluation/grading:** score each item on the rubric below. The "expected reasoning" is the
  key — a right answer for the wrong reason should not pass, because the agent must *generalize*.
- **Difficulty:** `basic` (single concept), `intermediate` (combine two), `advanced` (diagnose /
  trade-offs).

### Grading rubric (per item, 0–3)

- **3 — Full:** correct answer AND reasoning hits the key concept(s); names the right fix/rule.
- **2 — Partial:** correct answer, reasoning incomplete or missing a concept link.
- **1 — Shaky:** right instinct but wrong/garbled reasoning, or correct reasoning but wrong answer.
- **0 — Miss:** wrong answer and wrong reasoning.

A passing agent should average ≥ 2.5 overall and never score 0 on a `basic` item.

---

## Category 1 — Context reasoning

**T-CTX-01 (basic).** *In a matrix with `'Product'[Category]` on rows, what does `[Sales Amount]`
return on the "Audio" row?*
- Reasoning: the row adds a filter `'Product'[Category]="Audio"` to the filter context; the measure
  evaluates under it.
- Answer: Audio-only sales.
- Concepts: CC-001. Rules: —.

**T-CTX-02 (intermediate).** *Why does `SUMX('Sales', [Sales Amount])` differ from `SUM` and run
slowly?*
- Reasoning: referencing a measure inside the iterator triggers context transition per fact row;
  each row becomes its own filter context.
- Answer: it transitions per line — usually unintended and expensive; use column math or iterate a
  dimension.
- Concepts: CC-003. Rules: ARC-PERF-01.

**T-CTX-03 (intermediate).** *In a calculated column on `'Product'`, can a bare row context read
matching `'Sales'` rows?*
- Reasoning: a row context does not cross relationships by itself.
- Answer: no — use `RELATEDTABLE`/a measure (context transition), not the row context alone.
- Concepts: CC-002, CC-008. Rules: ARC-CTX-02.

**T-CTX-04 (intermediate).** *A `Category × Color` matrix of `[Sales Amount]` omits some pairs. Bug?*
- Reasoning: auto-exist intersects only combinations that occur in the data.
- Answer: not a bug — expected behavior.
- Concepts: CC-018. Rules: —.

**T-CTX-05 (advanced).** *You need each product's count of higher-selling products in a calculated
column, without `EARLIER`. Approach?*
- Reasoning: capture the current row's value in a `VAR`, then iterate `ALL('Product')` comparing to
  it; nested row contexts otherwise shadow each other.
- Answer: `VAR cur=[Sales Amount] RETURN COUNTROWS(FILTER(ALL('Product'),[Sales Amount]>cur))`.
- Concepts: CC-002. Rules: —.

---

## Category 2 — CALCULATE behavior

**T-CALC-01 (basic).** *Does `CALCULATE([Sales Amount], 'Date'[Year]=2025)` honor a Year slicer set
to 2024?*
- Reasoning: the predicate is `FILTER(ALL('Date'[Year]),…)`, which replaces the column's filter.
- Answer: no — it overrides to 2025.
- Concepts: CC-004, CC-005. Rules: ARC-CALC-01.

**T-CALC-02 (basic).** *Restrict to Red while keeping the user's other Color selections. How?*
- Reasoning: default filters replace; intersection requires `KEEPFILTERS`.
- Answer: `CALCULATE([Sales Amount], KEEPFILTERS('Product'[Color]="Red"))`.
- Concepts: CC-006. Rules: AR-CALC-001 / ARC-CALC-01.

**T-CALC-03 (intermediate).** *Difference between `CALCULATE([m],'Product')` and
`CALCULATE([m],'Product'[Color]="Red")`?*
- Reasoning: a table filter reapplies the whole expanded table (clears filters on every Product
  column); a column predicate touches only Color.
- Answer: the table form clears far more and is usually slower.
- Concepts: CC-005, CC-008. Rules: ARC-PERF-03.

**T-CALC-04 (intermediate).** *A measure must ignore the date but keep the Day-of-Week slicer. Is
`ALL('Date')` correct?*
- Reasoning: `ALL('Date')` clears every Date column including Day of Week.
- Answer: no — use `ALLEXCEPT('Date','Date'[Day of Week])` or `REMOVEFILTERS('Date'[Date])`.
- Concepts: CC-019. Rules: AR-ALL-001 / ARC-ALL-01.

**T-CALC-05 (intermediate).** *"Sales by delivery date" returns order-date numbers. Why and fix?*
- Reasoning: the DeliveryDate relationship is inactive; plain measures use the active one.
- Answer: `CALCULATE([Sales Amount], USERELATIONSHIP('Sales'[DeliveryDate],'Date'[Date]))`.
- Concepts: CC-016, CC-006. Rules: ARC-REL-01.

**T-CALC-06 (advanced).** *A disconnected `'Category Bucket'` table applied as a filter does
nothing. Why and fix?*
- Reasoning: it has no lineage to a model column, so it filters nothing.
- Answer: apply via `TREATAS(VALUES('Category Bucket'[Category]),'Product'[Category])`.
- Concepts: CC-010. Rules: ARC-LINEAGE-01.

---

## Category 3 — Function semantics

**T-FUNC-01 (basic).** *Is `ENDOFMONTH` valid inside scalar date math like an `EOMONTH`-style
expression?*
- Reasoning: `ENDOFMONTH` is a **table** TI function; scalar math needs a scalar.
- Answer: no — use `EOMONTH` (scalar); `ENDOFMONTH` only as a `CALCULATE` filter.
- Concepts: CC-005 (return-type). Rules: AR-TI-001 / ARC-FUNC-01.

**T-FUNC-02 (intermediate).** *A distinct count is one higher than expected. `VALUES` or `DISTINCT`?*
- Reasoning: `VALUES` includes the blank row added for invalid/missing relationship keys.
- Answer: use `DISTINCT` (or fix the missing keys).
- Concepts: CC-011. Rules: —.

**T-FUNC-03 (intermediate).** *`SUMMARIZE` with a measure column gives odd subtotals. Fix?*
- Reasoning: computing expressions inside `SUMMARIZE` has context pitfalls.
- Answer: group with `SUMMARIZE`, then compute with `ADDCOLUMNS` (or use `SUMMARIZECOLUMNS`).
- Concepts: CC-004. Rules: ARC-FUNC-02.

**T-FUNC-04 (basic).** *Why does `SELECTEDVALUE('Store'[Channel])` return blank on the total row?*
- Reasoning: multiple values are in context, so it returns the alternate (blank if none supplied).
- Answer: provide a default: `SELECTEDVALUE('Store'[Channel],"All Channels")`.
- Concepts: CC-011. Rules: ARC-STYLE-01.

**T-FUNC-05 (advanced).** *`ISFILTERED('Product'[Category])` is FALSE but Category clearly affects
results. Explanation?*
- Reasoning: the column may be cross-filtered (via another table), not directly filtered.
- Answer: check `ISCROSSFILTERED`; `ISFILTERED` only detects direct filters.
- Concepts: CC-011. Rules: —.

---

## Category 4 — Performance smells

**T-PERF-01 (intermediate).** *A measure is slow; timings show ~95% Formula Engine and many
CallbackDataIDs. Where do you look?*
- Reasoning: FE-bound with callbacks means per-row logic running during the scan.
- Answer: find a measure/`IF` inside an iterator; restructure to column math + column filter.
- Concepts: CC-013. Rules: ARC-PERF-04. Playbook: PB-SLOW-MEASURE.

**T-PERF-02 (intermediate).** *A measure is slow but timings show mostly Storage Engine and no
callbacks. Rewrite the DAX?*
- Reasoning: work is already in the fast engine; the formula isn't the bottleneck.
- Answer: no — investigate volume/cardinality in the model, not a DAX rewrite.
- Concepts: CC-013, CC-014. Rules: —.

**T-PERF-03 (basic).** *Model is 4 GB for ~10M fact rows. First thing to inspect?*
- Reasoning: cardinality dominates size and scan cost.
- Answer: highest-cardinality columns (full datetime, wide text keys); split/reduce/drop them.
- Concepts: CC-014. Rules: ARC-MODEL-02 / AR-PERF-004.

**T-PERF-04 (intermediate).** *`CALCULATE([Sales Amount], FILTER('Sales','Sales'[Net Price]>100))`
is slow. Improvement?*
- Reasoning: `FILTER` over the fact materializes a large table in the FE; a column predicate is an
  SE filter.
- Answer: use a column predicate, or `FILTER(VALUES(...))` on the smallest needed column.
- Concepts: CC-005, CC-012. Rules: AR-PERF-002 / ARC-PERF-03.

**T-PERF-05 (advanced).** *`DISTINCTCOUNT` of customers across a bridge is slow. Options?*
- Reasoning: distinct count is heavier than SUM and sensitive to filter shape/cardinality.
- Answer: reduce key cardinality; test bridge vs `TREATAS` propagation on realistic data; measure
  both.
- Concepts: CC-014. Rules: —.

---

## Category 5 — Measure review

**T-REV-01 (basic).** *Review: `Margin % := [Margin] / [Sales Amount]`.*
- Reasoning: `/` errors on zero and isn't engine-optimized.
- Answer: use `DIVIDE([Margin],[Sales Amount])`.
- Concepts: —. Rules: AR-DIV-001 / BP-021.

**T-REV-02 (basic).** *Review: `IF(HASONEVALUE('Store'[Channel]), VALUES('Store'[Channel]))`.*
- Reasoning: this is the verbose idiom for a single-value read.
- Answer: replace with `SELECTEDVALUE('Store'[Channel], "All Channels")`.
- Concepts: CC-011. Rules: ARC-STYLE-01.

**T-REV-03 (intermediate).** *Review: a measure references `[Expensive Measure]` five times in one
expression.*
- Reasoning: it may be recomputed each time; also hurts readability.
- Answer: capture once in a `VAR` and reuse.
- Concepts: CC-007. Rules: AR-PERF-003 / BP-022.

**T-REV-04 (intermediate).** *Review: `[Net Price]` written unqualified and `'Sales'[Sales Amount]`
written qualified.*
- Reasoning: the convention is reversed, inviting column/measure ambiguity bugs.
- Answer: qualify columns (`'Sales'[Net Price]`), leave measures unqualified (`[Sales Amount]`).
- Concepts: —. Rules: AR-STYLE-001 / AP-031.

**T-REV-05 (advanced).** *Review: a running-total measure clears the date with `'Date'[Date]<=cutoff`
but a Day-of-Week slicer no longer applies.*
- Reasoning: replacing the Date filter dropped the weekday filter that should persist.
- Answer: re-apply the surviving filter (e.g. add `VALUES('Date'[Day of Week])`) or scope the clear.
- Concepts: CC-019. Rules: AR-ALL-001. Pattern: cumulative-running-total.

---

## Category 6 — Model prerequisites

**T-MODEL-01 (basic).** *YTD returns odd values. First model check?*
- Reasoning: time intelligence requires a marked, contiguous Date table.
- Answer: verify Mark as Date Table + complete calendar.
- Concepts: — (BP-001). Rules: AR-TI-002. Playbook: PB-TI-WRONG.

**T-MODEL-02 (basic).** *Analyzing by delivery date won't filter. Likely model cause?*
- Reasoning: the delivery relationship is inactive.
- Answer: activate it per measure with `USERELATIONSHIP`.
- Concepts: CC-016. Rules: ARC-REL-01.

**T-MODEL-03 (intermediate).** *Distinct counts inflate after someone enabled a bidirectional
relationship "to make filtering work." Guidance?*
- Reasoning: bidirectional defaults create ambiguous paths and wrong totals.
- Answer: revert to single-direction; use per-measure `CROSSFILTER` or `TREATAS`.
- Concepts: CC-015, CC-006. Rules: AR-BIDI-001 / ARC-MODEL-01.

**T-MODEL-04 (intermediate).** *A calculated column stores a full-precision `OrderDateTime`. Concern?*
- Reasoning: near-unique values destroy VertiPaq compression and bloat the model.
- Answer: split into `OrderDate` (+ `OrderTime` if needed) or push to ETL.
- Concepts: CC-014. Rules: ARC-MODEL-02 / AP-022.

**T-MODEL-05 (advanced).** *A segmentation measure throws or double-counts for some customers.
Model cause?*
- Reasoning: overlapping/gapped ranges in the config table let a value match 0 or 2+ segments.
- Answer: make ranges contiguous and non-overlapping (derive Max from next row's Min).
- Concepts: —. Rules: AR-SEG-001. Pattern: dynamic-segmentation.

---

## Category 7 — Diagnostic scenarios (apply a playbook)

**T-DIAG-01 (intermediate).** *A matrix's "# distinct customers" grand total is smaller than the
sum of the category rows. Bug?*
- Reasoning: distinct count is non-additive; a customer active in two categories counts once in the
  total.
- Answer: not a bug — expected. (Confirm via PB-WRONG-TOTAL.)
- Concepts: CC-001. Rules: AR-ADD-001. Playbook: PB-WRONG-TOTAL.

**T-DIAG-02 (intermediate).** *YTD is flat across all of next year. Cause and fix?*
- Reasoning: no future-date guard; TI extends past the last real transaction.
- Answer: guard with `DateWithSales`/last-date-with-data and return `BLANK()` beyond it.
- Concepts: — . Rules: AP-006. Playbook: PB-TI-WRONG.

**T-DIAG-03 (advanced).** *A "% of total" sums to far more than 100% across the visible categories.
Likely cause?*
- Reasoning: the denominator's scope doesn't match the rows — `ALL` (grand total) vs `ALLSELECTED`
  (visible total) mismatch.
- Answer: choose `ALLSELECTED` for visible-total percentages; scope cleared columns deliberately.
- Concepts: CC-009, CC-019. Rules: ARC-CTX-03. Playbook: PB-PERCENT-OF-TOTAL.

**T-DIAG-04 (advanced).** *A measure shows blank rows everywhere after a colleague "fixed" blanks
with `+ 0`. What happened?*
- Reasoning: coalescing `BLANK()` to 0 defeats deliberate row-hiding (e.g. future dates / empty
  combinations now display).
- Answer: preserve `BLANK()` where hiding is intended; coalesce only at the display layer when safe.
- Concepts: — (core-concepts §9). Playbook: PB-BLANK-ZERO.

**T-DIAG-05 (advanced).** *A filter on a bridge dimension won't reach the fact. Diagnostic path?*
- Reasoning: walk PB-PROPAGATION — relationship exists? direction? active? many→one needs help?
  bidi ambiguity? disconnected table needs `TREATAS`?
- Answer: choose explicit propagation (`CROSSFILTER`/`TREATAS`/bridge), avoid blanket bidirectional.
- Concepts: CC-015, CC-010, CC-016. Rules: ARC-MODEL-01 / ARC-LINEAGE-01. Playbook: PB-PROPAGATION.

---

## Coverage map (item → primary concept/playbook)

| Category | Items | Primary concepts | Playbooks |
|---|---|---|---|
| Context reasoning | T-CTX-01..05 | CC-001/002/003/008/018 | — |
| CALCULATE behavior | T-CALC-01..06 | CC-004/005/006/010/016/019 | — |
| Function semantics | T-FUNC-01..05 | CC-005/011 | — |
| Performance smells | T-PERF-01..05 | CC-013/014 | PB-SLOW-MEASURE |
| Measure review | T-REV-01..05 | CC-007/011/019 | — |
| Model prerequisites | T-MODEL-01..05 | CC-014/015/016 | PB-TI-WRONG |
| Diagnostic scenarios | T-DIAG-01..05 | CC-001/009/015/019 | all 8 |

Total: 36 items across 7 categories. Expand over time; keep each item traceable to a concept or
rule so a failure points at the doc to reteach.
