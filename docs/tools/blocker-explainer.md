# Blocker Explainer -- usage and boundary

- **Status:** Runtime slice shipped: `retail blockers`.
- **Authority category:** Product Module / `read-only`.

## What it does

`retail blockers` scans committed `mappings/*/readiness-status.yaml` files,
finds recorded readiness blockers and pass-stage approval defects, categorizes
them, and names the next surface to use.

```bash
retail blockers
retail blockers --format json
```

The command is read-only. It does not edit `readiness-status.yaml`, clear
`blocking_reasons[]`, add approvals, run `seshat check`, run `retail validate`,
or move any stage to `pass`.

## Categories

- `approval` -- use the approval inbox / approval request flow.
- `grain` -- resolve grain or PK certainty in the mapping review.
- `live_validation` -- configure or rerun the live validation boundary.
- `artifact` -- author the missing committed artifact.
- `readiness` -- generic blocker; ask `retail next` for the stage-specific next
  action.

## Who acts: `remediation`, `doc`, `stop_condition`

Every blocker also carries three fields answering the question that decides who
picks it up:

| Field | Meaning |
|-------|---------|
| `remediation` | `human_only` or `mechanical` -- two values, never a score |
| `doc` | the one page to read for this category |
| `stop_condition` | where an agent must stop even while acting |

- `human_only` -- **cannot** be cleared without a named human decision.
  `approval` and `grain` are always human_only: an agent must not self-grant an
  approval, and grain/PK certainty is a Principle-V judgment call.
- `mechanical` -- an agent can produce the next artifact or setup step. It does
  **not** mean the stage then clears on its own: a stage that requires approval
  still requires the named human.

These values come from a **committed allowlist** in
`src/seshat/readiness_classify.py`, keyed by the same category the classifier
already returns. They are never generated per blocker -- free-form remediation
text is exactly where an agent would begin inventing steps the governance model
does not sanction.

An **unrecognized** category fails safe to `human_only`. Defaulting it to
`mechanical` would invite an agent to act on a blocker nobody classified, so the
safe direction is always toward the human.

No numeric score or confidence is emitted. The source of truth remains the
readiness status file; this command only explains what is already recorded.
