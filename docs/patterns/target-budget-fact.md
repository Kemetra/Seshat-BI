# Pattern: Target/Budget Fact + Actual-vs-Plan Variance

**Status of this document**: a generic MODELLING PATTERN, not a shipped table. No
target/budget fact exists anywhere in this kit today. This document closes a
structural gap named in `skills/retail-kpi-knowledge/domains/targets-and-budgets.md`:
that domain doc teaches the "Net Sales vs Target %" KPI but records its status as
`Planned (needs target fact)`, because no target fact has ever been modelled here.

This document supplies the SHAPE a real target/budget fact would take. It supplies
no target VALUE, no RAG (red/amber/green) threshold, and no specific table's grain
decision -- those are owner-supplied business inputs (Principle V) that stay open,
named questions below.

## Who this is for

An analyst who has an actuals star already at Gold Ready (or later) and now has a
real target/budget source (a finance-supplied plan file, a budget spreadsheet, or
similar) and needs to model it as a second Kimball fact that can be compared
against actuals.

## 1. Conformed dimension keys (resolved default)

**The target fact MUST conform to the SAME dimension keys as the actuals star it
will be compared against.** This is not a new rule invented for target facts -- it
is RC14 (`docs/decisions/0002-retail-cleaning-defaults.md`: "Gold is a Kimball
star: one fact at the silver grain + conformed dims"), applied to a second fact
sharing the first fact's dimensions.

Concretely: if an actuals star has `dim_customer`, `dim_product`, and `dim_date`,
a target fact compared against it reuses THOSE SAME conformed dimension tables
(the same surrogate keys, the same `-1` UNKNOWN member convention) rather than
building parallel, disconnected dimensions. Without shared dimension keys, a
Kimball star has nothing to join a plan number against, and the comparison is not
mechanically expressible as a query -- it would have to be reconciled by hand
outside the model.

This is a **resolved structural default**: it applies to every target/budget fact,
not an owner decision to make per table.

## 2. Grain (owner-supplied, per table)

**Target-fact grain is an OWNER-SUPPLIED business decision.**
`[NEEDS CLARIFICATION: target-fact grain is owner-supplied per table]`

A target/budget source is commonly supplied at a COARSER grain than the actuals
fact it will be compared against -- for example, a budget might be planned at
"month x store x category" while the actuals star records one row per
transaction. This pattern does not assert what grain any given real target
source arrives at, or should be modelled at. That is a business-policy /
data-availability judgment the table owner makes when a real target source is
onboarded, and it belongs in that table's own `unresolved-questions.md`
(Acceptance Scenario 4, spec 095, User Story 1).

What this pattern DOES assert generically: whatever grain is chosen, the target
fact's dimension keys still conform per Section 1 above -- a coarser grain means
fewer dimensions are populated (or some are rolled up to a higher level of a
conformed hierarchy), not that the target fact invents its own, unconformed keys.

## 3. Non-additive variance calculation (resolved default)

**Aggregate actuals and targets SEPARATELY at the comparison grain, then
recompute the percentage. Never average two already-computed percentages.**

This rule is not invented here -- it is stated in
`skills/retail-kpi-knowledge/domains/targets-and-budgets.md` itself (see that
domain doc's "Notes" section: "Net Sales vs Target % is non-additive: aggregate
actuals and targets separately, then recompute the percentage"). This pattern
document cites that rule rather than restating it as independently-invented
guidance.

Why this matters mechanically: a variance percentage (e.g. `actual / target`) is
a ratio, and ratios do not average correctly across a rollup. If a query
pre-computes "percent of target" at a fine grain (say, per store) and then
averages those percentages up to a region, the result is mathematically wrong --
it does not equal the region's actual sum divided by the region's target sum,
unless every store happens to have an identical target. The correct approach is
always: sum the actuals at the comparison grain, sum the targets at the
comparison grain, THEN divide.

This is a **resolved structural default**: it applies to any actual-vs-plan
variance metric, not an owner decision to make per table.

## 4. Comparison happens at the coarser grain (resolved default)

**When actuals and target grains differ, the comparison happens at the COARSER
(typically target) grain. Actuals are rolled up to meet the target grain; targets
are never disaggregated to meet actuals.**

This is the expected, common case: targets are almost always supplied coarser
than the actuals a business tracks day to day. Rolling actuals up to a coarser
grain is a well-defined aggregation. Disaggregating a target down to a finer
grain than it was actually planned at would require inventing a distribution
assumption that the business never made -- which this pattern does not sanction.

What this pattern does NOT assert: which specific dimensions any given real
table's comparison rollup actually uses (e.g. "month x store" vs.
"month x store x category"). That detail follows directly from whatever grain
decision the table owner makes per Section 2, and is not asserted generically
here.

## 5. Missing-target handling (resolved default)

**A dimension member present in the actuals star with no corresponding target
row MUST be surfaced as an explicit flag. It MUST NOT be defaulted to a 0%
variance or silently dropped from the comparison.**

This rule is drawn from `skills/retail-kpi-knowledge/domains/targets-and-budgets.md`'s
own named key ambiguity ("Missing targets (e.g., new stores) must be flagged, not
shown as 0%"). A common real-world trigger: a store opened mid-year has actuals
but no budget yet, or a newly introduced product has sales but no target. Showing
that member's variance as 0% (which would read as "on target") or as blank (which
would read as "no data") both misrepresent an operationally important gap -- the
member is not failing its target, it simply has no target defined yet.

This pattern states the requirement as structural: a real target-fact build MUST
be able to represent "no target exists for this member" distinctly from "target
was hit exactly" or "no data." It does NOT decide how a specific table's
dashboard should visually represent that flag -- that is a dashboard-design
decision, out of scope for this pattern document.

## 6. Versioning / reforecast (owner-supplied, per table -- open edge case)

`[NEEDS CLARIFICATION: whether a target fact needs a version/as-of dimension for
reforecasts is owner-supplied per table]`

A target/budget source can itself change mid-period: a budget revision or a
reforecast replaces an earlier plan. A target fact that simply overwrites the
prior plan's row on ingest silently loses the ability to compare "actuals vs.
original plan" against "actuals vs. latest reforecast" -- two different, both
legitimate, business questions.

This pattern flags that a target fact MAY need a version/as-of dimension to avoid
that silent overwrite. It does not mandate one: whether any given table's target
source is ever revised mid-period, and if so what versioning scheme to use (a
version number, an as-of date, a separate "original" vs. "latest" fact), is an
owner-supplied judgment made when a real target fact is onboarded for that table.

## 7. Resolved defaults vs. open Principle-V items

This section exists so a future reader does not have to re-derive which parts of
this pattern are safe, kit-supplied defaults and which are business-policy
judgment calls a named human must still supply (FR-019, spec 095).

**Resolved structural defaults (this pattern already decides these):**

- Conformed dimension keys -- the target fact reuses the SAME dimension keys as
  the actuals star it is compared against (Section 1; RC14).
- Non-additive variance calculation -- aggregate each side separately at the
  comparison grain, then recompute the ratio (Section 3).
- Comparison happens at the coarser (typically target) grain -- actuals rolled
  up, never targets disaggregated (Section 4).
- Missing-target-must-flag -- a dimension member with no corresponding target
  MUST be surfaced as an explicit flag, never a silent 0% or drop (Section 5).

**Open, owner-supplied Principle-V items (this pattern deliberately leaves these
unresolved):**

- Target-fact grain for any specific table (Section 2).
- RAG (red/amber/green) numeric thresholds for any variance metric -- see
  `templates/metric-contract-shape.variance-vs-target.yaml` for where this is
  recorded once an owner supplies it. This pattern document does not restate or
  invent a threshold.
- Whether a target fact needs a version/as-of dimension for reforecasts, and if
  so what scheme (Section 6).
- How a specific table's dashboard visualizes the missing-target flag (Section
  5) -- a dashboard-design decision, out of scope here.

