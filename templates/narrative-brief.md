# Narrative brief -- <table id>

<!--
  GENERIC TEMPLATE (roadmap rule 7). Copy this blank to
  `mappings/<table>/narrative-brief.md` and fill the placeholders. This is the
  FIRST step of Stage 6 design -- author it BEFORE any layout or visual work.

  <table> IS A PLACEHOLDER, NEVER AN EXAMPLE INLINED HERE. Do NOT copy any
  per-client or worked-example specifics into this file. ASCII, UTF-8 no BOM.
  No real connection host, no secret, no PII.

  WHAT THIS IS
    The reviewable output of the `bi-analyst-knowledge` derivation route: two
    committed artifacts (approved metric contracts + the committed
    source-profile) turned into ranked, grounded decision-questions and a story
    arc. It has a MACHINE-READABLE front section (the fenced `yaml` block below,
    which `seshat narrative-check` parses) followed by a HUMAN-FIRST body.
    Consumers read the front section; the named human reviewer reads the body.

  THE TWO-INPUT RULE (do not drift)
    A decision-question may reference ONLY measures, dimensions, and facts
    present in (1) the approved contracts and (2) the committed source-profile.
    If answering a question needs a measure/column/feed that is not there, it is
    NOT a question -- it is a `gaps[]` entry. Never reach past the committed
    evidence to invent an answerable question.

  WHO FILLS THIS
    An ANALYST/OWNER authors it. Choosing the decision-questions, each
    question's framing, the story order, and the callouts are Principle-V
    judgment calls -- an agent MUST NOT self-author or self-approve them. The
    checker asserts the brief obeys its own frozen schema; it never judges
    whether a question is the RIGHT question. A clean `narrative-check` is
    EVIDENCE FOR the named human design review, never a substitute for it.

  VERIFY BEFORE REVIEW
    seshat narrative-check --table <table> --report .
-->

```yaml
# narrative-brief front section -- FROZEN schema seshat.narrative-brief/v1.
# Every key below is REQUIRED unless its comment says optional.
schema: seshat.narrative-brief/v1      # exact literal; do NOT edit or bump
table: <table id>                      # MUST match the mappings/<table>/ dir holding this brief
source_profile: mappings/<table>/source-profile.md   # the cited committed profile

contracts:                             # every approved contract this brief may cite
  - id: <ContractName>                 # resolves to mappings/<table>/metrics/<ContractName>.yaml
    revision: <blob-sha>               # STALE-CITATION GUARD -- must equal the contract's
                                       #   CURRENT blob: `git hash-object
                                       #   mappings/<table>/metrics/<ContractName>.yaml`
                                       #   Re-stamp it whenever the contract changes.

questions:                             # RANKED: index order IS the rank (owner priority x data strength)
  - id: Q1                             # stable id; the binding map references it
    decision: <the owner decision this answers, ONE sentence>
                                       #   Phrase as a DECISION ("where do I push spend"),
                                       #   never as a metric request ("show TotalSales by x").
    stage: overview                    # one of: overview | change | why_where | action
    framing: <framing-card-id>         # one of the EIGHT framing cards (framing-*.md):
                                       #   benchmark-threshold | concentration | contribution-mix
                                       #   period-variance | rate-decomposition | segment-behavior
                                       #   signal-vs-noise | trend-anomaly
    cites:
      measures: [<ContractName>]       # GROUNDED: every id MUST appear in `contracts` above
      dimensions: [<entity.attribute>] # dotted semantic-model refs; NOT ground-checked in v1
    comparison: <named comparison>     # REQUIRED to be a NAMED value when stage == overview
                                       #   (headline rule): "none" is allowed ONLY off-overview.
    guardrail:                         # REQUIRED when `framing` is a guardrail-bearing card
                                       #   (trend-anomaly, period-variance, concentration,
                                       #    segment-behavior, benchmark-threshold,
                                       #    signal-vs-noise). OMIT for the other framings.
      basis: <named basis>             #   e.g. "same week last year", "portfolio average", "plan"
      window: <stated window>          #   optional; band/trend framings, e.g. "trailing 13 weeks, k=2"
      min_sample_floor: <count>        #   optional; rate framings (below -> insufficient-sample)
    callout: <the so-what sentence>    # REQUIRED: the finding this question yields, ONE sentence

story_order:                           # the arc. ALL FOUR keys MUST be present, in this order.
  overview:  [Q1]                      #   MUST be non-empty -- a report with no overview is a defect.
  change:    []                        #   A stage may be empty ([]), but the key must exist.
  why_where: []                        #   Every question id appears in EXACTLY ONE stage, and the
  action:    []                        #   stage here MUST equal that question's own `stage` field.

gaps:                                  # key REQUIRED; the list MAY be empty ([])
  - question: <the owner decision the data cannot answer>
    missing_source_fact: <the absent column/feed>
    unlocking_feed: <what would answer it later>
                                       #   A gap MUST NOT also appear as a `questions[]` entry --
                                       #   you cannot frame what you cannot answer.
```

## <Q1 -- the decision, in the owner's words>

<!--
  HUMAN-FIRST BODY (required: prose MUST follow the front section, and a fenced
  block alone does not count). One short section per question: the decision, why
  it matters to this audience, what the framing compares against, and the
  intended callout expanded into plain language. This is what the named human
  reviews.
-->

<Why this decision matters to the stated audience, what the framing compares
against and why that basis was chosen, and the so-what the reader should leave
with. Name the caveat if the underlying data carries one.>

## Gaps

<Each `gaps[]` entry in prose: the decision the owner wants, the specific fact
the source does not carry, and the feed that would unlock it. A gap is a
first-class output, not an omission -- record it rather than dropping it.>

## Review

- **Authored by:** <analyst name, date>
- **Reviewed by:** <named human reviewer, date>  <!-- LEAVE EMPTY until the real review happens -->

<!--
  The reviewer line is a Principle-V seam. An agent NEVER fills it, and
  `narrative-check` NEVER grants the approval it records.
-->
