# KPI Sufficiency and Policy Decisions

Use this resource to decide what kind of artifact can be produced from the available evidence. It
does not approve a KPI, grant readiness, or fill an owner-policy gap.

## Inputs

- candidate KPI and stable registry identity, if one exists;
- source-field/profile evidence and logical-field bindings;
- ambiguity ledger and relevant upstream contracts;
- named authority eligible to make each policy decision;
- affected downstream contracts, transformations, measures, and reports.

## Closed sufficiency statuses

Use exactly one:

- `answerable`: required meaning, fields, grain, policies, and validation evidence are present;
- `blocked_by_source`: meaning is settled but a required field, grain fact, coverage fact, or
  binding is absent or contradicted;
- `blocked_by_policy`: source evidence may exist, but an authorized owner decision is missing;
- `not_applicable`: the KPI does not apply to the stated business process or scope, with evidence.

These are knowledge-layer findings. They are not readiness stages, scores, approvals, or execution
authorizations.

## Sufficiency sequence

1. Name the KPI, contract revision, question, output grain, and intended decision.
2. Check business definition, formula in business terms, additivity, time behavior, filters, and
   exclusions.
3. Check required logical source fields against supplied evidence.
4. Check all number-moving ambiguities and policy slots.
5. Identify the named authority for unresolved policy.
6. Choose one categorical status and list concrete evidence/blockers.
7. End on one artifact:
   - implementation handoff when `answerable`;
   - source-evidence request when `blocked_by_source`;
   - owner decision packet when `blocked_by_policy`;
   - applicability record when `not_applicable`.

## Owner policy decision packet

One packet covers one decision. Record:

| Field | Requirement |
|---|---|
| Decision ID | stable ambiguity or policy-slot identifier |
| Question | one choice the authority can answer |
| Business consequence | which populations/numbers change and why |
| Available evidence | profiles, contracts, prior rulings, reconciliations |
| Alternatives | finite options stated neutrally |
| Refutation evidence | what would disprove or invalidate each option |
| Named authority | role/person eligible to decide; never the agent |
| Downstream artifacts affected | contract IDs, derivation descendants, SQL/DAX/Python/BigData handoffs, reports |
| Required receipt | where the human ruling and evidence must be recorded |

Do not select a recommended alternative when the choice is owner-governed. You may explain
consequences and missing evidence, then stop at `../checklists/kpi-policy-decision-checklist.md`.

## Same-store example

`KPI-MC-12` remains `planned` with two independent policy blockers:

- `A11`: comparable-store membership policy;
- `comparison-period-policy`: baseline/comparable-period policy.

Resolving one does not resolve the other. Until both approved receipts exist, the packet may become
more precise, but the generic contract is not promoted and no implementation handoff is emitted.
