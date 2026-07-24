# Framing card: contribution & mix-shift

**Card id**: `contribution-mix`

## Question shape

"Who drives the total, and is the mix shifting?" Separates size (who is big)
from momentum (whose share is growing or shrinking) -- two different decisions.

## Required inputs

- One additive measure (share of a total requires additivity; a ratio has no
  meaningful "share of total" -- do not force this framing onto ratios).
- A categorical dimension to attribute the total across (division, category,
  segment, channel, ...).
- For mix-SHIFT: a comparison period (this year vs last) so share can move.

## Visual guidance

- Contribution (static): each member as a % of the current total -- a ranked
  bar or a 100%-stacked view. Avoid pies beyond ~5 slices.
- Mix-shift (dynamic): current share vs prior share side by side, or the
  change in share (percentage points) by member. The SHIFT is the insight, not
  the level.
- Always sort by contribution; never leave members in arbitrary order.

## Statistical guardrail (signal vs noise)

- Share is a display derivation (member measure / total measure) of an
  approved additive measure -- not a new metric.
- **Composition caveat**: a member's share can rise purely because others fell
  (the total shrank), not because the member grew. Read share-shift together
  with the absolute (ties to `framing-period-variance.md`) before claiming a
  member "gained."
- **Tiny-member noise**: sub-1% members' share swings are usually noise; group
  them ("all others") rather than narrating each.

## So-what template

"<member(s)> drive <X%> of <measure>; <a member> is <gaining/losing> share
(<+/- pp> vs <basis>) -- <because it grew / because the total shrank>." 
