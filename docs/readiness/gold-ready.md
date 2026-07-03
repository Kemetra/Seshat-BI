# Gold Ready

Status note: Planning (docs/templates; no runtime code).

## Purpose

Stage 4. The Kimball gold star is built AND live-validated -- the hard gate
before Power BI. "Ready" means the fact + conformed dimensions exist, pass the
static gold checks, and a live read-only validate proves the data is correct:
keys unique, dates contiguous, no orphan FKs, and silver<->gold reconciliation
penny-exact. Maps to playbook Phase 6.

## Required artifacts

| Artifact | Must contain |
|----------|--------------|
| `warehouse/migrations/NNNN_create_gold_<table>_star.sql` | fact + conformed dims; `-1` unknown member in each dim; `COALESCE` on FK joins to the unknown member; contiguous `generate_series` date dimension |
| `mappings/<table>/reconciliation-report.md` | FILLED (not template stub) -- silver<->gold totals reconciled penny-exact, with the queries/figures recorded |

Numbering is contiguous and idempotent (see conventions). The reconciliation
report must be a filled instance, not the blank template.

## Required checks

| Gate | What it proves here |
|------|---------------------|
| `retail check` (static) | S6 -> `-1` unknown member present; S7 -> date dim built via `generate_series` (contiguous) |
| `retail validate` (LIVE, read-only) | RC2 -> PK/grain uniqueness; RC15 -> date coverage; RC16 -> 0 orphan FKs AND penny-exact silver<->gold reconciliation |

Live validate needs the `db` extra installed and a DSN. With neither, the stage
is `blocked` in deferred mode -> report the boundary, never fake a pass. Static
`retail check` exit 0 alone is NOT proof of correctness.

## Statuses

| Status | Meaning here |
|--------|--------------|
| `not_started` | silver_ready is not `pass`, or no gold migration exists yet |
| `blocked` | a live finding (V-RC2 / V-RC15 / V-RC16), reconciliation not penny-exact, OR no DSN / no `db` extra (blocked-deferred) |
| `warning` | a non-fatal static WARN recorded; never used to mask a live finding |
| `pass` | static gold checks pass AND live validate passes (RC2/RC15/RC16) AND reconciliation is penny-exact, with evidence recorded |

## Blocking reasons

- Prior stage not `pass`: `silver_ready` is not `pass`.
- Live finding open: V-RC2 (duplicate grain), V-RC15 (date gap), or V-RC16
  (orphan FK) reported by `retail validate`.
- Reconciliation not penny-exact: silver<->gold totals differ by any amount.
- Deferred boundary: no DSN configured or `db` extra not installed
  (blocked-deferred) -- record it, do not infer a pass.

## Required owner / approval

None -- mechanical. The live validate findings are objective; a clean run is the
sign-off. No human approval is added at this stage.

## Next allowed action

When `pass`: build the semantic model -> Stage 5 (Semantic Model Ready).

## What the agent must NOT do

- Point Power BI at the gold star before `retail validate` passes (Principle VIII
  hard gate).
- Treat `retail check` exit 0 alone as proof of correctness.
- Emit a `pass` while in deferred mode (no DSN / no `db` extra) -- report
  blocked-deferred instead.
- Fabricate or round reconciliation figures to reach penny-exact.
- Skip ahead to dashboard or publish work.

## See also

- The state model: `readiness-model.md`
- The stage sequence + hard gates: `readiness-pipeline.md`
- Reconciliation template (point-in-time snapshot): `../../templates/reconciliation-report.md`
- Reconciliation ledger (durable history over time): `../../templates/reconciliation-ledger-entry.md`
- Live validate gate: `../../.claude/skills/retail-validate/SKILL.md`
- First filled instance (worked example): a filled worked example under `../../docs/worked-examples/`