## 8. Scope boundary -- what this document does NOT contain

This document contains NO target VALUES, NO RAG thresholds, and NO specific
table's grain decision anywhere. Every number a reader might expect to see next
to "target," "budget," "variance," or "RAG" is intentionally absent. When a real
target/budget table is onboarded, its grain decision, its RAG thresholds, and any
versioning scheme are owner-supplied business inputs recorded in THAT table's own
`unresolved-questions.md` (following the existing `source-mapping` gate) -- not in
this generic pattern document, and not invented by an agent reading this document.

## What building a real target/budget fact requires

Per Constitution Principle IV (source mapping before silver) and Principle VIII
(static-first, live-deferred), a real target/budget fact for any table restarts
at Mapping Ready for the NEW target source -- it walks the existing
`source-mapping` -> `retail-build-warehouse` -> `retail-validate` sequence like
any other new bronze table. This pattern document is not itself a build; it is
the reference an analyst reads before starting that build. See
`docs/worked-examples/target-budget-pattern-retail-store-sales.md` for a
narrative walkthrough of this pattern applied to an existing, named actuals star,
and `templates/metric-contract-shape.variance-vs-target.yaml` for the matching
variance metric contract shape.

## See also

- `docs/decisions/0002-retail-cleaning-defaults.md` (RC14: Kimball star +
  conformed dims discipline).
- `skills/retail-kpi-knowledge/domains/targets-and-budgets.md` (the domain doc
  this pattern closes the gap for; the non-additive variance rule and the four
  named key ambiguities).
- `templates/metric-contract-shape.variance-vs-target.yaml` (the matching
  variance metric contract shape).
- `docs/worked-examples/target-budget-pattern-retail-store-sales.md` (the second
  worked-example narrative applying this pattern to a named, existing actuals
  star).
- `docs/worked-examples/retail-store-sales.md` (the kit's first worked example;
  the actuals-only star pattern this document extends).
