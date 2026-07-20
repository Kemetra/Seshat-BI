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

No numeric score or confidence is emitted. The source of truth remains the
readiness status file; this command only explains what is already recorded.
