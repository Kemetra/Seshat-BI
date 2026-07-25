# KPI Policy Decision Checklist

ID: KPI-CHK-04

## Gate

- [ ] One KPI/contract and one unresolved policy question are named.
- [ ] Current sufficiency status is `blocked_by_policy`.
- [ ] The policy changes meaning, population, time basis, or another number-moving rule.
- [ ] Named authority is eligible to decide; the agent is not the authority.

## Packet quality

- [ ] Decision ID is stable and traceable to the ambiguity/registry/contract.
- [ ] Business consequence states which numbers or populations change.
- [ ] Available evidence is cited; unknowns are explicit.
- [ ] Alternatives are finite, neutral, and mutually distinguishable.
- [ ] Refutation evidence is stated for each alternative.
- [ ] Downstream artifacts and derivation descendants are listed.
- [ ] Required approval receipt location is named.
- [ ] No option is silently selected and no approval is self-granted.

## Terminal artifact

Return the completed owner decision packet plus:

- `status: blocked_by_policy`;
- concrete `blockers`;
- named `authority`;
- `next_action` to record a human ruling;
- `affected_artifacts`.

After a real receipt is supplied, re-run sufficiency. This checklist does not change lifecycle,
readiness, or implementation state.

