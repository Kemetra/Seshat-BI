# Implementation Plan: Activate the dagster-dbt Engine Seam

**Branch**: `135-activate-dagster-dbt-seam` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/135-activate-dagster-dbt-seam/spec.md`

## Summary

Activate the documented dagster-dbt engine seam by giving the `silver_tables` and
`gold_tables` assets a selectable build engine. The ACTION inside the two assets
branches on engine (`migrations` default -> apply committed SQL; `dbt` ->
governed `seshat.dbt` build into shadow schemas); the GATE is unchanged (the SAME
`seshat check` exit-0 gate, engine-independent because it reads committed text),
the `source_map` HUMAN SEAM upstream is unchanged, and the STOP-edge topology is
unchanged. Migrations remain the default, the parity oracle, and the rollback
path. Only `_build_layer`'s body changes; deps/edges, the run-evidence schema, and
the publish wall do not.

## Technical Context

**Language/Version**: Python 3.13 exactly (repo floor); the orchestration project
is a separate Python project with its own venv.

**Primary Dependencies**: main `seshat` package unchanged (`pyyaml>=6`, stdlib
static core, NO dagster/dagster-dbt/dbt). Orchestration venv:
`dagster==1.13.14` plus `seshat-bi[dbt]` (brings `dbt-core==1.12.0` +
`dbt-postgres==1.10.2`, the spec-133 pinned pair) and `psycopg2-binary` for the
migrations path. `dagster-dbt` is REMOVED (FR-011 owner decision, 2026-07-17):
it excludes dbt-core 1.12 (ResolutionImpossible) and sits on no execution path.

**Storage**: committed mappings, the `dbt/` project, dagster run-evidence markdown
(`orchestration/dagster/run-evidence/<run-id>.md`), and the distinct dbt
run-evidence JSON (`mappings/<table>/dbt-evidence/<invocation-id>.json`);
git-ignored raw dbt `target/` and `.seshat/dagster/runs/<run-id>/`; PostgreSQL
only at the live boundary (deferred).

**Testing**: pytest (main suite for the control-layer/doctor units; orchestration
tests in `orchestration/dagster/tests/`, runnable in CI with the orchestration
venv); ruff; `seshat check`; the definitions-load smoke. Fixture tests use a fake
dbt runner and monkeypatched gate commands, needing no database and no secrets.

**Target Platform**: Windows/macOS/Linux dev installs; Linux CI runner (no DB, no
secrets).

**Project Type**: Python CLI/library + a separate orchestration Python project;
no new project is created -- this feature edits two existing projects.

**Performance Goals**: unchanged; the dbt build cost is the underlying governed
dbt invocation, gated identically to the migrations path.

**Constraints**: the run-evidence schema MUST NOT change; the asset dependency
topology MUST NOT change; the main package import path MUST stay stdlib-only;
stable exit codes; no raw dbt pass-through; secrets only in `.env`; ASCII,
UTF-8 without BOM; short repo-relative paths (Windows MAX_PATH).

**Scale/Scope**: one shared build body edited (`_build_layer`), one engine
resolver added, one dbt-engine branch added, one doctor finding added, one
orchestration `pyproject.toml` dependency line, one integration-doc reconcile,
plus ~4-6 test modules. No new asset, job, schedule, or sensor.

## Constitution Check

*GATE: Passed before design; re-checked after.*

| Principle | Design proof | Status |
|---|---|---|
| I -- Agent-first, gate-enforced | Both engines run the SAME `seshat check` gate; asset success = exit-0 evidence; the checker/named human remain sole pass authority; the agent proposes, the gate disposes. | PASS |
| II -- Depend, never fork | dbt and dagster-dbt consumed as pinned external deps in the orchestration project; `seshat.dbt` is reused unforked; publish stays behind the F016 trigger (untouched). | PASS |
| III -- Medallion, Postgres-first, gold-only | dbt writes ISOLATED SHADOW schemas only (spec 133 FR-005); no Power BI read of shadow/silver/bronze; Postgres-only. | PASS |
| IV -- Mapping before silver | The `source_map` HUMAN SEAM upstream is unchanged; the dbt engine is downstream of it and cannot run around it; the governed `seshat.dbt` gate re-checks the mapping approval. | PASS |
| V -- Stop at judgment calls | The FR-007 build-path switch, dbt-as-default, real-gold writes, and migration retirement are LEFT to named humans (open-for-human); no approval is self-granted; schedule/sensor stay STOPPED. | PASS |
| VI -- Defaults then deviations | Migrations remain the default engine; dbt is an explicit, recorded deviation; a fail-closed default preserves the committed baseline. | PASS |
| VII -- Example, not schema | Engine resolution and the dbt branch are generic; `retail_store_sales` is the filled instance; no table specifics leak into generic code. | PASS |
| VIII -- Static-first, live deferred | Definitions-load smoke + fixture tests (fake dbt runner) need no DB; the dbt engine records a `deferred` boundary without creds; live dbt drive stays `[PENDING LIVE PROFILE]`. | PASS |
| IX -- Secrets and reproducibility | `.env`-only credentials; shared redaction on every surfaced error (dbt logs included); exact version pins; ASCII/UTF-8-no-BOM; short paths. | PASS |

**Post-design re-check:** PASS. Routing the dbt build through `seshat.dbt`
planning/gate (not a raw `dagster-dbt` CliResource) strengthens Principles
I/IV/VIII; evidence-only semantics and the publish wall are unchanged from spec
134.

## Project Structure

### Documentation for Feature 135

```text
specs/135-activate-dagster-dbt-seam/
|-- spec.md
|-- plan.md
|-- tasks.md
`-- analysis.md
```

