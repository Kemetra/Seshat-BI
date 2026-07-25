# Diagnostic Question Tree

Use when an approved headline changes and the owner needs a grounded investigation sequence before
layout or visual design.

## Inputs

- approved metric contracts with current revisions;
- committed source profile and available dimensions;
- headline question, comparison, period, and guardrail from the narrative brief;
- named owner decision the investigation is meant to inform.

Every node cites at least one approved contract and only dimensions evidenced by the profile/model
references already admitted by the narrative brief. An unavailable node becomes `[GAP]`; it is
never populated with an invented metric or dimension.

## Sequence

### 1. Overview -- did the approved headline move?

Restate the approved measure, output grain, comparison basis, period, and guardrail. Confirm that
the observed change is not a stale contract/profile citation or an incomplete comparison period.

### 2. Change -- what component of the approved result changed?

Use only approved base components or comparisons already supported by contracts. Separate level,
rate, mix, and period effects without introducing a new KPI.

### 3. Driver -- which available dimension accounts for the change?

Test dimensions evidenced as usable and relevant to the owner's decision. Rank candidates by
decision relevance first, then by evidence coverage. Do not assign a numeric importance score.

### 4. Segment -- where is behavior materially different?

Compare grounded segments with the applicable sample/coverage guardrail. If the required segment
attribute or denominator is absent, emit `[GAP]`.

### 5. Exception -- which entities or periods need review?

Identify exceptions only under a named threshold, benchmark, or signal-vs-noise rule from the
brief. "Largest" is descriptive; "problem" requires an approved basis.

### 6. Action -- what named decision can the owner take?

Connect the supported finding to a decision, trigger, and evidence refresh. If no named owner or
decision exists, hand off to `action-and-review-cadence.md` and remain blocked.

## Node format

```yaml
node:
  stage: overview | change | driver | segment | exception | action
  question: ""
  owner_decision: ""
  contract_citations: []
  available_dimensions: []
  comparison_or_guardrail: ""
  evidence: []
  result: supported | no_material_change | insufficient_evidence | gap
  next_nodes: []
  gap:
    missing_source_fact: ""
    unlocking_feed: ""
```

## Terminal diagnostic question tree

Return the six-stage tree, ordered by owner decision relevance and evidence availability, plus
explicit `[GAP]` nodes. End by reviewing it with
`checklists/narrative-judgment-review-checklist.md`.

