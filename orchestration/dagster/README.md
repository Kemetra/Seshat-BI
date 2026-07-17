# Seshat BI Dagster Orchestration Adapter (F030)

The unattended / CI runtime for the medallion sequence -- the scheduler sibling
of the `retail-orchestrate` conductor. It RUNS already-approved steps behind
every gate and RECORDS what each asset did as derived run-evidence, deciding no
readiness stage and publishing nothing. Authority boundary: spec
`specs/024-dagster-orchestration-adapter` (unchanged); activation slice: spec
`specs/134-activate-dagster-mvp`.

## Setup (two environments, by design)

The main `seshat` package stays dagster-free (its static core is stdlib-only);
this project keeps its own environment:

```text
cd orchestration/dagster
uv venv .venv
uv pip install -p .venv -e "../..[dbt]" -e ".[dev]"
```

Installed runtime (spec 024 auto-update posture): `dagster==1.13.14`, plus
`seshat-bi[dbt]` (the governed dbt control layer: `dbt-core==1.12.0` +
`dbt-postgres==1.10.2`, the spec-133 pinned pair). The `dagster-dbt` pin was
DROPPED by spec 135 (FR-011 owner decision, 2026-07-17): no released dagster-dbt
accepts dbt-core 1.12, and the dbt engine's execution path never imports
dagster-dbt -- it routes through `seshat.dbt`. Updates via PR only; MAJOR bumps
need a named reviewer; no automerge.

Credentials (live DB steps only) come from the git-ignored `.env`
(`DATABASE_URL` or the `ANALYTICS_DB_*` set). Without them, DB-touching assets
fail closed with a "deferred boundary" blocking reason -- never a fabricated
pass. Validation connections are read-only.

## Running

The front door is the main package's CLI (see
`specs/134-activate-dagster-mvp/contracts/dagster-cli.md`):

```text
seshat dagster doctor                 # preflight: env, pinned dagster, engine mode, gate state
seshat dagster run --job through_gold_job --table retail_store_sales
seshat dagster evidence --run-id <id> # render run-evidence/<id>.md
```

`seshat dagster run` launches THIS project's interpreter as a shell-free child
process with a closed argument set:

```text
.venv/Scripts/python -m dagster job execute -m tower_bi_orchestration.definitions -j <job>
```

`dagster dev` (the local UI) works too and is optional; nothing in this slice
requires a daemon.

## The asset graph (gate semantics fixed by spec 024)

Eleven assets per mapped table (discovered from `mappings/<table>/source-map.yaml`),
plus the live-validate step:

```text
raw_source_file -> bronze_<table> -> source_profile
  -> source_map                  [HUMAN SEAM: reads Gate status; HALTS if not CLEARED]
  -> silver_tables               [STOP: migrations + the same check CI runs]
  -> gold_tables                 [STOP]
  -> (live validate: records deferred without creds)
  -> metric_contracts            [reads approved contracts; authors none]
  -> semantic_model              [STOP + HUMAN SEAM: reads the committed approval]
  -> dashboard_blueprint -> handoff_pack
  -> publish_execution_evidence  [publish wall: TRIGGERS F016 only; FAILS CLOSED while F016 is absent]
```

- A failed gate asset HALTS all downstream assets (recorded `skipped`, never run
  around) and the run terminates `failed` -- the CI signal.
- HUMAN-SEAM assets READ committed approvals (`Gate status`, `approvals[]`,
  `publish_ready`); no code path here writes any of them.
- Outcomes are execution words (`materialized|failed|skipped|blocked|deferred`),
  never the readiness token `pass`; no numeric score exists anywhere in the
  evidence (hard rule #9).

## Evidence flow

Assets append raw JSONL records to `.seshat/dagster/runs/<run-id>/`
(git-ignored; schema `schemas/dagster-run-evidence.schema.json`); the committed
record is `run-evidence/<run-id>.md`, rendered per
`templates/dagster-run-evidence.md`. Measured results are also surfaced as
`evidence[]` / `blocking_reasons[]` on the affected table's readiness status by
Core Authority's process -- never as a `status`/approval write from here.

## Automations (shipped STOPPED)

One daily schedule on `full_sequence_job` and one raw-landing file sensor ship
with `default_status=STOPPED`. Enabling either is a named-human action; this
slice never turns them on.

## The dbt engine seam (activated, selectable)

`silver_tables` / `gold_tables` have a SELECTABLE build engine (spec 135). The
default is the committed `warehouse/migrations/*.sql` path; when a table's
`mappings/<table>/build-engine.yaml` names `dbt` for a layer, that asset runs the
governed dbt build through the `seshat.dbt` control layer (plan -> self-accepted
accept-plan digest -> shadow-schema build) instead. The gate is UNCHANGED: both
engines run the same `seshat check` on exit 0, downstream of the `source_map`
HUMAN SEAM, fail-closed. The engine resolves per layer and fails closed to
migrations on anything but the exact `dbt` value.

The dbt engine is a governed REHEARSAL into isolated shadow schemas: it does NOT
rebuild the real `silver`/`gold` (spec 133 FR-005), so its evidence records
`warehouse_updated: false` and `seshat dagster doctor` warns on mixed-engine
tables. Migrations remain the default, the parity oracle, and the rollback path
until a named human retires them (spec 133 FR-006). Live dbt drive stays
`[PENDING LIVE PROFILE]` (`docs/operations/dbt-activation-status.yaml`). The
execution path goes through `seshat.dbt`, NOT the `dagster-dbt` library (dropped
by spec 135 FR-011); see `docs/integrations/dagster-adapter.md` (engine seam
section).

## Tests

```text
cd orchestration/dagster && .venv/Scripts/python -m pytest -q
```

In-process `materialize()` tests cover the four spec-024 user stories:
fail-closed propagation, human-seam blocking, evidence written with zero
readiness-truth changes, and no self-approval path. CI runs the
definitions-load smoke (`.github/workflows/dagster-smoke.yml`) with no DB and
no secrets.
