# Architecture -- the Readiness Pipeline (the operating spine)

- **Status:** Planning (docs/templates; no runtime code).
- **Read with:** `tower-bi-agent-kit.md` (the kit), `docs/readiness/readiness-model.md`
  (the state model), `docs/roadmap/roadmap.md` (the feature sequence).

## One line

> The **Tower BI Readiness System** is the **operating spine** inside the Tower BI
> Agent Kit: a stage/state model that organizes the kit's existing gates into a
> tracked sequence the agent reads to decide the next allowed action.

## What it is, and is not

- It **does NOT replace** the constitution, the medallion playbook, the
  source-mapping gate, or `seshat check` / `retail validate`.
- It **organizes them** into seven readiness stages (Source -> Mapping -> Silver ->
  Gold -> Semantic Model -> Dashboard -> Publish), each with explicit
  `status + evidence + blockers` (never a fabricated confidence number).
- `seshat check` and `retail validate` remain **gates/helpers the agent calls** --
  not the user-facing product. The agent + skills are the primary surface
  (Impeccable-style). `pbi-cli` / PBIP stays a **later adapter** (feature 016),
  not the core.

## Where the spine sits on the existing stack

The kit's stack (from `tower-bi-agent-kit.md`) is `D -> C -> A -> ENGINE ->
substrate`. The readiness spine is a **state layer the agent (Layer D) reads**; it
binds the existing layers into stages:

```
  D  AGENT EXPERIENCE        the agent reads READINESS STATE -> picks the one
     (primary surface)       next allowed action; runs the stage's workflow
        | reads/advances
        v
  READINESS SPINE  [NEW, state-only]   7 stages, each = status + evidence + blockers
     source -> mapping -> silver -> gold -> semantic model -> dashboard -> publish
        | each stage's gate is an EXISTING check:
        v
  A  GOVERNANCE CORE         seshat check (static) + retail validate (live)
        |                    -- the gates the stages assert; unchanged
        v
  ENGINE / SUBSTRATE         pbi-cli (later adapter) ; Postgres medallion + PBIP
```

The spine adds **no new gate** -- it sequences the gates that already exist and
records where each table is. The `retail-orchestrate` conductor (spec 005)
executes the sequence; the readiness status records the state.

## Stage -> gate -> evidence (the binding)

| Stage | Gate (existing) | Evidence (committed) |
|-------|-----------------|----------------------|
| Source Ready | profile review | `mappings/<t>/source-profile.md` |
| Mapping Ready | source-mapping gate (Principle IV) | `source-map.yaml` + `assumptions.md` + `unresolved-questions.md` (CLEARED) |
| Silver Ready | `seshat check` S1-S8 | silver migration .sql |
| Gold Ready | `seshat check` + `retail validate` (live) | gold star migration + filled `reconciliation-report.md` |
| Semantic Model Ready | `seshat check` D1-D11/C1/R1/G6 + metric contracts | PBIP model + metric-contract artifacts |
| Dashboard Ready | metric-contract review | report designed against approved contracts |
| Publish Ready | handoff review | BI handoff pack + publish approval |

## Hard gates the spine enforces (ordering)

- No `silver` before `mapping_ready` is `pass` (constitution Principle IV).
- No `gold` -> Power BI before `retail validate` passes (Principle VIII).
- No dashboard design before metric contracts (roadmap rule 5).
- No pbi-cli/PBIP automation before `semantic_model_ready` (roadmap rule 6;
  Principle II -- adapter is later).

## What this slice does not do

Docs/planning only. No runtime code, no scoring engine, no dashboard generation,
no pbi-cli publishing, no Fabric/ML/forecasting/universal-connector. Each future
feature (005-016) gets its own spec before code. The architecture statement here
is the spine's shape, not its implementation.

## See also

- The kit architecture: `tower-bi-agent-kit.md`.
- The spine model + stages: `docs/readiness/`.
- The roadmap: `docs/roadmap/roadmap.md`.
- The conductor that executes the sequence: `.claude/skills/retail-orchestrate/SKILL.md`.