### Source touchpoints (edits to two existing projects; no new project)

```text
orchestration/dagster/
|-- pyproject.toml                                    # add seshat-bi[dbt] to the orchestration venv deps (dagster-dbt already pinned)
|-- src/tower_bi_orchestration/
|   |-- engine.py                                     # NEW: resolve_build_engine(root, table, layer) -> {"migrations","dbt"}; fail-closed default
|   |-- assets/gates.py                               # EDIT: _build_layer branches on engine; new _build_layer_dbt body (governed seshat.dbt build)
|   |-- dbt_build.py                                  # NEW: thin bridge -- calls seshat.dbt plan+accept-plan-recompute+build for one table/layer; returns exit + measured + dbt-evidence path
|   `-- (db.py, commands.py, evidence_writer.py)      # UNCHANGED interfaces; commands.checker_argv() reused as the shared gate
`-- tests/
    |-- test_engine_resolution.py                     # US2/SC-003: absent/migrations/dbt/malformed -> resolved engine
    |-- test_dbt_engine_build.py                      # US1/SC-001/SC-002: governed plan + shadow-only + gate identical; forced non-zero skips downstream
    |-- test_dbt_engine_deferred.py                   # US3/SC-004: no DSN -> deferred; dbt runtime absent -> blocked, no traceback
    `-- test_migrations_unchanged.py                  # US5/SC-007: migrations files untouched; revert reproduces prior behavior

