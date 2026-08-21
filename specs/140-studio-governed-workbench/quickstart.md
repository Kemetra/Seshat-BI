# Quickstart: Studio Governed Analyst Workbench (spec 140)

**This feature is not implemented.** This file describes the intended journey so a
reviewer can judge the specification, and so implementers have an acceptance script.
Nothing here works today.

## Prerequisites

- Seshat installed with app extras (`pip install "seshat-bi[app]"`), as spec 139.
- A workspace with at least one onboarded table and cleared mapping.
- Studio running: `seshat studio` (Foundation behaviour, unchanged).

## Journey 1 -- Investigate a table (US1)

1. Open Studio, land on the Command Room, pick a table.
2. The table journey shows the seven readiness stages, each with evidence links.
3. Any missing or malformed evidence shows as a **defect**, not an empty pass.
4. Live numbers show `[PENDING LIVE PROFILE]` when no DSN is configured.

**Acceptance**: every displayed claim links to a committed source, or is explicitly
marked pending-live. Nothing is unattributed.

## Journey 2 -- Review a proposed change (US2)

1. Ask the agent, in business language, to prepare a mapping or metric change.
2. Studio shows a `ChangeProposal`: exact diff, per-field provenance, impact, and the
   validation result from the existing engines.
3. Each field is labelled `discovered_fact`, `existing_decision`, `default`,
   `inference`, or `new_human_judgment`.
4. If a gate fails or the stage is forbidden, no approval control appears at all.

**Acceptance**: you can see exactly what would change, and which parts are guesses
rather than established facts, before anything is offered for approval.

## Journey 3 -- Record a business decision (US3)

1. The proposal names the business question and the authority class required.
2. **You** type the signer (`Ahmed Shaaban (owner)`), pick the answer, and submit. The
   agent cannot pre-fill any of these.
3. Studio validates through the shipped predicates and appends to
   `.seshat/semantic-decisions.yaml`.
4. The result shows **`pending commit`**, with the file path and a note that the gate
   reads committed state.
5. Readiness has **not** moved. This is correct, not a bug.
6. Review the diff yourself and commit it:

   ```bash
   git diff .seshat/semantic-decisions.yaml
   git add .seshat/semantic-decisions.yaml
   git commit -m "decision: <what was decided>"
   ```

7. Reload. Readiness now reflects the decision.

**Acceptance**: step 5 shows no stage advancing, and step 7 shows it advancing. If
step 5 advances a stage, the write boundary is broken. If step 7 does not, readiness is
not reading `HEAD`.

## Journey 4 -- Apply a change (US4, P2)

1. With the decision committed, request apply.
2. Studio applies only the reviewed scope and shows an `ApplyReceipt` with static
   verification, optional live verification, and remaining blockers.
3. Static success is labelled necessary, not sufficient.

**Acceptance**: attempting apply while the decision is only `pending commit` is
refused. Attempting to widen the scope is refused.

## Journey 5 -- Client review scope (US5, P3)

1. Open a scoped review in the same local session.
2. The reviewer sees only decisions requiring their authority, with question, choices,
   provenance, and affected scope.
3. Decline and request-clarification are always available.
4. No tool-approval or unrelated artifact controls are reachable.

**Acceptance**: nothing outside the selected scope is visible or reachable.

## What to check if you are reviewing this specification

The single question that matters: **can any sequence of steps make a decision
authoritative without a human running `git commit`?** If yes, the feature is unsafe
regardless of how the UI reads. See `contracts/decision-write-boundary.md`.
