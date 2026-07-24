# BI Analyst Knowledge Router

Route first. Each route opens the fewest files and ends on a reviewable
artifact, a named blocker, or a handoff. Do not scan the whole pack.

This pack supplies the ANALYST JUDGMENT layer for Stage 6 design (spec
021-analyst-narrative-layer,
issue #452): how to turn approved metric contracts + a committed source
profile into decision-questions, analytical framings, and a story order --
BEFORE any layout or visual work. It defines HOW to frame numbers, never WHAT
a metric means (meaning lives in metric contracts and domain packs such as
`retail-kpi-knowledge`).

## Stop rules (pack-level, apply on every route)

- **No metric meaning here.** A framing card frames an APPROVED contract; if
  the metric's definition is unclear, stop and route to the contract or the
  domain pack -- never define it inline.
- **No invented numbers.** Every number a brief or callout cites is computed
  from approved contracts over committed data. Bands and trailing averages
  are labeled display derivations of approved measures, never new metrics.
- **Unanswerable question -> [GAP].** A question the committed data cannot
  answer becomes a [GAP] entry (question + missing source fact + unlocking
  feed) and STOPS. It never becomes a visual.
- **GENERALITY RULE.** Every card and route in this pack is domain-neutral in
  substance: no framing's LOGIC assumes a vertical. Domain flavor enters only
  via domain knowledge packs and the client's own contracts/profile at
  runtime. A card MAY use a domain noun as a PARENTHETICAL, non-exclusive
  illustration (e.g. "a categorical dimension (division, channel, ...)"), but
  never as a baked-in assumption; sustained domain walkthroughs live in the
  worked examples, never in a card or route.
- **No self-granted pass.** A brief, a framing choice, or a clean check is
  evidence FOR the named human design review, never an approval.

## 1. Task routes

| Task | Open | End on |
|------|------|--------|
| Derive decision-questions for a table | `derivation-route.md` | a ranked-question set citing only approved contracts + source-profile |
| Author the narrative brief | `derivation-route.md` (schema section) | committed `mappings/<table>/narrative-brief.md` for human review |
| Pick the framing for a question | the matching `framing-*.md` card | one named card id per question in the brief |
| Order pages/zones into a story | `story-order.md` | declared story order in the brief |
| Decide if a spike/change is real | `framing-signal-vs-noise.md` | a guardrailed claim, an insufficient-sample/insufficient-history statement, or no claim |
| Frame growth vs last period | `framing-period-variance.md` | seasonality-aware variance framing |
| Frame who drives the total | `framing-contribution-mix.md` | contribution/mix-shift framing |
| Frame dependency risk | `framing-concentration.md` | Pareto/ABC concentration framing |
| Decompose a headline move | `framing-rate-decomposition.md` | driver-rate decomposition framing |
| Compare behavior across segments | `framing-segment-behavior.md` | segment-behavior framing with min-sample guardrail |
| Set "is this good?" context | `framing-benchmark-threshold.md` | benchmark/threshold framing with named basis |
| Frame a time series | `framing-trend-anomaly.md` | trend framing; anomaly claim only if the guardrail holds |
| See the whole method on real-shaped data | `example-specialty-retail.md` | worked example (example, not schema) |
| See the method as a recurring review | `example-weekly-business-review.md` | worked example (example, not schema) |

## 2. Symptom routes

| Symptom | Open | End on |
|---------|------|--------|
| "The report is correct but says nothing" | `derivation-route.md` + `story-order.md` | a brief whose every page answers a named decision |
| "KPI cards are bare totals" | `framing-period-variance.md` + `framing-benchmark-threshold.md` | every headline carries a named comparison |
| "Visuals bound but no one knows why" | `derivation-route.md` | three-way map: visual -> contract -> question |
| "A spike was called an insight and reversed next week" | `framing-signal-vs-noise.md` | band-based claim or withheld claim |
| "A rate on a tiny slice drove a decision" | `framing-signal-vs-noise.md` (min-sample) | insufficient-sample statement |
| "Owner asked for margin/turnover we don't have" | `derivation-route.md` ([GAP] format) | [GAP] entry, not a fabricated visual |
| "Pages feel like disconnected topic buckets" | `story-order.md` | overview -> change -> why/where -> action order |

## 3. Consumers

- `dashboard-design` skill (F011): requires a committed narrative brief
  conforming to `derivation-route.md`'s schema BEFORE layout; binding map is
  three-way (visual -> contract -> question).
- `seshat narrative-check` (spec 021-analyst-narrative-layer Phase C): read-only checker over the
  brief + design guidance; fail-closed; findings are evidence, not approval.
