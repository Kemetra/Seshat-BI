# Readiness pipeline -- the stage sequence

- **Status:** Planning (docs/templates; no runtime code).
- **Read first:** `readiness-model.md` (the state model).

The seven readiness stages run in strict order. A stage is entered only when the
prior stage is `pass`. Each stage maps to an existing kit artifact/gate -- the
spine adds sequencing and state, not a new method.

## The sequence (each stage -> its gate -> its artifacts)

| # | Stage | Gate (existing) | Required artifacts (existing) | Maps to |
|---|-------|-----------------|-------------------------------|---------|
| 1 | Source Ready | profile review | `mappings/<t>/source-profile.md` | playbook Phase 1 |
| 2 | Mapping Ready | source-mapping gate (Principle IV) | `source-map.yaml`, `assumptions.md`, `unresolved-questions.md` (`Gate status: CLEARED`) | playbook Phase 2-4 |
| 3 | Silver Ready | `seshat check` (S1-S8) | `warehouse/migrations/NNNN_create_silver_<t>.sql` | playbook Phase 5 |
| 4 | Gold Ready | `seshat check` + `retail validate` (live) | `NNNN_create_gold_<t>_star.sql`, filled `reconciliation-report.md` | playbook Phase 6 |
| 5 | Semantic Model Ready | `seshat check` (D1-D11/C1/R1) + metric contracts | the PBIP model + metric-contract artifacts (F009/F010) | playbook Phase 7 (model) |
| 6 | Dashboard Ready | metric-contract review | the report designed against approved contracts (F011) | playbook Phase 7 (BI) |
| 7 | Publish Ready | handoff review | the BI handoff pack (F013) | post-Phase-7 |

## Transition rules

```
source_ready  --pass-->  mapping_ready  --pass-->  silver_ready
   |                         |  (HARD GATE: no silver before CLEARED map)
   |                         v
   +--blocked--> STOP    silver_ready  --pass-->  gold_ready
                            |                        | (HARD GATE: live validate
                            v                        v   before Power BI)
                         gold_ready  --pass-->  semantic_model_ready
                            |                        | (HARD GATE: metric
                            v                        v   contracts before dashboard)
                  semantic_model_ready --pass--> dashboard_ready --pass--> publish_ready
```

- **`pass` advances; `blocked` stops.** A `warning` is recorded and may proceed
  if the stage's own doc allows it (it never auto-promotes to `pass`).
- **Hard gates (cannot be skipped, ever):**
  - No `silver_ready` work until `mapping_ready` is `pass` (Principle IV).
  - No `gold_ready` -> Power BI until the live validation passes (Principle VIII).
  - No `dashboard_ready` design until metric contracts exist (roadmap rule 5).
  - No pbi-cli/PBIP automation until `semantic_model_ready` (roadmap rule 6).
- **Resumption is state-based.** The agent recomputes `current_stage` from the
  committed artifacts + `Gate status` + migration presence + the readiness
  status file -- there is no separate run-state engine (consistent with the
  `retail-orchestrate` conductor, spec 005).

## Where the spine meets the conductor

The `retail-orchestrate` skill (spec 005) already sequences the verbs and
self-heals against the gate. The readiness spine is the **state layer** that
conductor reads: the conductor's phases ARE these stages, and a stage's `status`
is what tells the conductor whether to advance, stop at a human seam, or report a
blocker. The conductor executes; the readiness status records.

## See also

- Per-stage detail: the seven `docs/readiness/<stage>-ready.md` docs.
- The conductor: `.claude/skills/retail-orchestrate/SKILL.md`.
- Status template: `templates/readiness-status.yaml`.
