# Worked Example -- Target/Budget Fact Pattern applied to retail_store_sales

**This is a NEW, second worked-example document. It is distinct from, and does
not edit, `docs/worked-examples/retail-store-sales.md`.** That file is the
kit's first worked example and traverses the full seven-stage readiness spine
for the `retail_store_sales` ACTUALS star; it remains unchanged. This document
follows that file's own section-structure convention (a "readiness at a
glance" framing plus a narrative walkthrough) but does not restate its content
-- it applies the target/budget-fact pattern from
`docs/patterns/target-budget-fact.md` to that same actuals star's EXISTING,
committed conformed dimensions, as the SECOND data point Principle VII's
genericity bar calls for (one worked example cannot prove a pattern is
generic; this is the second).

**What this document is NOT.** This is a pattern-and-shape walkthrough, not a
build. No bronze, silver, or gold object for a `retail_store_sales` target
fact exists anywhere in this repository. No mapping artifact, no
`readiness-status.yaml` record, and no metric contract for a target/budget
fact exists for this table. If a reader (human or agent) tries to treat this
document as evidence that a `retail_store_sales` target fact is buildable or
started -- for example, by running `retail-onboard-table` against it -- that
is a misuse of this document: there is nothing here to onboard against. See
the "Honest readiness framing" section below.

## Readiness at a glance -- retail_store_sales TARGET FACT (not the actuals star)

| # | Stage | Status | One-line evidence |
|---|-------|--------|-------------------|
| 1 | Source Ready | **not_started** | No target/budget source has been supplied or profiled for this table. |
| 2 | Mapping Ready | **not_started** | No `mappings/<target-source-table>/` directory exists. |
| 3 | Silver Ready | **not_started** | No silver migration exists for a target fact. |
| 4 | Gold Ready | **not_started** | No gold target fact exists. |
| 5 | Semantic Model Ready | **not_started** | No variance metric contract has been filled or approved for this table. |
| 6 | Dashboard Ready | **not_started** | No variance/RAG dashboard design exists. |
| 7 | Publish Ready | **not_started** | Nothing above has started. |

This table is separate from, and does not affect, `retail_store_sales`'s
EXISTING actuals-star readiness record (`mappings/retail_store_sales/readiness-status.yaml`),
which is already at Publish Ready (`warning`) per
`docs/worked-examples/retail-store-sales.md`. The two are independent spine
records: one for the actuals star (built), one for a hypothetical target fact
(not started). See "Restarting at Mapping Ready" below.

## 1. Conformed dimensions this hypothetical target fact would reuse

Per `docs/patterns/target-budget-fact.md` Section 1 (conformed dimension keys,
RC14), a target/budget fact for `retail_store_sales` would conform to the SAME
dimension keys as the existing actuals star. Those dimensions already exist,
committed, in `warehouse/migrations/0004_create_gold_retail_store_sales_star.sql`:

- `gold.fct_sales_rss` -- the existing ACTUALS fact (12,575 transaction-grain
  rows; see `docs/worked-examples/retail-store-sales.md` Section 4). A target
  fact is compared AGAINST this fact; it does not replace or modify it.
- `gold.dim_customer_rss`
- `gold.dim_product_rss`
- `gold.dim_payment_method_rss`
- `gold.dim_location_rss`
- `gold.dim_date_rss`

These five dimension names and the one fact name above are copied VERBATIM
from `0004_create_gold_retail_store_sales_star.sql` and from
`docs/worked-examples/retail-store-sales.md`. No dimension or table name in
this section is invented.

Applying the pattern's Section 1 requirement: IF a real target/budget fact
were built for `retail_store_sales`, it would need to reuse these same
conformed dimension surrogate keys (`customer_sk`, `product_sk`,
`payment_method_sk`, `location_sk`, `date_sk`) -- not build parallel,
disconnected dimensions -- so that a variance query can join actuals and
target rows on shared keys. Which of these five dimensions a real target
source would actually populate (all five, or a coarser subset) depends on the
grain decision below, which this document does not make.

## 2. Grain -- not decided here

Per `docs/patterns/target-budget-fact.md` Section 2,
`[NEEDS CLARIFICATION: target-fact grain is owner-supplied per table]`
applies to `retail_store_sales` exactly as it applies to any other table. No
budget or target source has ever been supplied for this table, so there is no
data fact to ground a grain decision against. A plausible illustrative
example -- NOT a decision, NOT a real source -- might be a monthly budget by
`location` and `category` (a coarser grain than the actuals fact's
transaction grain), but this document does not assert that is the grain a
real `retail_store_sales` target source would actually use. That determination
would be made from the real source's own profile, at Source Ready, exactly as
the actuals star's own grain (one transaction) was determined by profiling
in `docs/worked-examples/retail-store-sales.md` Section 1 -- never asserted in
advance of the data.

## 3. Non-additive variance calculation -- the rule, not a computed number

