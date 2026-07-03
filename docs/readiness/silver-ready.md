# Silver Ready

Status note: Planning (docs/templates; no runtime code).

## Purpose

Stage 3. The typed/cleaned silver table for `<schema>.<table>` is authored as a
migration and is statically clean. "Ready" here means the migration .sql exists,
was generated from the CLEARED source map (Stage 2 `pass`), follows the
load-bearing Phase-5 column/transform order, and passes `retail check`. This is
authoring only -- applying the SQL to Postgres is the deferred DB-write seam and
is out of scope (a human applies). Maps to playbook Phase 5.

## Required artifacts

| Artifact | Notes |
|----------|-------|
| `warehouse/migrations/NNNN_create_silver_<table>.sql` | Authored by the `retail-build-warehouse` skill from the CLEARED map; numbered, idempotent. Phase-5 order is load-bearing. |
| CLEARED map (from Stage 2) | `source-map.yaml` with `Gate status: CLEARED` -- the input the migration is derived from. |

First filled instance: `warehouse/migrations/0003_create_silver_retail_store_sales.sql`.

## Required checks

| Gate | Scope |
|------|-------|
| `retail check` (S1-S7) exit 0 on the migration | NECESSARY, not sufficient. The gate is order-blind and static: it cannot prove row-count/sentinel correctness -- that is proven later by live `retail validate` at Gold Ready. |
| Self-review diff vs Phase-5 order | Confirms the generated SQL did not reorder/skip load-bearing transforms. |

## Statuses

| Status | Meaning HERE |
|--------|--------------|
| `not_started` | No silver migration authored; Stage 2 (mapping_ready) may not be `pass` yet. |
| `blocked` | A blocking reason holds (no CLEARED map, `retail check` ERROR, or Phase-5 order violated). STOP. |
| `warning` | Migration authored and `retail check` passes but a non-fatal WARN or an accepted deviation is recorded in evidence. Does not auto-promote. |
| `pass` | Migration committed, `retail check` (S1-S7) exit 0, self-review diff confirms Phase-5 order. Evidence lists the file + check run. |

## Blocking reasons

- No CLEARED map -- Stage 2 (mapping_ready) is not `pass`.
- `retail check` returns an ERROR on the migration (S1-S7 failure).
- Phase-5 order violated -- self-review diff shows reordered/missing load-bearing
  transforms vs the CLEARED map.
- Migration not committed (file absent from `warehouse/migrations/`).

## Required owner / approval

None -- mechanical for authoring. The .sql is generated and statically checked
without sign-off. A human applies the migration to Postgres (the deferred
DB-write seam); that application is an operational act, not a stage approval.

## Next allowed action

When this stage is `pass` AND the migration has been applied by a human: proceed
to Gold Ready (Stage 4) -- author `NNNN_create_gold_<table>_star.sql` and prepare
for live `retail validate`.

## What the agent must NOT do

- Write silver before mapping_ready is `pass` (Principle IV hard gate).
- Execute/apply the migration against Postgres (deferred DB-write seam).
- Claim the silver table "exists" before a human has applied it.
- Reorder or skip Phase-5 transforms to make `retail check` pass.
- Record `pass` without evidence, or emit a confidence number.

## See also

- `readiness-model.md` -- the state model and the no-fake-confidence rule.
- `readiness-pipeline.md` -- stage sequence and the Principle IV hard gate.
- `mapping-ready.md` -- the prior stage (CLEARED map is this stage's input).
- `gold-ready.md` -- the next stage (live validate gate).
- `../../warehouse/migrations/` -- where the migration is committed.
- `../../.claude/skills/retail-build-warehouse/SKILL.md` -- the authoring skill.
