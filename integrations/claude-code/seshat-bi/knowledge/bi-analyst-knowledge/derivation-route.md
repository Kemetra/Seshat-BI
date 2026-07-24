# Derivation route: contracts + source-profile -> ranked decision-questions

This route turns two committed artifacts into a reviewable narrative brief. It
is the FIRST step of Stage 6 design -- run it before any layout or visual work.

## Inputs (exactly two; nothing else)

1. **Approved metric contracts** for the table (F009), each with a `pass`
   `semantic_model_ready` gate.
2. The **committed source-profile** for the table
   (`mappings/<table>/source-profile.md`): the measured facts about what the
   data contains (columns, cardinalities, missingness, grain, date span,
   authoritative flags).

**Grounded-only rule.** A decision-question may reference ONLY measures,
dimensions, and facts present in those two artifacts. If answering a question
needs a measure/column/fact that is not there, it is not a question -- it is a
[GAP] (see below). You never reach past the committed evidence to invent an
answerable question.

## Procedure

1. **List the decisions the owner can act on.** For each approved contract and
   each profiled dimension, ask: "what decision does knowing this change?"
   Phrase as a decision, not a metric ("where do I push spend", not "show
   TotalSales by division").
2. **Keep only grounded, actionable questions.** Drop questions the data
   cannot answer (-> [GAP]) and questions that inform no decision (vanity).
3. **Rank by owner priority x data strength.** A question the owner acts on
   weekly, answerable with a strong measure over a well-populated dimension,
   ranks above a monthly one over a sparse dimension.
4. **Assign one framing per question** from the catalog (`framing-*.md`). The
   framing determines the comparison and the guardrail, not just the visual.
5. **Order the questions into a story** using `story-order.md`
   (overview -> what changed -> why/where -> action).
6. **Record [GAP]s explicitly** (see format). A [GAP] is a first-class output,
   not an omission.

## [GAP] format (an unanswerable question is a first-class output)

Each [GAP] states three things and stops:

- **Question**: the owner decision it would inform.
- **Missing source fact**: the specific column/feed the committed evidence
  lacks (e.g. "no unit-cost column", "no inventory snapshot", "no target
  feed").
- **Unlocking feed**: what would have to be added to answer it later.

A [GAP] never becomes a visual. It is the honest boundary of the analysis and
feeds the absent-KPI/data roadmap.

## The narrative-brief schema (FROZEN -- the shared contract)

The brief lives at `mappings/<table>/narrative-brief.md`. It has a
**machine-readable front section** (a fenced `yaml` block, so the
`narrative-check` verb parses structure without NLP) followed by a
**human-first body**. Consumers (the `dashboard-design` skill and
`seshat narrative-check`) read the front section; humans read the body.

Front-section keys (all required unless marked optional):

```yaml
# narrative-brief front section -- FROZEN schema (spec 021-analyst-narrative-layer, T002)
schema: seshat.narrative-brief/v1      # exact literal; version bump = new contract
table: <table id>                      # matches mappings/<table>/
source_profile: mappings/<table>/source-profile.md   # the cited profile path
contracts:                             # every approved contract this brief may cite
  - id: <ContractName>                 # matches the approved metric contract
    revision: <git blob sha of the committed contract>   # stale-citation guard
questions:                             # ranked; index order IS the rank (priority element)
  - id: Q1                             # stable id, referenced by the binding map
    decision: <the owner decision, one sentence>
    stage: overview                    # REQUIRED: overview | change | why_where | action
                                       #   (the arc stage this question serves; drives story order + headline rule)
    framing: <framing-card-id>         # one of the eight; see framing-*.md
    cites:                             # only ids present in `contracts`/profile dims
      measures: [<ContractName>, ...]
      dimensions: [<dim.attribute>, ...]
    comparison: <named comparison>     # REQUIRED to be a named value when stage == overview
                                       #   (headline); "none" allowed only for non-overview stages
    guardrail:                         # REQUIRED when `framing` is a guardrail-bearing card
                                       #   (trend-anomaly, period-variance, concentration,
                                       #    segment-behavior, benchmark-threshold, signal-vs-noise);
                                       #   omit for framings that carry no guardrail.
      basis: <named basis>             #   e.g. "same week last year", "portfolio average", "plan"
      window: <stated window>          #   optional; for band/trend framings (e.g. "trailing 13 weeks, k=2")
      min_sample_floor: <count>        #   optional; for rate framings (below -> insufficient-sample)
    callout: <the so-what sentence>    # REQUIRED: the finding this question yields, one sentence
story_order:                           # REQUIRED: the arc. Keys are the four stages, in this order;
  overview:  [Q<n>, ...]               #   each value is the ordered question ids in that stage.
  change:    [Q<n>, ...]               #   A stage may be empty ([]) but all four keys MUST be present.
  why_where: [Q<n>, ...]               #   Every question id MUST appear in exactly one stage, and its
  action:    [Q<n>, ...]               #   stage here MUST equal that question's `stage` field.
gaps:                                  # may be empty, but the key MUST be present
  - question: <owner decision>
    missing_source_fact: <the absent column/feed>
    unlocking_feed: <what would answer it later>
```

Body (human-first, after the front section): a short prose narrative per
question -- the decision, why it matters, the framing's so-what, and the
intended callout expanded. The body is what the named human reviews; the front
section is what the machine checks.

## Rules the checker enforces against this schema

- Every `questions[].cites` id MUST appear in `contracts` or the profile's
  dimensions (grounded-only).
- Every `contracts[].revision` MUST match the committed contract's current
  blob sha, or the citation is STALE (same posture as dbt model citations).
- `questions[].stage` MUST be one of the four literals; `questions[].callout`
  MUST be a non-empty sentence.
- `story_order` MUST have all four stage keys; every question id appears in
  exactly one stage; a question's `story_order` stage MUST equal its own
  `stage` field (no orphan id, no phantom id, no stage mismatch). The
  `overview` stage MUST be non-empty (a report with no overtable is a defect).
- **Headline rule (FR-006)**: every `stage: overview` question MUST set
  `comparison` to a named value, never "none" -- a bare-total headline is a
  defect.
- **Guardrail rule (FR-002a)**: when `framing` is a guardrail-bearing card,
  the `guardrail.basis` MUST be a named value -- an anomaly/variance/rate/
  threshold claim with no stated basis is a defect (the checker asserts the
  basis is PRESENT; it does not judge whether the basis is wise -- that is the
  human review).
- `gaps` MUST be present (empty list allowed); a [GAP] MUST NOT also appear as
  a question with a framing (you cannot frame what you cannot answer).

## The five decision-driven elements: what is CHECKABLE vs human-review

`story-order.md` names five elements. Their enforcement split is explicit so
the checker's scope is unambiguous:

- **Priority** -- CHECKABLE: `questions` index order is the rank.
- **Thresholds** -- CHECKABLE (partial): `guardrail.basis`/`min_sample_floor`
  capture the named basis when a guardrail framing is used.
- **Signals** -- CHECKABLE (partial): a `signal-vs-noise` or `trend-anomaly`
  framing with a stated `guardrail.basis` is the structural hook.
- **Driver relationships** -- HUMAN-REVIEW ONLY: whether the `why_where` stage
  actually explains the `change` stage is a judgment the checker does not make.
- **Action cues** -- HUMAN-REVIEW ONLY: whether `action`-stage callouts imply a
  real follow-up is a judgment the checker does not make.

## What this route does NOT do

- It does not define metric meaning (contracts + domain packs own that).
- It does not author layout or pick visual pixel geometry (that is the
  `dashboard-design` skill, gated on this brief existing).
- It does not grant any readiness or approval.
