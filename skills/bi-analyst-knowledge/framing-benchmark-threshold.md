# Framing card: benchmark & threshold

**Card id**: `benchmark-threshold`

## Question shape

"Is this number good?" Supplies the context that makes a value interpretable --
against a named baseline (benchmark) and a named line for attention
(threshold). Without this framing, a headline is a number with no verdict.

## Required inputs

- One measure (any kind).
- A named comparison basis that EXISTS in the committed evidence or is an
  owner-supplied decision: prior period, plan/target (only if a target feed
  exists -- else [GAP]), an overall/portfolio average, or a peer/category
  norm present in the data. The basis must be real, not invented.

## Visual guidance

- Pair the value with its basis and mark the threshold line; use a KPI card
  with a comparison, or a bullet-style visual (value, basis marker, band).
- Encode direction-of-good so above/below reads as good/bad without a legend
  (respect each contract's `direction_of_good`).
- State the basis on the visual ("vs plan", "vs portfolio average").

## Statistical guardrail (signal vs noise)

- A threshold is a NAMED basis (period average, plan, portfolio mean), never a
  magic number the agent invents. If the only sensible basis is a target that
  does not exist in the data -> [GAP] (missing target feed), not a fabricated
  threshold.
- A single value against a single basis has no dispersion context; where
  volatility matters, pair with the trend band (`framing-trend-anomaly.md`) so
  "below average" is not just this period's noise.

## So-what template

"<measure> is <value>, <above/below> <basis> by <delta> -- <good/bad per
direction-of-good>, <crossing / within> the <threshold basis>." If no basis
exists: "[GAP] -- no <target/benchmark> feed; value shown without a verdict."
