# Framing card: trend & anomaly

**Card id**: `trend-anomaly`

## Question shape

"How is <measure> moving over time, and is any point unusual enough to act
on?" Answers direction, tempo, and whether a spike/dip is signal or noise.

## Required inputs

- One additive measure (contract kind: additive) OR a non-additive rate
  measure plotted as-is (never summed across time).
- A date/time dimension with enough contiguous history to establish a baseline
  (see guardrail). No date dimension -> this framing is a [GAP]; state why.

## Visual guidance

- A line (continuous time) for the measure over the finest grain the decision
  needs; coarser grain for the overview stage, finer for the driver stage.
- Show the baseline the anomaly claim rests on (a trailing-average band), not
  just the raw series, whenever an anomaly is claimed.
- Annotate only the points that clear the guardrail; do not label every wiggle.

## Statistical guardrail (signal vs noise)

- An anomaly is a point outside a **trailing band**. Apply the control-band
  guardrail defined in `framing-signal-vs-noise.md` (the home card) for the
  band's k and window; record the chosen basis/window in the brief's
  `guardrail` block. The band is a LABELED display derivation of the approved
  measure -- never a new metric.
- **History floor**: if the series is too short for a stable band (fewer than
  ~2x the seasonal cycle, or a handful of points), state the band's basis is
  insufficient and WITHHOLD the anomaly claim -- show the trend plain.
- Seasonality: a "spike" that recurs every cycle is seasonal, not an anomaly
  -- compare to the same phase last cycle (see `framing-period-variance.md`)
  before calling it unusual.
- Regression, forecasting, and significance testing are out of scope (v1).

## So-what template

"<measure> is <rising/flat/falling> over <window>; the <date> point is
<above/below> its trailing band (<basis>), which warrants <a look at drivers /
no action -- within normal variation>." If withheld: "trend shown; too little
history to call any point anomalous."
