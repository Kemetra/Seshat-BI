---
name: bi-analyst-knowledge
description: >-
  Analyst-judgment layer for Seshat BI Stage-6 design. Use when turning approved metric
  contracts + a committed source-profile into a decision-driven report: deriving ranked
  decision-questions, choosing an analytical framing (trend/anomaly, period variance,
  contribution & mix-shift, concentration/Pareto, rate decomposition, segment behavior,
  benchmark/threshold, signal-vs-noise statistical guardrails), and ordering pages into a
  story (overview, what changed, why/where, action), building grounded diagnostic
  question trees, reviewing narrative drift, and defining action/review-cadence handoffs
  BEFORE layout. It teaches HOW to frame approved numbers, never WHAT a metric means. A
  thinking layer, not a layout engine, chart renderer, metric definer, or owner assigner.
---

# BI Analyst Knowledge (Seshat BI)

The judgment layer that turns a structurally-correct report into an ANALYSIS. It
sits between semantic-model readiness (F010) and dashboard layout (F011): given
approved contracts and a profiled source, it produces the decision-questions,
framings, and story order a good analyst would -- so a page answers a decision
instead of merely displaying a number.

This file is short by design. **It does not contain the knowledge base.** Do not
read every file. Follow the flow.

## Mandatory flow (do not skip a step)

```text
this SKILL.md  ->  INDEX.md  ->  ONLY the route(s) named  ->  narrative brief / [GAP] / handoff
```

1. **Open `INDEX.md` first.** It routes by task and by symptom.
2. **Read only what the route names** -- the derivation route, one or two framing
   cards, the story-order rule. Reading the whole pack is an anti-pattern.
3. **Ground in the two committed inputs only** -- approved metric contracts and the
   committed source-profile. A question that reaches past them is a [GAP], not a
   question.
4. **End on an artifact:** a committed narrative brief conforming to
   `derivation-route.md`'s frozen schema, a [GAP] entry, or a framing handoff to
   `dashboard-design`. Never end on prose alone.

## What this skill is for

Deriving ranked decision-questions from approved contracts + profile; choosing the
analytical framing per question; attaching statistical guardrails (control bands,
seasonality-aware comparison, minimum-sample caveats, correlation caution);
ordering questions into a story; and recording unanswerable owner questions as
honest [GAP]s. It also diagnoses headline changes, reviews contract/profile revision
impact on an existing brief, and structures a supplied owner/cadence handoff. Its output
is the narrative brief and review evidence `dashboard-design` needs before layout.

## What this skill is NOT for

Not metric definition (contracts + domain packs own meaning); not layout, pixel
geometry, or chart rendering (that is `powerbi-workflows` / `dashboard-design`);
not statistics beyond owner-grade guardrails (no regression, forecasting, or
significance testing in v1 -- those are a [GAP], routed to a human); not a
publisher; not a database executor. It frames approved numbers; it never invents
one.

## Routing boundaries (pick the right skill first)

| The task is about... | Route to |
|---|---|
| What a metric MEANS / defining a contract | `retail-kpi-knowledge` (+ metric contracts) |
| HOW to frame approved metrics into an analysis / decision-questions / story | **`bi-analyst-knowledge`** (this skill) |
| Layout, visuals, pages, themes, PBIR authoring | `powerbi-workflows` / `dashboard-design` |
| SQL grain / DAX measures | `bi-sql-knowledge` / `bi-dax-knowledge` |

Where it sits:

```text
... -> [semantic-model readiness: approved contracts + governed model]
    -> [bi-analyst-knowledge: decision-questions -> framings -> story -> narrative brief]
    -> [dashboard-design: layout FROM the brief; three-way map visual->contract->question]
```

## Stop rules

- **No metric meaning here.** Unclear definition -> route to the contract/domain
  pack; never define inline.
- **No invented numbers.** Bands, trailing averages, shares, cumulative %s are
  LABELED display derivations of approved measures -- never new metrics.
- **Unanswerable question -> [GAP].** Question + missing source fact + unlocking
  feed, then stop. Never a fabricated visual.
- **Generality.** Every card and route is domain-neutral in substance; domain
  flavor enters only via domain packs and the client's own contracts/profile.
  A domain noun may appear as a parenthetical, non-exclusive illustration in a
  card, never as a baked-in assumption; sustained walkthroughs live in the
  worked examples.
- **No self-granted pass.** A brief or a clean check is evidence for the named
  human design review, never an approval.
- **No owner invention.** Action handoffs use an already named owner role. If none exists,
  record an owner `[GAP]` and stop.
