# Framing card: signal vs noise (statistical guardrails)

**Card id**: `signal-vs-noise`

This is the guardrails HOME card. The other seven cards reference it. Its job:
stop the report from presenting noise as a finding -- the statistical twin of
inventing a metric. Every guardrail here is OWNER-GRADE (a numerate owner would
accept it), not a statistician's toolkit.

## Question shape

Not a standalone page question -- a check applied to any claim: "is this
difference/spike/rate real enough to act on, or is it noise?"

## The four guardrails

1. **Control bands for anomaly claims.** A point is "unusual" only if it falls
   outside a trailing band: trailing mean +/- k x dispersion (k=2 x trailing
   SD, or an IQR-based band) over a STATED window. The band is a labeled
   display derivation of the approved measure. No band basis stated -> no
   anomaly claim.

2. **Seasonality-aware comparison for variance claims.** Compare to the same
   phase of the prior cycle (same month/week last year), never the adjacent
   period, when the measure is seasonal. An adjacent-period jump on seasonal
   data is expected, not news.

3. **Minimum-sample caveat for rate claims.** A rate (return rate, conversion,
   any share) over too few underlying observations is unstable. Below a stated
   count floor, report **insufficient-sample** and withhold the rate as a
   finding -- never rank, sort, or narrate it. This is the rule
   `framing-segment-behavior.md` leans on.

4. **Correlation-vs-causation caution for driver claims.** A decomposition or
   co-movement ("X rose with Y") is arithmetic or associational, NOT a causal
   claim. State drivers as decomposition/association; never assert cause the
   data cannot establish.

## What is explicitly OUT of scope (v1)

Regression, forecasting, significance/hypothesis testing, confidence
intervals, and any method that computes NEW business meaning. Those would cross
from framing-approved-numbers into inventing analysis. If a decision genuinely
needs them, that is a [GAP] (missing analytical capability), routed for a named
human, not silently applied.

## The invariant

A band, a trailing average, an overall-mean reference line, a share, a
cumulative % -- all are LABELED DISPLAY DERIVATIONS of approved measures.
They are allowed and must be labeled as such. Nothing here defines or invents
a metric; meaning always traces to a contract.

## So-what template

Applied inline to other cards' claims: "<claim> -- <holds: outside the band /
above min sample / seasonally comparable> " OR "<withheld: insufficient
sample / insufficient history / seasonal, not anomalous>."
