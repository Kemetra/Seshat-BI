# Worked example: specialty-retail sales redesign (example, not schema)

A sanitized walkthrough of the full route on a generic specialty-retail sales
table. It demonstrates the machinery; it is NOT a schema and carries no client
data, numbers, names, or connection details (Principles VII, IX). Any real run
derives everything from that run's own approved contracts + source-profile.

> Deviation note (spec 021-analyst-narrative-layer, T007): tasks/plan named this
> file `example-c086-retail.md` "from the #452 review". It ships as
> `example-specialty-retail.md`, fully genericized -- the originating critique
> (#452) is real, but all client identity (project code, numbers, PII, hosts)
> is removed under Principles VII/IX.

## The starting point (the anti-pattern this example fixes)

A first attempt produced a structurally valid report: KPI cards + a trend + a
product matrix + a category donut, repeated per page, every visual bound to an
approved contract. It passed every correctness gate -- and answered no
decision. Cards showed totals with no comparison; pages were topic buckets
("Sales", "Returns"); nothing localized a cause. That is the "traditional /
computer" view. The route below turns it into an analysis.

## Inputs assumed (from that table's committed artifacts)

- Approved measures (illustrative kinds): a gross sales total (additive), a
  units total (additive), a transaction count (distinct-count), an average
  transaction value (ratio), an average basket size (ratio), a return rate by
  count (ratio, lower-is-better), a return rate by value (ratio), a YTD total,
  a YoY growth (ratio).
- Profiled dimensions: a product hierarchy (division -> category ->
  subcategory -> segment -> item), a billing/transaction-type dimension that
  is the AUTHORITATIVE returns signal, a staff dimension (name masked at the
  gate -- PII), a customer dimension, and a contiguous multi-year date
  dimension. Gross-only model (discount/net dropped by owner ruling).

## Decision-questions (ranked) with framing

| # | Owner decision | Framing card | Why this framing |
|---|----------------|--------------|------------------|
| Q1 | Is the business healthy vs last year, broadly or narrowly? | `period-variance` | overview headline must carry YoY, decomposed by division |
| Q2 | Is growth price, basket, or traffic? | `rate-decomposition` | tells the owner which lever to pull |
| Q3 | Where do I push -- which categories carry us and whose share is shifting? | `contribution-mix` | size vs momentum are different decisions |
| Q4 | How dependent are we on a few items? | `concentration` | dependency-risk read on the product tail |
| Q5 | Where do returns concentrate -- by count vs by value? | `segment-behavior` + `signal-vs-noise` | the count/value gap is the insight; thin segments withheld |
| Q6 | Is return intensity trending up? | `trend-anomaly` | band-checked so a one-off is not called a trend |
| Q7 | What is our trajectory and seasonal shape? | `period-variance` (YTD pace) + `trend-anomaly` | names the seasonal peaks, not just the daily wiggle |

## Story order (the arc, not topic buckets)

- **Overview**: Q1 (+ Q2 as the "why" of the headline).
- **What changed**: Q1's diverging-by-division view, Q7's YTD pace.
- **Why / where**: Q3 (contribution/mix), Q4 (concentration), Q5 (returns
  drivers).
- **Action**: Q6's flagged return trend + the shortlist of shifting categories.

## The narrative-brief front section this produces (the enforceable shape)

This is what the front section of `mappings/<table>/narrative-brief.md` looks
like for the questions above -- the machine-checkable half. Values are
illustrative (no client numbers); `revision` shas are placeholders.

```yaml
schema: seshat.narrative-brief/v1
table: <table>
source_profile: mappings/<table>/source-profile.md
contracts:
  - {id: GrossSalesGrowthYoY, revision: <sha>}
  - {id: TotalSales,          revision: <sha>}
  - {id: ReturnRate,          revision: <sha>}
  - {id: ReturnRateValue,     revision: <sha>}
questions:
  - id: Q1
    decision: "Is the business healthy vs last year, broadly or narrowly?"
    stage: overview
    framing: period-variance
    cites: {measures: [GrossSalesGrowthYoY, TotalSales], dimensions: [product.division]}
    comparison: "same period last year"          # named: passes the headline rule
    guardrail: {basis: "same period last year"}   # period-variance is guardrail-bearing
    callout: "Total is <+/-X%> YoY; <broad-based / driven by N divisions>."
  - id: Q5
    decision: "Where do returns concentrate -- by count vs by value?"
    stage: why_where
    framing: segment-behavior
    cites: {measures: [ReturnRate, ReturnRateValue], dimensions: [billing_type.type]}
    comparison: none                              # not overview -> "none" is legal
    guardrail: {basis: "overall return rate", min_sample_floor: 200}
    callout: "Returns are <frequent-cheap / rare-expensive> in <segment>; thin segments withheld."
story_order:
  overview:  [Q1, Q2]
  change:    [Q7]
  why_where: [Q3, Q4, Q5]
  action:    [Q6]
gaps:
  - question: "Which categories are bleeding margin?"
    missing_source_fact: "no unit-cost column"
    unlocking_feed: "a landed-cost feed joined at item grain"
```

Note how the schema makes the analysis ENFORCEABLE: Q1 is `stage: overview`
so its `comparison` may not be "none" (no bare-total headline); Q5's
`segment-behavior` framing requires a `guardrail.basis`; `story_order` places
every question in exactly the stage its `stage` field declares. A checker
verifies all of this without reading a word of prose.

## A guardrail in action (Q5)

Return rate by a thin transaction-type segment is reported as
**insufficient-sample**, not ranked -- a confident return rate on a handful of
lines would be noise dressed as a finding. The count-based vs value-based
return rates are shown together: the GAP between them (frequent-but-cheap vs
rare-but-expensive returns) is the actual insight, not either rate alone.

## A [GAP] in action

- **Question**: "Which categories are bleeding margin?"
- **Missing source fact**: no unit-cost column in the source.
- **Unlocking feed**: a cost/landed-cost feed joined at item grain.
- Recorded as a [GAP]; NO margin visual is fabricated. Same treatment for
  inventory turnover (no inventory snapshot) and target attainment (no target
  feed).

## The three-way binding map this produces (Phase B, the enforceable shape)

Once the brief is committed and `dashboard-design` authors the layout, the
binding map is upgraded from F011's two-way (visual -> contract) to THREE-way:
**visual -> contract -> decision-question**. It lives at
`mappings/<table>/design/visual-contract-binding-map.md` and, like the brief,
carries a machine-readable `seshat.binding-map/v1` front section the
`narrative-check --binding-map` verb reads. Values are illustrative (no client
numbers); it references the SAME question ids the brief above declares (Q1, Q5,
...), so the two artifacts compose.

```yaml
schema: seshat.binding-map/v1
table: <table>
brief: mappings/<table>/narrative-brief.md    # the brief whose Q-ids this map references
pages:
  - id: executive_overview                    # a page may be a bare id or {id, regions}
    regions: [kpi_strip, main_insight, why_where]
visuals:
  - visual_id: v01
    page: executive_overview
    region: kpi_strip
    visual_type: card
    contract: TotalSales
    decision_questions: [Q1]                   # a LIST: one visual may answer >1 decision
    headline: true                             # KPI-card class -> must answer an overview question
  - visual_id: v03
    page: executive_overview
    region: kpi_strip
    visual_type: card
    contract: AvgTransactionValue
    decision_questions: [Q1, Q5]               # basket-value card serves BOTH the headline and Q5
    headline: true
  - visual_id: v09
    page: executive_overview
    region: why_where
    visual_type: bar
    contract: ReturnRate
    decision_questions: [Q5]                    # a diagnostic visual answering one why/where question
    headline: false
```

Note how the three-way map makes the analysis ENFORCEABLE, one level past the
brief:

- **No orphan visual (FR-005).** Every visual names >=1 `decision_questions`
  entry, and each entry MUST be a question the brief declares. A visual bound to
  a contract but answering no owner decision is an orphan -- the same defect
  class as an unbound visual, now checkable.
- **No page serves nothing.** Every declared page carries at least one
  question-bearing visual; a page that answers no owner decision is a coverage
  defect.
- **No bare-total headline (FR-006).** A `headline: true` (KPI-card class)
  visual MUST answer at least one `stage: overview` question -- and the brief
  already forces every overview question to name a `comparison` (never "none").
  So "the headline carries a comparison" is enforced by the two artifacts
  together, without the map restating the comparison rule.
- **One visual, many decisions (allowed, explicit).** v03 answers Q1 AND Q5;
  the map lists both -- no implicit reuse. This is the spec edge case: two
  decision-questions answered by the same visual are allowed, but both triples
  must be stated.

## What changed vs the traditional baseline

- Every page opens with a decision, not a subject.
- Every overview headline carries a comparison (YoY / vs-average), never a
  bare total.
- Returns are framed by the count-vs-value gap with a sample guardrail, not a
  single rate on a donut.
- Unanswerable owner questions are honest [GAP]s, not faked visuals.
- The product hierarchy is used to LOCALIZE a change (why/where), not just to
  display a matrix of totals.
- The three-way binding map ties every visual to the decision it serves
  (Phase B) -- an orphan visual, an empty page, or a bare-total headline is now
  a named, checkable defect, not a judgment call.
