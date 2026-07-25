# Narrative Change Review

Use when a contract revision or source-profile drift may invalidate a committed narrative brief.
This is a citation-and-judgment review, not a rewrite of metric meaning or dashboard layout.

## Required evidence

- prior narrative brief revision and its cited contract/profile revisions;
- current contract blob SHAs and committed source-profile blob SHA;
- semantic meaning/diff notes supplied by the contract or source owner;
- affected question IDs, framings, comparisons, guardrails, gaps, and downstream binding refs.

## Review procedure

1. Compare prior and current revisions; distinguish content change from ref-only refresh.
2. For a contract change, trace every question that cites the contract.
3. For source drift, trace questions whose cited dimensions, coverage, date span, or grain evidence
   changed.
4. Decide whether the owner decision, comparison, guardrail, callout, story stage, or `[GAP]`
   status still holds.
5. Record affected questions and exact reason; do not silently rewrite a contract or metric.
6. Route a meaning change to `retail-kpi-knowledge`; route an unanswerable question to `[GAP]`.

## Closed verdicts

- `unchanged`: revisions are current and evidence shows no question/framing consequence;
- `revise`: evidence identifies specific questions, framings, comparisons, guardrails, callouts,
  or gaps that must change;
- `blocked`: revision evidence is missing, meaning is unresolved, or the current profile cannot
  support the question.

## Terminal narrative-change verdict

```yaml
verdict: unchanged | revise | blocked
prior_brief_revision: ""
prior_contract_revisions: {}
current_contract_revisions: {}
prior_source_profile_revision: ""
current_source_profile_revision: ""
affected_questions:
  - id: ""
    affected_fields: []
    evidence: []
    required_change: ""
blockers: []
next_action: ""
```

Validate the result with `checklists/narrative-judgment-review-checklist.md`. The verdict is not a
readiness pass or design approval.
