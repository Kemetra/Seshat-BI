# Dagster MVP Activation -- design (2026-07-17)

**Status:** Approved by the user (brainstorming session, 2026-07-17; all four
recommended options accepted). Implements the runtime slice ENUMERATED by
`specs/024-dagster-orchestration-adapter` (roadmap F030). On-disk spec:
`specs/134-activate-dagster-mvp` (this design feeds speckit-specify).

**One line:** Turn the shipped Dagster advisory seam into the real unattended /
CI runtime for the medallion sequence -- running only already-approved steps,
failing closed at every gate, writing derived run-evidence, deciding nothing.

## Decisions taken (with the user, 2026-07-17)

1. **MVP scope: the full 11-asset graph** from spec 024 -- raw_source_file ->
   bronze_<table> -> source_profile -> source_map [HUMAN SEAM] -> silver_tables
   [STOP] -> gold_tables [STOP] -> metric_contracts -> semantic_model [STOP +
   HUMAN SEAM] -> dashboard_blueprint -> handoff_pack ->
   publish_execution_evidence [publish wall]. Proven on `retail_store_sales`.
   The publish asset FAILS CLOSED ("F016 publish adapter not available").
2. **Layout: hybrid.** The Dagster definitions live in `orchestration/dagster/`
   exactly as spec 024 enumerated (own `pyproject.toml`, package
   `tower_bi_orchestration`, pins `dagster` + `dagster-dbt` TOGETHER). A thin
   control layer + `seshat dagster` CLI family lives in
   `src/seshat/dagster_adapter/`, mirroring the dbt MVP (spec 133) surface.
3. **dbt coupling: none this slice.** Silver/gold assets wrap the existing
   `warehouse/migrations/*.sql` path (already on main). A documented
   `dagster-dbt` integration seam activates after the dbt MVP (spec 133,
   separate worktree) merges. Spec 024 explicitly allows this posture.
4. **Automations: CI smoke + paused schedule.** A GitHub Actions job installs
   the orchestration project and asserts the Definitions object loads (the
   FR-009 minimum gate; no DB). One daily schedule and one file-arrival sensor
   ship STOPPED / paused by default -- a named human enables them.

## Components

### 1. orchestration/dagster/ (the spec-024 enumerated project, now real)

```text
orchestration/dagster/
  README.md                  # how to run; the human seams; gate-read posture
  pyproject.toml             # tower-bi-orchestration; pins dagster + dagster-dbt together
  src/tower_bi_orchestration/
    definitions.py           # the Definitions object
    gates.py                 # read-only gate/approval readers (Gate status, approvals[], publish_ready)
    assets/                  # the 11 assets
    jobs/                    # full_sequence_job (+ through_gold partial)
    schedules/               # daily schedule, default_status=STOPPED
    sensors/                 # file-arrival sensor, default_status=STOPPED
  run-evidence/              # <run-id>.md per run (filled templates/dagster-run-evidence.md)
  tests/                     # in-process materialize() tests for US1-US4
```

- Gated assets raise `dagster.Failure` -> downstream `skipped`, run status
  failed (the CI signal). No run-around of a STOP edge.
- `source_map` READS `Gate status: CLEARED` + zero open rows +
  `approvals[]`; it never writes them.
- No DB creds -> DB-touching assets record `deferred-boundary` with timestamp;
  never a fabricated pass.
- Run evidence: `run-evidence/<run-id>.md` + measured results surfaced as
  `evidence[]` / `blocking_reasons[]` on the table's readiness status. Never a
  `status`, `Gate status`, or approval write. No numeric score (hard rule #9).

### 2. src/seshat/dagster_adapter/ + `seshat dagster` CLI

Small units, mirroring the dbt adapter shape: `gate` (read-only preflight),
`runner` (subprocess `dagster` invocation; closed argument set; no shell),
`evidence` (parse run output -> evidence record), `redaction` (strip DSN/host/
credential material from every surfaced error). Lazy-loaded CLI verbs:

```text
seshat dagster doctor    # environment + project + gate preflight (no DB required)
seshat dagster run       # execute a job behind the gates; fail-closed
seshat dagster evidence  # render/inspect run-evidence records
```

The main `seshat` package gains NO dagster dependency -- the orchestration
project keeps its own environment; the static core stays stdlib-only.

### 3. Skills, commands, distribution

- `.claude/skills/dagster-orchestration-adapter/SKILL.md`: replace the "NOT
  created yet" seam note with the operational procedure (doctor/run/evidence);
  authority boundary text unchanged.
- New slash commands `dagster-doctor`, `dagster-run`, `dagster-evidence` added
  to `distribution/public-command-surface.yaml` (the authority), regenerated
  into the Claude/Codex bundle templates and `integrations/`.
- `docs/capabilities/capabilities.yaml`: the adapter entry gains its runtime
  claim (locally-verified) + the CLI command references.

### 4. Automations

- `.github/workflows/` job: install `orchestration/dagster/`, run the
  definitions-load smoke test (`dagster definitions validate` or equivalent)
  plus the orchestration unit tests. No DB, no secrets.
- Schedule + sensor ship STOPPED (fail-closed posture; Principle V).

## Testing (TDD; 80%+ on new code)

The four spec-024 user stories become the test spine, via Dagster's in-process
`materialize()` API over fixture repos:

- US1: a failed gate asset halts all downstream assets; run terminates failed.
- US2: `Gate status: OPEN` blocks `silver_tables`; nothing writes CLEARED.
- US3: a completed run writes run-evidence; `git diff` shows zero changes to
  any readiness `status` / `Gate status` / `approvals[]`.
- US4: no asset has a code path that writes a readiness pass or approval.

Control-layer units (gate/runner/evidence/redaction) tested in the main suite.

## Out of scope

Enabling schedules/sensors, F016 publish, dbt internals (spec 133 owns them),
live-DB CI runs, multi-engine orchestration, numeric scoring of any kind.

## Constraints honored

Constitution Principles I, II, IV, V, VII, VIII, IX; ASCII-only artifacts
(UTF-8 no BOM); secrets only in git-ignored `.env`; `dagster` + `dagster-dbt`
pinned together, PR-only updates, no automerge on majors (F031/F033 deferred).
