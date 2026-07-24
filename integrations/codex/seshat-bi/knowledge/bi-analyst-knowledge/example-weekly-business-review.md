# Worked example: weekly business review (example, not schema)

A generic recurring-review example -- a different shape from the one-off
redesign: here the SAME brief is re-run each week, so framings emphasize
variance-vs-plan and threshold callouts. Domain-neutral; carries no client
data. Grounded in decision-back dashboard practice (see the spec's research
anchors: decision-driven elements, ABC/Pareto in category management, Few's
monitoring vs Eckerson's action).

## Context

A retail operator reviews performance every Monday. The review's job is to
answer, fast: did we hit plan, what moved, why, and what needs action this
week. This is a MONITORING cadence -- but still decision-driven: every element
earns its place by supporting a Monday decision.

## Decision-questions (ranked) with framing

| # | Weekly decision | Framing card | Note |
|---|-----------------|--------------|------|
| Q1 | Did we hit plan this week? | `benchmark-threshold` | value vs plan; threshold = plan line (a real target feed; else [GAP]) |
| Q2 | Up or down vs the same week last year? | `period-variance` | seasonality-aware (same week last year, not last week) |
| Q3 | Which categories drove the gap to plan? | `contribution-mix` | attribute the variance, not just show size |
| Q4 | Are we over-reliant on a few SKUs this week? | `concentration` | ABC; report the actual split, never assume 80/20 |
| Q5 | Any metric outside its normal band? | `trend-anomaly` + `signal-vs-noise` | band-checked; a holiday spike is seasonal, not an anomaly |
| Q6 | Which regions behave off-normal? | `segment-behavior` | min-sample guardrail on small regions |

## Story order (monitoring arc)

- **Overview**: Q1 (vs plan) + Q2 (vs last year) as paired headline deltas.
- **What changed**: Q5's banded metrics -- what left its normal range.
- **Why / where**: Q3 (variance-to-plan by category), Q4 (concentration), Q6
  (region behavior).
- **Action**: the shortlist of categories/regions crossing a threshold or
  outside a band, with the follow-up each implies.

## Guardrails in action

- **Seasonality (Q2/Q5)**: a spike in a holiday week is compared to the same
  holiday week last year before anyone calls it a "record" -- otherwise every
  seasonal peak reads as news.
- **Threshold discipline (Q1)**: the attention line is PLAN (a real feed), not
  a number the agent picked. If there is no plan feed, Q1 becomes a [GAP]
  (missing target feed) and the review reports actuals vs last year only.
- **Min-sample (Q6)**: a small new region with a wild rate is reported
  insufficient-sample, not ranked as best/worst performer.

## A [GAP] in action

- **Question**: "Is this week's promotion lifting sales above baseline?"
- **Missing source fact**: no promotion flag / no price-change event in the
  feed.
- **Unlocking feed**: a promo-calendar or price-change event stream joined by
  date/item.
- Recorded as a [GAP]; no uplift visual is fabricated.

## Why this example is here

It shows the route generalizes beyond a one-time redesign to a RECURRING
review, and that the same eight framings + story arc + guardrails apply -- only
the emphasis (plan-variance, thresholds) shifts with the cadence.
