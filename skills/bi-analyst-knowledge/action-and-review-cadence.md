# Action and Review Cadence

Use when a supported insight lacks an explicit decision owner, trigger, evidence refresh, or review
cadence. This resource structures a handoff; it never appoints an owner.

## Required inputs

- narrative question/callout and approved contract citations;
- supported finding plus comparison/guardrail evidence;
- owner role already named by governance or supplied by the user;
- operational frequency and evidence-refresh availability.

If no owner role has been named, record `owner_role: [GAP]`, state who must name it, and stop.

## Handoff fields

| Field | Meaning |
|---|---|
| Question ID | stable narrative-brief question |
| Decision | specific choice the evidence informs |
| Owner role | supplied/named role; never agent-assigned |
| Trigger | evidence condition that calls for review/action |
| Review cadence | event-driven, daily, weekly, monthly, quarterly, etc., with rationale |
| Evidence refresh | source/contract refresh needed before review |
| Action window | when a decision remains useful |
| Escalation condition | threshold/guardrail breach, stale evidence, unresolved blocker |
| Record location | where decision/action outcome is captured |

Cadence follows decision latency and data freshness; it is not chosen merely because a report is
refreshed. A trigger is tied to a named approved measure/comparison, not a newly invented target.

## Terminal action/cadence handoff

```yaml
question_id: ""
decision: ""
owner_role: ""
trigger:
  contract_id: ""
  comparison_or_guardrail: ""
review_cadence: ""
evidence_refresh: []
action_window: ""
escalation_condition: ""
record_location: ""
blockers: []
next_action: ""
```

Review with `checklists/narrative-judgment-review-checklist.md`. This handoff does not assign work,
approve a design, or execute an action.