src/seshat/dagster_adapter/
`-- doctor.py                                         # EDIT: add per-table engine-mode finding (migrations vs dbt; dbt availability); read-only, no score

docs/integrations/dagster-adapter.md                 # EDIT: "activates after spec 133 merges" seam note -> activated selectable-engine reality (history preserved, no live-pass claim)

tests/unit/dagster_adapter/
`-- test_doctor_engine_mode.py                        # US4/FR-010: doctor reports resolved engine + dbt availability truthfully
```

**Structure Decision**: no new project. The seam is a body-level branch inside the
existing `_build_layer` shared function in `orchestration/dagster/.../assets/gates.py`,
plus a small engine resolver and a thin dbt bridge that delegates to the already
committed `seshat.dbt` control layer. The main `seshat` package gains no
dependency; the doctor edit lives in the existing control layer.

## Technical Approach

1. **Engine resolution (FR-001, fail-closed default).** `resolve_build_engine`
   reads an explicit committed configuration value per table+layer. Allowed
   values: `migrations` (default) and `dbt`. Absent, unrecognized, or malformed
   -> `migrations`. The resolver never infers from the presence of the `dbt/`
   project; only the exact `dbt` value engages dbt. Config source (CONSTRAINED
   per plan-review R1/F2): a committed file inside the table's human-reviewed
   working set (`mappings/<table>/`), so the engine flip inherits mapping-review
   attribution; environment variables, CLI flags, and any runtime input are
   FORBIDDEN as engine selectors. The exact key name stays generic and
   placeholder-driven per Principle VII.

2. **The build body branch (FR-004/FR-005 -- gate unchanged, action changes).**
   `_build_layer` keeps its current preamble (resolve DSN; deferred boundary when
   absent) and its trailing gate call unchanged. It branches only on the produce
   step: `migrations` -> the current `db.apply_sql_file` loop over
   `warehouse/migrations/*.sql`; `dbt` -> `dbt_build.build_layer(...)`. Both
   branches then run `commands.run_gate_command(commands.checker_argv(), cwd=root)`
   and treat exit 0 as the only green. The STOP edge and the `source_map` upstream
   dep are untouched (FR-005).

3. **The governed dbt bridge (FR-002 -- no raw pass-through, digest honored).**
   `dbt_build.build_layer` delegates to `seshat.dbt`: resolve the working set and
   evaluate the mapping gate (`seshat.dbt.gate`), compute an execution plan
   (`seshat.dbt.planning`) for the fixed governed selector (`seshat_table_<table>`),
   recompute the accept-plan digest and refuse on drift (spec 133 FR-025), then run
   the governed `dbt build` in shadow schemas via the `seshat.dbt.runner`
   child-process seam. It returns an exit code, a `measured` dict (dbt run-result
   counts, selector, shadow schemas -- redacted), and the path of the dbt-evidence
   record it produced. No raw dbt selector/argument is accepted; the asset never
   constructs a `dagster-dbt` `DbtCliResource` that bypasses `seshat.dbt`
   planning/gate. (Rationale: spec 133 FR-023 forbids pass-through; routing through
   the committed control layer is what makes the governance identical to
   `seshat dbt build`.)

   Note on the `dagster-dbt` LIBRARY (naming vs mechanism). This seam is named the
   "dagster-dbt engine seam" and the documented contract says the build runs "via
   dagster-dbt", but the EXECUTION PATH deliberately goes through `seshat.dbt`
   (plan + accept-plan digest + shadow build), NOT through native `dagster-dbt`
   asset wiring (`@dbt_assets` / a raw `DbtCliResource`). Native dagster-dbt wiring
   would run dbt directly and BYPASS the accept-plan digest recompute and the
   governed gate (spec 133 FR-023/FR-025) -- so it is intentionally NOT used. The
   `dagster-dbt` pin is REMOVED by this feature (FR-011 owner decision): the
   solve proof showed dagster-dbt excludes dbt-core 1.12, and since the library
   sits on no execution path, removal -- not a dbt downgrade -- resolves the
   conflict; doctor/smoke/docs surfaces asserting the old pinned pair are
   reconciled to dagster-only. What lands on the dbt engine's
   execution path is `seshat-bi[dbt]` (the governed control layer), not the
   `dagster-dbt` library. This is the one place naming and mechanism could read as
   disagreeing; the mechanism is the authority.

4. **Deferred boundary and unavailability (FR-006).** When the resolved engine is
   `dbt` and `db.resolve_dsn()` is None, the asset records `deferred` with a
   timestamp and blocks fail-closed (same shape as the migrations path and
   `live_validate`). When the dbt runtime is not importable in the orchestration
   venv, the bridge blocks with a concrete `blocking_reason` + named owner and no
   traceback (spec 133's `unavailable` posture surfaced as a dagster block).

5. **Doctor engine-mode surfacing (FR-010).** `run_doctor` gains a per-table
   engine finding: `migrations` (info) or `dbt` (info) plus, under `dbt`, a
   deferred/enable finding when the dbt runtime or DSN is absent. Findings stay
   categorical (blocker/warning/info) with a concrete remedy; no numeric score
   (hard rule #9). The DSN is reported PRESENT/absent only, never echoed.

6. **Evidence rendering unchanged (FR-008/FR-009).** The dagster run-evidence
   record renders against the unchanged `schemas/dagster-run-evidence.schema.json`:
   under the dbt engine the `gate_command` string names the governed dbt build and
   `measured` carries the dbt counts + selector; asset names, outcomes (execution
   words, never `pass`), and required fields are unchanged. The dbt run-evidence
   JSON under `mappings/<table>/dbt-evidence/` remains a distinct artifact; the
   dagster record MAY cite its path in `measured` but MUST NOT merge or overwrite
   it.

7. **Integration-doc reconcile (FR-013).** The `docs/integrations/dagster-adapter.md`
   section "The dagster-dbt engine seam (activates after spec 133 merges)" is
   rewritten to describe the activated selectable engine, its fail-closed default,
   and the `[PENDING LIVE PROFILE]` live status; the historical framing is
   preserved as history, no live pass is claimed.

## Constraints and Risks

- **No new dependency on the main package.** `seshat-bi[dbt]` and `dagster-dbt`
  live in the orchestration venv only; a guard test (existing B1/B3 posture)
  asserts importing base `seshat` loads no dagster/dagster-dbt/dbt module. This is
  the spec 134 FR-001 constraint restated.

- **The pinned pair already proves IMPORT, not live drive.** The definitions-load
  smoke proves `dagster` + `dagster-dbt` load; it does NOT prove `dagster-dbt`
  0.29.14 can drive `dbt-core` 1.12.0 at runtime. That is a NEW, unproven surface.
  Verification points at dagster-dbt 0.29.14's declared requirements and the
  pending compile in `docs/operations/dbt-activation-status.yaml`. Because dbt
  compile is `pending` and live parity has not run, the dbt engine records
  `deferred` without a live profile -- the same posture `live_validate` takes
  today. Live drive is verified only when a disposable Postgres profile exists;
  this feature does not claim it.

- **Digest drift is a real fail-closed path -- and a drift-guard ONLY.** The
  asset recomputes the plan and passes its own digest; if any bound input drifted
  (map revision, project fingerprint, versions, selection, target), `seshat.dbt`
  refuses and the asset blocks. Per plan-review R1 this self-recompute removes
  the per-run human plan review; the compensating control is the reviewed
  committed engine flag (FR-001), and the evidence records the self-acceptance
  (FR-014). The drift-guard must not be short-circuited by the unattended caller.

- **The dbt engine is a rehearsal; the real warehouse is not refreshed.** Shadow-
  only writes (spec 133 FR-005) mean a dbt-engine run leaves real `silver`/`gold`
  exactly as the last migrations run built them, while downstream assets validate
  that REAL warehouse. Evidence records `warehouse_updated: false` under dbt, and
  doctor warns on mixed-engine tables (FR-015, plan-review R2).

- **The pins must co-resolve BEFORE anything is built on them (R3) -- RESOLVED.**
  The T001 solve proof FAILED as R3 anticipated: dagster-dbt 0.29.14 declares
  dbt-core <1.12, excluding the spec-133 pin (ResolutionImpossible, confirmed in
  isolation). Owner decision (2026-07-17): DROP the unused dagster-dbt pin; keep
  dagster 1.13.14 + seshat-bi[dbt] intact. T001 now proves THAT solve and
  reconciles the pinned-pair surfaces (doctor, smoke, docs, contract tests).

- **Lock semantics under unattended kill.** The bridge inherits
  `seshat.dbt.runner`'s bounded cross-process lock. Contention or a stale holder
  must surface as a concrete redacted `blocking_reason` (never a traceback or a
  silent hang); a stale-lock gap discovered in `seshat.dbt` is surfaced to the
  owner, not silently patched here -- plan-review R6.

- **Redaction must cover dbt output.** dbt logs can echo profile-derived values;
  every surfaced error passes the shared redaction before reaching dagster
  run-evidence or console (Principle IX), identical to the migrations path.

- **No schema and no topology change.** `git diff` must show zero change to
  `schemas/dagster-run-evidence.schema.json` and zero change to asset deps/edges;
  only `_build_layer`'s body and the new small modules change.

## Complexity Tracking

No constitution violations to justify. The feature adds one engine branch and a
thin bridge to an already committed control layer; it introduces no new project,
no new dependency on the governed import path, and no new gate.
