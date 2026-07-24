# Framing card: segment behavior

**Card id**: `segment-behavior`

## Question shape

"Do different segments behave differently, in a way that changes what I do for
them?" Compares rate measures ACROSS a segmentation to find behavioral
difference, not size difference.

## Required inputs

- One or more rate/ratio measures (approved) that express behavior (an
  average, a rate, an intensity) -- not a raw total (that is size, covered by
  contribution).
- A segmentation dimension (customer type, channel, billing type, cohort, ...)
  whose members have enough volume to compare (see guardrail).

## Visual guidance

- Compare the rate across segments against the overall mean as a reference
  line -- "above/below normal" is the read, not the raw rate.
- For two behavioral rates at once, a scatter (rate A vs rate B, sized by a
  volume measure) separates behavior from size in one view.
- Sort or position by the behavioral difference, not alphabetically.

## Statistical guardrail (signal vs noise)

- **Minimum sample**: apply the minimum-sample guardrail from
  `framing-signal-vs-noise.md` (the home card). If a segment's underlying count
  is below the stated `guardrail.min_sample_floor`, report it as
  insufficient-sample and DO NOT rank or narrate its rate as a finding.
- **Mix confound**: a segment's rate can differ because its internal mix
  differs, not because the segment "behaves" differently. Note when a segment
  difference may be a composition effect.
- The overall-mean reference line is a display derivation, not a target.

## So-what template

"<segment> shows <rate> vs the <overall mean>, <above/below> normal by
<delta> -- warranting <segment-specific action>. (<Segment(s) X> excluded:
insufficient sample.)"
