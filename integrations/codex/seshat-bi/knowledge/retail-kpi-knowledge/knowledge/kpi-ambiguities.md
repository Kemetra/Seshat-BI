# KPI Ambiguities

The dangerous ambiguities that change a retail number without changing the data. Each
must be resolved (or explicitly flagged **Needs business definition**) before a contract
is handed off. Route here from any "numbers disagree between reports" symptom, then end
on the metric-ambiguity-checklist.

## A1 — VAT included vs excluded

Is a sales amount stored pre-tax or tax-inclusive? Mixing the two across branches,
channels, or measures silently inflates or deflates revenue and every margin built on
it. Decide once: revenue KPIs in this layer assume **pre-tax** unless the owner states
otherwise. Flag any field where VAT treatment is unconfirmed.

## A2 — Returns as negative sales vs separate fact

Are returns negative lines inside the sales fact, or a separate returns fact? If they
are negative lines and a measure naively sums, returns are netted invisibly and the true
sales and true return volume are both hidden. Prefer a separate fact or an explicit
`transaction_type` flag; either way the policy must be stated in every sales and returns
contract.

## A3 — Sale date vs posting date vs return date

Which date drives the time axis? Sale date (when sold), posting date (accounting date),
and return date (when returned) can all differ. A KPI compared on sale date will not
reconcile to one compared on posting date. Each contract names its primary date and
flags alternatives.

## A4 — Gross vs net

Gross sales (before discounts) and net sales (after discounts, pre-tax) are different
KPIs. Mixing them in one visual or one measure is the most common retail error. Discount
rate uses gross in the denominator; margin uses net. Never substitute one for the other.

## A5 — Discount: line vs header

Discounts can sit at the line level, the header (transaction) level, or both. Summing
both onto the same base, or counting a header discount once per line, double-counts the
giveaway. The discount contract must state which fields exist and how they combine.

## A6 — Cost method

COGS depends on the costing method (FIFO, average, standard). Margin and turnover change
with the method. The cost figure must align with finance's method; if unknown, margin
KPIs are **Needs business definition**.

## A7 — Cancelled / void / test transactions

Cancelled, voided, training, and test-store transactions must be excluded by policy.
Definitions of "cancelled" vary by source. Including them inflates counts and sales;
the exclusion rule must be explicit and confirmable.

## A8 — Product name vs product key

Aggregating by product name breaks when names change or duplicate; only the surrogate
product key is stable. Contracts require keys, not names, for grouping. Same logic for
hierarchy: one product maps to exactly one category path.

## A9 — Branch name vs branch key

Same problem as products: branch names get renamed, reused, or spelled inconsistently.
Aggregate on the branch/store key; treat the name as a display attribute only.

## A10 — Inventory snapshot date

Inventory is semi-additive: a snapshot is a state at a point in time, not a flow. The
snapshot frequency (daily EOD, intra-day, weekly) and whether it represents on-hand,
on-shelf, or warehouse stock change every inventory KPI. Must never be summed across
dates. Snapshot policy is **Needs business definition** until confirmed.

## A11 — Same-store definition

"Same-store" / "comparable store" needs an explicit rule: minimum months open, handling
of relocations and major refurbishments, treatment of closures. Without an agreed rule,
same-store growth is not reproducible and stays **Needs business definition**.

## Resolution rule

For any KPI touching one of these, the contract must either state the resolved policy
(with the owner who set it) or carry a **Needs business definition** flag. This layer
never invents a policy to make a number appear.
