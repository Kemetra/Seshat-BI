# Framing card: period variance (YoY / PoP / YTD-pace)

**Card id**: `period-variance`

## Question shape

"Are we up or down versus a comparable prior period, and by how much?" The
answer that turns a bare total into a signal. This is the default framing for
overview-stage headlines.

## Required inputs

- One measure (additive, or a period-over-period-capable ratio).
- A date dimension supporting the chosen comparison: prior year (YoY), prior
  period (PoP), or year-to-date pace (YTD vs prior YTD). The comparison
  baseline must exist in the data (e.g. YoY needs >= 2 years of history).

## Visual guidance

- Pair the current value with its comparison as a delta (absolute and %), not
  two bare numbers the reader must subtract.
- Overview headline: value + delta callout. Driver stage: a diverging column
  of delta by dimension member (gainers vs decliners around a zero line).
- State the comparison basis on the visual ("vs same period last year").

## Statistical guardrail (signal vs noise)

- **Seasonality-aware**: apply the seasonality guardrail from
  `framing-signal-vs-noise.md` (the home card) -- compare to the SAME phase of
  the prior cycle (same month/week last year), never the adjacent period, when
  the measure is seasonal. Record the chosen basis in the brief's `guardrail`
  block.
- **Base-size caveat**: a large % change on a tiny base is fragile; report the
  absolute alongside the % and flag when the base is small (ties to
  `framing-signal-vs-noise.md` minimum-sample rule).
- The comparison is a display derivation of the approved measure across a
  filter context -- not a new metric. If the contract already defines the
  comparison (e.g. a YoY-growth contract), cite the contract; do not redefine.

## So-what template

"<measure> is <+/-X%> (<+/-abs>) vs <basis>; <broad-based / driven by
<member(s)>>." For a diverging view: "<n> members grew, <m> declined; the
biggest mover is <member> at <+/-X%>."
