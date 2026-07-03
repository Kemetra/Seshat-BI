# Quickstart: Run-Next Readiness State Machine

This is a spec/plan-stage quickstart: it describes how a future implementation
will be invoked and validated. No code ships in this slice; this document is
the acceptance script a future implementation slice must satisfy.

## What this is for

You have a table somewhere in the seven-stage readiness spine and you want one
question answered: **"what is the single next allowed action, or why am I
stopped?"** -- without trusting a possibly-stale stored string, and without
anything being executed or approved on your behalf.

## How to invoke it (once implemented)

As an agent-facing skill (the default delivery shape; see plan.md Assumption
A7), invocation looks like a natural-language ask:

```text
"What's the next allowed action for silver.example_table?"
"Is silver.example_table blocked? Why?"
"Can I proceed to silver for silver.example_table yet?"
```

The agent reads `mappings/example_table/readiness-status.yaml`, applies the
stage-order walk (`data-model.md` "State Transitions"), and replies using the
shape in `contracts/run-next-response.md` -- in prose, not necessarily as raw
YAML, when talking to a human.

## Fixture-based validation a future implementation MUST pass

Each fixture below is a MINIMAL `readiness-status.yaml` excerpt (only the
fields relevant to the case are shown; a real fixture file fills in the rest
per the template). These map 1:1 onto spec.md's User Stories, Acceptance
Scenarios, and Edge Cases.

| # | Fixture shape | Expected `outcome` | Source requirement |
|---|----------------|---------------------|----------------------|
| 1 | `source_ready: pass`, rest `not_started` | `next_action` @ `mapping_ready` | US1 scenario 1 |
| 2 | `mapping_ready: blocked` + `blocking_reasons: [...]` | `stop_blocked` @ `mapping_ready`, reasons verbatim | US1 scenario 2 |
| 3 | stages 1-6 `pass` (approved), `publish_ready: not_started` | `approval_required` is NOT yet the case here -- `publish_ready` is `not_started`, so first confirm this returns `next_action` @ `publish_ready`... **unless** the immediately-preceding approval-required stage (`dashboard_ready`) itself lacks a valid approval, in which case `approval_required` @ `dashboard_ready` | US1 scenario 3 (see note below) |
| 4 | `mapping_ready: pass`, `approvals[]` has a bare-role owner for it | `approval_required` @ `mapping_ready`, never `next_action` past it | US2 scenario 1 |
| 5 | full chain `pass` through `dashboard_ready` with valid approvals | `next_action` or `approval_required` @ `publish_ready` depending on whether that stage's own approval is separately required before entry (it is NOT -- `publish_ready` itself is the stage being entered, so this is `next_action` unless a `publish_ready` approval is ALSO a precondition to even starting the handoff review; see stage doc) | US2 scenario 2 |
| 6 | `gold_ready: pass`, `evidence: []` | whatever outcome the rest of the chain implies, PLUS a `pass_without_evidence` caveat naming `gold_ready` | US3 scenario 2 |
| 7 | stored `next_action` names `silver_ready`, computed answer is `mapping_ready` | response includes BOTH values + a `next_action_disagreement` caveat | US3 scenario 1 |
| 8 | no `mappings/<table>/readiness-status.yaml` file at all | `next_action` @ `source_ready`, text = "no readiness file found; start onboarding" | Edge case: missing file |
| 9 | file exists, invalid YAML | `input_defect`, `stage: null`, detail = "readiness file incomplete/unparseable" | Edge case: malformed file |
| 10 | `current_stage: gold_ready` but `silver_ready.status: blocked` | `stop_blocked` @ `silver_ready` (computed from stage order, NOT from the stale `current_stage` label) + a conflict caveat | Edge case: current_stage disagreement |
| 11 | all seven stages `pass`, all approvals valid | `terminal_pass`, `stage: null` | Edge case: all-pass terminal |
| 12 | a stage status is `"done"` (not a recognized value) | `input_defect` naming that stage | Edge case: invalid status string |
| 13 | earliest non-pass stage is `warning` | `next_action` for that stage's own next-step text, plus a `warning_carried_forward` caveat | Edge case: warning non-blocking |
| 14 | two different stages both `blocked` | `stop_blocked` @ the EARLIER of the two, plus a `dual_blocked` caveat naming the later one | Edge case: dual blocked |
| 15 | `source_ready` declares `source_kind: csv`, is `pass`, no matching `source_ready` approval | `approval_required` @ `source_ready` (the file-source special case) | Edge case: file-source approval |

**Note on fixture #3/#5 ambiguity -- RESOLVED (2026-07-03, implementation slice).**
Whether an approval-required stage's OWN approval gates ENTRY into that stage or
only gates LEAVING it once it reaches `pass` is now settled, consistent with how
RS1 actually treats it: RS1 checks a stage's approval requirement only when that
stage's OWN status is `pass` (the approval check lives inside the `status ==
"pass"` block of `src/retail/rules/readiness_status.py`; verified against the
current source at build time). This feature mirrors that exactly -- the approval
check fires when we are ABOUT to treat a `pass` stage as cleared for moving on
(an approval-required stage recorded `pass` without a shape-valid approval is
`approval_required`, never silently passed through), NOT as a precondition to
starting a `not_started` stage. Concretely for the two fixtures:

- **Fixture #3** (`us1_publish_next.yaml`): `publish_ready` is `not_started`, so it
  is the earliest non-`pass` stage and the walk returns its forward `next_action`.
  The publish approval gates the transition of `publish_ready` TO `pass`, not
  entry into the stage -- so no `approval_required` fires here. (This is the
  owner-ratified reading (a) recorded in spec.md Assumption A5 /
  NEEDS-CLARIFICATION-1.)
- **Fixture #5** (`us2_approved_chain.yaml`): every `pass` stage through
  `dashboard_ready` carries a shape-valid approval, so none of them trip the
  pass-branch approval check; the walk reaches `publish_ready` (`not_started`) and
  returns `next_action`.

Both encoded in the shipped fixtures under `tests/fixtures/readiness/run_next/`;
the SKILL.md walk and its "Verified fixtures" table match this resolution. The
"state machine" ENTER-vs-ADVANCE-PAST ambiguity no longer exists as an open
question.

## Read-only proof procedure

After running any fixture (real or manual) against a future implementation:

```bash
git status --short
```

Expected output: empty (no lines). If any file appears, the implementation
has violated FR-006/NG-... and must be fixed before this feature can be
considered done, regardless of whether the reported `outcome` was otherwise
correct.

## Non-goals reminder (do not extend scope while validating)

While building fixtures for the fifteen cases above, do NOT:
- add a fixture that expects the surface to WRITE anything (there is no such
  case; if you find yourself writing one, you have drifted from the spec).
- add a fixture that expects cross-table output (single-table only; NG-003).
- add a fixture that expects a numeric score field anywhere in the response
  (NG-009).
