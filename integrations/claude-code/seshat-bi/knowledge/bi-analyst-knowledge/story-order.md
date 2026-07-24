# Story order: from a set of questions to a narrative a reader follows

A report is not a set of topic buckets; it is an argument. This route orders
the ranked decision-questions into a story arc and attaches the five
decision-driven elements so each stage does work, not decoration.

## The arc (four stages)

1. **Overview -- "is it healthy?"** The one-glance state of the business.
   Headline measures, each carrying a comparison (never a bare total). The
   reader should leave this stage knowing whether to relax or to dig.
2. **What changed -- "what moved?"** Variance and trend against a baseline
   (prior year, prior period, plan, benchmark). Surfaces the deltas that
   overview only summarized.
3. **Why / where -- "where is it coming from?"** Contribution, concentration,
   segment behavior, rate decomposition -- the drivers behind the change.
   This is where the report earns its keep: it localizes the cause.
4. **Action -- "what do I do?"** The few places that warrant a decision, made
   obvious. Thresholds crossed, signals flagged, the shortlist to act on.

A single-page report runs the same arc as **zones** top-to-bottom instead of
as pages: overview band -> change band -> driver band -> action rail.

## The five decision-driven elements (attach to every stage)

Carried through the arc so a page enables action, not just observation:

- **Priority** -- what matters is shown first / largest. Rank drives position.
- **Thresholds** -- when a number deserves attention is defined, not left to
  the reader (e.g. "above the period average", "below plan"). A threshold is a
  named basis, not a hardcoded magic number invented by the agent.
- **Signals** -- a pattern worth attention is visually distinct (a flagged
  point, a diverging bar), and only claimed when its framing's guardrail holds
  (see `framing-signal-vs-noise.md`).
- **Driver relationships** -- top-line results are connected to their likely
  causes (the "why/where" stage links back to "what changed").
- **Action cues** -- the report says what kind of follow-up a finding implies,
  without prescribing a business decision the owner must make.

## How story order is recorded

In the narrative brief's front section (schema in `derivation-route.md`),
`story_order` is a mapping of the four stage keys (`overview`, `change`,
`why_where`, `action`) to the ordered question ids in each stage, and each
question also carries its own `stage` field. The checker verifies every
question id appears in exactly one stage, that a question's `story_order`
placement matches its `stage` field, and that `overview` is non-empty (no
orphan, no phantom, no mismatch). It does not judge the arc's quality -- that
is the named human's review.

## Anti-patterns (each is a defect the design review should catch)

- **Topic buckets**: pages named for a subject ("Sales", "Returns") with no
  decision the page answers. Fix: name the decision, order by the arc.
- **All-overview**: every page is glanceable KPIs; nothing localizes a cause.
  Fix: earn the "why/where" stage.
- **Bare totals**: a headline number with no comparison. Fix: every overview
  measure carries a comparison (`framing-period-variance.md` /
  `framing-benchmark-threshold.md`).
- **Buried lede**: the most decision-relevant finding is last or smallest.
  Fix: priority element -- rank drives position.