Per `docs/patterns/target-budget-fact.md` Section 3 and
`skills/retail-kpi-knowledge/domains/targets-and-budgets.md`'s own notes, a
"Net Sales vs Target %" variance for `retail_store_sales` would be computed by
summing actual net sales (from `gold.fct_sales_rss`) separately at the
comparison grain, summing target net sales (from the not-yet-built target
fact) separately at the same grain, and then dividing -- never by averaging
two pre-computed percentages. This section states the RULE only. No actual
sum, no target sum, and no resulting percentage is computed or asserted
anywhere in this document, because no target data exists for this table.

## 4. Comparison grain -- rollup direction only, no dimensions asserted

Per `docs/patterns/target-budget-fact.md` Section 4, IF a real target source
for `retail_store_sales` were supplied at a coarser grain than the actuals
fact's transaction grain, the comparison would roll actuals UP to meet that
coarser grain -- never disaggregate the target down to transaction grain. This
document does not assert which of the five conformed dimensions such a rollup
would actually group by; that follows from whatever grain decision Section 2
above leaves open.

## 5. Missing-target case -- illustrative only

Per `docs/patterns/target-budget-fact.md` Section 5, IF a real target source
for `retail_store_sales` existed and some dimension member (e.g. a `location`
or a product `category`) had no corresponding target row, that member's
variance would need to be surfaced as an explicit flag -- never a silent 0% or
dropped row. `retail_store_sales`'s actuals star has known dimension members
(five populated `location` values, and so on, per
`docs/worked-examples/retail-store-sales.md`), but since no target source
exists, this document does not claim any specific member IS or IS NOT
currently missing a target -- there is no target data to check that against.

## 6. Honest readiness framing -- not_started, and why that is the correct status

`retail_store_sales` has NO target/budget fact today. No bronze, silver, or
gold object exists for one. No `mappings/<target-source-table>/` directory,
no `source-map.yaml`, no `unresolved-questions.md`, and no
`readiness-status.yaml` record exists for a `retail_store_sales` target fact.
Per the four-status vocabulary (`not_started | blocked | warning | pass`;
`.specify/memory/constitution.md` Readiness System section) and hard rule #9
(no fabricated confidence/health/maturity/completeness score), the only
honest status for every stage of this hypothetical build is **not_started**.
This document does not assign `blocked`, `warning`, or `pass` to any stage of
a `retail_store_sales` target fact, because none of those statuses would be
true: nothing has been attempted yet that could be blocked, carry a
non-fatal warning, or be approved.

Zero target values, zero variance figures, and zero RAG (red/amber/green)
color or threshold assignments appear anywhere in this document for
`retail_store_sales` or for any table. Every place a reader might expect a
number is instead a citation to the pattern document's own
`[NEEDS CLARIFICATION]` markers.

## 7. Restarting at Mapping Ready -- this does not extend the actuals star's status

Building a REAL target/budget fact for `retail_store_sales` (or any table)
restarts the mapping gate at Mapping Ready for the NEW target source -- the
budget file or finance system that would supply target rows is a distinct
bronze source from the Kaggle CSV that supplied the actuals star, and it goes
through its own Source Ready -> Mapping Ready walk via the existing
`source-mapping` skill, exactly like onboarding any other new table.

This MUST NOT be read as implying that `retail_store_sales`'s existing actuals
star -- already at Gold Ready, Semantic Model Ready, Dashboard Ready, and
Publish Ready (`warning`) per `docs/worked-examples/retail-store-sales.md` --
extends any of that progress to an unbuilt target fact. The two are entirely
separate readiness journeys sharing only the conformed dimension tables
(Section 1 above) once (if) a target fact is actually built.

## What a real build would look like (orientation only -- not scheduled here)

Per Constitution Principle VIII (static-first, live-deferred) and FR-018 of
spec 095, this document does not author, and does not schedule, any of the
following. They are named here only so a future reader knows what a real
target-fact build for `retail_store_sales` would eventually touch:

- `mappings/<target-source-table>/` -- the standard five mapping-gate
  artifacts, walked via the `source-mapping` skill.
- `warehouse/migrations/NNNN_create_silver_<target-source-table>.sql` and a
  matching gold migration, authored via `retail-build-warehouse` only after
  the mapping gate clears.
- `mappings/<target-source-table>/metrics/<VarianceMetricName>.yaml` -- a REAL
  filled contract, starting from
  `templates/metric-contract-shape.variance-vs-target.yaml` as a pattern, with
  a real owner, a real grain, and eventually real RAG thresholds.
- A fresh `mappings/<target-source-table>/readiness-status.yaml`, restarting
  at Mapping Ready.

None of these exist today. None are created by this document.

## See also

- `docs/patterns/target-budget-fact.md` -- the modelling pattern this
  document applies (grain, conformance, non-additive variance, missing-target
  flagging, comparison-at-coarser-grain).
- `templates/metric-contract-shape.variance-vs-target.yaml` -- the matching
  variance metric contract shape.
- `docs/worked-examples/retail-store-sales.md` -- the kit's first worked
  example; the ACTUALS star this document's illustrative pattern is applied
  against, unedited by this document.
- `warehouse/migrations/0004_create_gold_retail_store_sales_star.sql` -- the
  source of every dimension/table name cited in Section 1.
- `skills/retail-kpi-knowledge/domains/targets-and-budgets.md` -- the domain
  doc naming the "Net Sales vs Target %" gap this pattern closes, unedited by
  this document.
