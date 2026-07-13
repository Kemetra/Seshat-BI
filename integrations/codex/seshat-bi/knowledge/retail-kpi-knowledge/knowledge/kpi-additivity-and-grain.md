# KPI Additivity and Grain

Additivity and grain are the two calls that most often go wrong and most often corrupt
a dashboard total row. Every contract must declare both.

## Grain

Grain is the level at which one row of the underlying fact means one thing. Retail
KPIs typically reference one of:

- **transaction line** — one product line within a receipt (price × qty, discount, cost)
- **transaction (receipt / header)** — one customer purchase event
- **branch-day** — one store's activity for one day
- **product-day / product-period** — one SKU's activity over a period
- **inventory snapshot date** — stock state captured at a point in time
- **period** — a roll-up grain (month, quarter, fiscal year) for time-based KPIs

A KPI declares the grain it is *computed from* and the grains it can be *aggregated to*.
Counting transaction lines when you mean receipts is the classic grain error: it
inflates transaction counts and breaks ATV and basket size.

## Additivity

Additivity answers: can you SUM this across a dimension and still get a correct number?

### Fully additive

Can be summed across every dimension including time. Currency amounts and unit counts
built from a clean fact are fully additive: gross sales, net sales, discount amount,
quantity sold, gross margin value. Summing them across days, branches, and products is
valid — provided no rows are double-counted.

### Semi-additive

Can be summed across some dimensions but **not** across time (or not the same way).
Examples:

- **Inventory snapshot (on-hand qty / cost)** — additive across products and branches at
  a single date, but you must **not** sum across snapshot dates. Use last/average over
  time, never SUM.
- **Cumulative measures like YTD** — already a running total; summing YTD values across
  months double-counts.
- **Distinct transaction count** — safe to add across branches and days when
  `transaction_id` is globally unique and time-bounded, but treat with care if the key
  is reused across branches or years.

### Non-additive

Cannot be summed across **any** dimension; must be recomputed from base components at
each level. This covers every ratio, average, and percentage:

- averages (ATV, average basket size)
- percentages (discount rate %, gross margin %, returns rate %, growth %)
- ratios (inventory turnover, GMROI, sales per sqm)

## Why ratios, averages, and percentages cannot be summed

A ratio is `numerator / denominator`. The correct value at a higher level is
`SUM(numerator) / SUM(denominator)` at that level — not the sum (or average) of the
child ratios. Summing percentages gives nonsense (e.g., three branches at 20% do not
make 60%). Averaging averages is weighted wrong (a small branch's ATV counts as much as
a large one). The rule: **carry the base components, recompute the ratio at every grain.**

## How this drives the contract

- Fully additive → measure is a SUM; safe in any total row.
- Semi-additive → measure needs an explicit time rule (last, average, or no-sum);
  flag it so the DAX layer does not naively SUM.
- Non-additive → measure must be defined as base-over-base and recomputed in filter
  context; the contract's "Common mistakes" must warn against summing it.
