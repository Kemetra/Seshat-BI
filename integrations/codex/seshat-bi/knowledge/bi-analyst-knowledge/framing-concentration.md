# Framing card: concentration (Pareto / ABC)

**Card id**: `concentration`

## Question shape

"How dependent is the total on a few members?" A risk read: high concentration
= fragility (lose one and the total drops); low concentration = a long tail to
manage. Distinct from contribution (which member is big) -- this is about the
SHAPE of the distribution.

## Required inputs

- One additive measure.
- A dimension with enough members that concentration is a real question
  (products, customers, SKUs). A handful of members has no meaningful tail.

## Visual guidance

- A Pareto view: members sorted descending with a cumulative-% line; mark the
  point where cumulative reaches ~80% (the ABC "A" set).
- Report the headline as a sentence, not just a chart: "top N = X% of total."
- For ABC, band members into A/B/C by cumulative contribution and count each
  band.

## Statistical guardrail (signal vs noise)

- Cumulative share is a display derivation of an approved additive measure.
- **The 80/20 is an observation, not a law**: report the ACTUAL split ("top
  12% of products = 80% of sales"), never assume 80/20 holds. Forcing the
  cliche onto data that does not show it is a fabricated finding.
- **Grain sensitivity**: concentration depends on the member grain -- SKUs
  look more concentrated than categories. State the grain the claim is at.

## So-what template

"The top <N> <members> (<share of member count>) account for <X%> of
<measure>; the business is <highly / moderately / lightly> concentrated,
implying <dependency risk on the head / a long tail to rationalize>."
