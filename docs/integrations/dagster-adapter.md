# Dagster Orchestration Adapter -- integration guide

- **Roadmap feature:** F030  **On-disk spec:** `specs/024-dagster-orchestration-adapter`
  (dir 024 == F030; when the dir number and the F-number disagree, the roadmap F-number wins).
- **Authority category (F024):** Execution Adapter / `DB-connected` (NOT publish-capable -- it
  TRIGGERS F016, it never publishes). See `docs/architecture/product-modules.md`.
- **Status:** BUILT (spec 134, the activation slice of F030). The Dagster PROJECT exists at
  `orchestration/dagster/` -- `definitions.py`, the 11-asset graph, the two jobs, one STOPPED
  schedule, one STOPPED sensor -- together with the `seshat dagster doctor|run|evidence`
  control layer in `src/seshat/dagster_adapter/`, the canonical evidence schema
  `schemas/dagster-run-evidence.schema.json`, and the CI definitions-load smoke
  (`.github/workflows/dagster-smoke.yml`). This guide's authority boundary is unchanged from
  the spec-024 planning slice.

## What Dagster is here (one line)

> The UNATTENDED / CI runtime for the medallion sequence -- the scheduler sibling of the
> `retail-orchestrate` conductor -- that RUNS already-approved steps behind every gate and
> RECORDS what each asset did as derived run-evidence, deciding no readiness stage and
> publishing nothing.

## Why it exists (and what it is not)

The kit already sequences the medallion stages interactively: `retail-orchestrate` (F005), where
a human is in the loop, the agent reads readiness state, runs the gate, and HARD-STOPS at the two
human seams (mapping approval, Principle-V judgment calls). What the kit lacked is the
unattended / CI sibling: a way to run the SAME approved sequence on a schedule or in a pipeline
without a human re-typing each step -- while still respecting every gate and every human seam.

Dagster is that sibling. Its single job is to RUN steps that have already been approved and to
RECORD what happened. It is the execution-side counterpart of the conductor, governed by exactly
the same authority boundary: the gate exit code and the named human are the truth; the
orchestrator proposes and runs, it never decides. Two runtimes, one sequence, one authority.

It is NOT:

- a definer of truth -- it never defines a metric, a mapping, a grain, a rollup, a segment, or a
  PII disposition; those are owned by the upstream governed artifacts.
- an approver -- it never writes a readiness `pass`, a `Gate status: CLEARED`, or an
  `approvals[]` entry.
- a publisher -- it never opens a Power BI connection; the terminal asset only TRIGGERS the
  parked F016 Power BI Execution Adapter once `publish_ready = pass`.
- a successor to `retail-orchestrate` -- it is the unattended sibling, not a replacement.

## The derived-evidence vs authored-truth boundary (the line this adapter lives or dies on)

The single biggest design risk is conflating "Dagster writes evidence back" with "Dagster
authors truth." They are different writes; the adapter keeps them apart:

- **DERIVED RUN-EVIDENCE (allowed).** When Dagster runs a step it records WHAT HAPPENED -- the
  gate command, the exit code, the measured numbers, the timestamp, the commit sha. This is a
  `templates/dagster-run-evidence.md` record: evidence ABOUT a step, the same category as a
  `reconciliation-report.md` being filled by a live run.
- **AUTHORED TRUTH (forbidden).** Flipping a readiness stage to `pass`, writing an approval,
  writing `Gate status: CLEARED`, defining a metric / grain / PII disposition -- these are
  RULINGS. Dagster MUST NOT write any of them.
- **How the two reconcile (the one sentence).** For mechanical stages (Silver Ready, Gold Ready)
  Dagster writes the CHECK evidence (the `retail check` / `retail validate` exit + numbers);
  whether that evidence MARKS the stage `pass` is Core Authority's record, written by Core
  Authority's process, not by Dagster's asset. For human-approval stages (Mapping Ready,
  Semantic Model publish-safety, Publish Ready) Dagster READS the committed approval and HALTS if
  it is absent -- it never writes the approval and never writes a `pass` that depends on one.

This is exactly the posture `retail-orchestrate` already takes ("you may READ `Gate status`; you
may not write `CLEARED` yourself"). Dagster is the unattended runtime of that same contract.

## The asset graph (gate semantics, not just names)

The planned graph is eleven assets. Each dependency edge is a STOP edge (a failed gate halts all
downstream assets) or a HUMAN-SEAM edge (reads a committed approval and halts if absent -- never
writes it):

```text
raw_source_file
  -> bronze_<table>              (load bronze; DB write of raw landing)
  -> source_profile              (profile the source; writes profile evidence)
  -> source_map                  [HUMAN SEAM: reads Gate status; HALTS if not CLEARED]
  -> silver_tables               [STOP edge: blocked until source_map gate CLEARED]
  -> gold_tables                 (Kimball star; mechanical -- writes check evidence)
  -> metric_contracts            [reads approved contracts; does not author them]
  -> semantic_model              [HUMAN SEAM: reads semantic-model approval]
  -> dashboard_blueprint         (design evidence; gated on semantic_model_ready)
  -> handoff_pack                (generate the BI handoff bundle; writes evidence)
  -> publish_execution_evidence  [gated on publish_ready = pass; TRIGGERS F016 only]
```

| Asset | Edge type | Gate / what it reads | Outcome on a missing gate |
|-------|-----------|----------------------|---------------------------|
| `raw_source_file` | input | landing input | n/a |
| `bronze_<table>` | build | load command | failed -> downstream skipped |
| `source_profile` | build | profile command | failed -> downstream skipped |
| `source_map` | HUMAN SEAM | `Gate status: CLEARED` + zero open rows; `approvals[]` | BLOCKS `silver_tables`; records open mapping blocker |
| `silver_tables` | STOP (gated on `source_map`) | `retail check` exit 0 | failed/blocked -> downstream skipped |
| `gold_tables` | STOP | `retail check` exit 0 | failed -> downstream skipped |
| `metric_contracts` | read | approved metric contracts | n/a (reads; authors none) |
| `semantic_model` | STOP + HUMAN SEAM | `retail check` + contract-binding read; semantic-model approval | failed/blocked -> downstream skipped |
| `dashboard_blueprint` | gated | Semantic Model Ready | skipped if upstream skipped |
| `handoff_pack` | build | generate-handoff command | failed -> downstream skipped |
| `publish_execution_evidence` | HUMAN SEAM | `publish_ready = pass`; TRIGGERS F016 | BLOCKS / FAILS CLOSED; triggers nothing |

Edges marked STOP halt all downstream assets on a failed gate. Edges marked HUMAN SEAM read a
committed human approval and halt if it is absent -- they never write it. The terminal asset
TRIGGERS the parked F016 adapter; Dagster never publishes itself. A directly-requested downstream
asset (e.g. targeting `dashboard_blueprint` while gold is broken) is still blocked by the upstream
STOP edge -- the dependency cannot be run around.

## Allowed operations (the closed RUN list)

Dagster MAY orchestrate exactly these steps; the list is explicit and closed:

- Sequence all seven readiness stages in the asset graph (decide none).
- RUN: load bronze, profile source, run dbt or SQL migrations (silver / gold), run
  `retail check`, run `retail validate`, run the semantic check, generate the handoff pack.
- WRITE DERIVED run-evidence (`orchestration/dagster/run-evidence/<run-id>.md`): per-asset gate
  command, exit code, measured numbers, timestamps, commit sha, blocked/skipped reasons + named
  owners; surface those measured results as `evidence[]` / `blocking_reasons[]` on the affected
  table's `readiness-status.yaml`.
- READ committed approvals and readiness state as the GO signal for human-seam assets.
- TRIGGER the F016 Power BI Execution Adapter -- and ONLY when `publish_ready = pass`.
- HALT a failed gate asset and propagate the stop to all downstream assets (fail-closed).
- TERMINATE a halted / fail-closed run with a non-zero / failed Dagster run status (the CI
  signal) so an unattended scheduler surfaces the blocker -- a derived signal about the run,
  never a readiness `pass` / fail write.
- ESCALATE any judgment call to the named owner.

## Forbidden operations (the matrix says NO)

- Approve a mapping; write `Gate status: CLEARED`; invent a parallel approval marker.
- Approve or define a metric contract; define a metric, mapping, grain, rollup, segment, or PII
  disposition.
- Change a readiness stage to `pass` without the required evidence + named approval; write any
  readiness `status`.
- Resolve a business ambiguity or any Principle-V judgment call.
- Bypass the source-map gate; materialize a silver asset before the mapping is CLEARED.
- Publish a Power BI model; open a Power BI connection; publish Power BI without
  `publish_ready = pass` (Dagster may only TRIGGER F016).
- Emit a numeric health / confidence / maturity score in run evidence (Principle IX, hard
  rule #9).
- Run a gate around a failed upstream gate (no run-around of a STOP edge).

## The human seams (every approval is a named human action)

Dagster never holds approval authority. Every approval is a named human action recorded in Core
Authority; Dagster reads it and halts if absent:

- **Mapping Ready** -- the reviewer sets `Gate status: CLEARED` after the source-mapping review.
  Dagster reads it; `silver_tables` is blocked until it is present.
- **Semantic Model Ready (publish-safety / metric approval)** -- the metric owner / governance
  approves; Dagster reads the approval and never grants it.
- **Publish Ready** -- the named approver signs off the handoff pack; only then may the publish
  asset TRIGGER F016.
- **Any Principle-V judgment call** (grain, PII, rollup, segment, sentinel-vs-null) -- the named
  owner decides; Dagster HALTS the affected asset and escalates.

## Fail-closed behavior (the CI signal)

- A failed gate asset HALTS all downstream assets, which are recorded `skipped` -- not run
  around (US1).
- A human-seam asset whose committed approval is absent BLOCKS and runs nothing (US2).
- In both cases the run terminates with a non-zero / failed Dagster run status (the CI signal) in
  ADDITION to writing the run-evidence record, so an unattended scheduler surfaces the blocker
  rather than exiting silently (FR-013). The failed run status is DERIVED evidence about the
  execution; it flips no readiness stage.
- When `publish_ready = pass` but F016 is parked / absent at run time, the publish asset FAILS
  CLOSED -- it HALTS, records `blocking_reason` "F016 publish adapter not available" with the
  named owner, terminates the run `failed`, and NEVER publishes itself as a fallback. The publish
  wall holds even when the only authorized publisher is absent (Principle II).
- When `retail validate` cannot connect (no creds / DB down), the validate asset records a
  `deferred-boundary` result with its timestamp -- it does NOT fabricate a pass and does NOT mark
  Gold Ready (Principle VIII; the live run is gated on creds).

## The project shape (BUILT, spec 134)

The adapter ships as a SEPARATE, dependable, upgradeable Dagster project -- consumed as an
external dependency, never forked (Principle II) -- with its OWN virtual environment so the
main package's static core stays stdlib-only:

```text
orchestration/dagster/
  README.md                                  # how to run the adapter, the human seams, the gate-read posture
  pyproject.toml                             # pins dagster==1.13.14; brings seshat-bi[dbt] (dagster-dbt dropped, spec 135 FR-011)
  src/tower_bi_orchestration/
    definitions.py                           # the Definitions object (assets/jobs/schedules/sensors)
    repo.py                                  # repo-root + mapped-table discovery (mappings/<table>/source-map.yaml)
    evidence_writer.py                       # re-export of the ONE evidence impl (seshat.dagster_adapter.evidence)
    db.py / commands.py                      # DSN boundary (deferred without creds); the SAME gate commands CI runs
    assets/{ingest,gates,downstream}.py      # the 11 assets + live_validate (STOP / HUMAN-SEAM semantics)
    jobs.py                                  # full_sequence_job + through_gold_job
    schedules.py / sensors.py                # one daily schedule + one file sensor, BOTH default_status=STOPPED
  run-evidence/
    <run-id>.md                              # a filled copy of templates/dagster-run-evidence.md per run
  tests/                                     # in-process materialize() tests (US1-US3) + definitions-load smoke
```

The control layer lives in the main package (`src/seshat/dagster_adapter/`: read-only gate
readers, doctor, shell-free closed-argv runner, redaction, evidence validate/render) and the
CLI family is `seshat dagster doctor|run|evidence` (exit codes 0..4; see
`specs/134-activate-dagster-mvp/contracts/dagster-cli.md`). Raw per-run records land under the
git-ignored `.seshat/dagster/runs/<run-id>/` (schema
`schemas/dagster-run-evidence.schema.json`); the committed record is the rendered
`orchestration/dagster/run-evidence/<run-id>.md`.

## The dbt engine seam (ACTIVATED as a selectable engine; spec 135)

`silver_tables` / `gold_tables` have a SELECTABLE build engine (spec 135, activating the seam
spec 134 left as documentation). The default engine is the committed `warehouse/migrations/*.sql`
path. When a table's committed `mappings/<table>/build-engine.yaml` names `dbt` for a layer, that
asset runs the governed dbt build through the `seshat.dbt` control layer (plan -> self-accepted
accept-plan digest -> build into isolated shadow schemas) INSTEAD of applying migration SQL --
with IDENTICAL gate semantics: still downstream of the `source_map` HUMAN SEAM, still gated on the
same `seshat check` exit codes, still fail-closed. The engine resolves per layer and FAILS CLOSED
to migrations on anything but the exact `dbt` value; the flag lives inside the human-reviewed
committed working set so flipping it is a reviewed, attributable change.

Naming vs mechanism: the seam is historically named the "dagster-dbt engine seam", but the
EXECUTION PATH deliberately routes through `seshat.dbt` (which enforces the accept-plan digest and
the governed gate), NOT through native `dagster-dbt` asset wiring (`@dbt_assets` / a raw
`DbtCliResource`) -- native wiring would bypass the digest and the gate (spec 133 FR-023/FR-025).
The `dagster-dbt` LIBRARY was consequently DROPPED (spec 135 FR-011 owner decision, 2026-07-17):
no released dagster-dbt accepts dbt-core 1.12 and it sits on no execution path. What lands on the
dbt engine's path is `seshat-bi[dbt]`, the governed control layer.

The dbt engine is a governed REHEARSAL into isolated shadow schemas: it does NOT rebuild the real
`silver`/`gold` (spec 133 FR-005), so evidence records `warehouse_updated: false`, `seshat dagster
doctor` warns on mixed-engine tables, and migrations remain the default / parity oracle / rollback
until a named human retires them (spec 133 FR-006). Live dbt drive stays `[PENDING LIVE PROFILE]`
(`docs/operations/dbt-activation-status.yaml`); this feature ships the selectable-engine WIRING,
not a proven live run.

## Relationship to the other features

- **F005 `retail-orchestrate` (the conductor sibling).** Same medallion sequence, same gate-exit
  authority, same two human seams, neither self-approving. `retail-orchestrate` is the
  conversational / interactive runtime; Dagster is the unattended / CI runtime. Where the
  conductor says "I will pause and ask," Dagster says "I will halt this asset and surface the
  open blocker." The sequence is cited from `specs/005-layer-d-orchestration/spec.md`, not
  redefined.
- **F029 dbt Transformation Adapter.** When the dbt engine is selected, the silver / gold build
  steps Dagster orchestrates run the governed dbt build through the `seshat.dbt` control layer
  (NOT native `dagster-dbt` wiring, which would bypass the governed gate). F029 owns HOW the
  transformations are defined and validated; F030 owns the SEQUENCING and gate-respecting
  execution of them. On the default engine the build steps are SQL-migration assets; the gate
  semantics are identical either way.
- **F024 Companion-Tools Architecture (the category parent).** Dagster declares the single
  category Execution Adapter / `DB-connected` against the F024 matrix. The unattended / CI flavor
  is real but does NOT make it Maintenance Automation -- that category declares no connectivity
  level, and Dagster crosses a live DB boundary and triggers publish. A tool declares exactly one
  category (the closed set; Principle VI).
- **F016 Power BI Execution Adapter (parked, execution-only, last).** Dagster's terminal publish
  asset TRIGGERS F016 once `publish_ready = pass`; Dagster never publishes itself. F016 remains
  the only feature allowed to materialize / publish a Power BI model.
- **F031 / F033 (sibling policy, referenced, not depended on).** The shared cross-adapter
  auto-update / maturity policy is owned by F031 (spec 025, adapter-maintenance-policy) and F033
  (spec 027, release-maturity). This adapter states only its adapter-specific update needs.

## Auto-update posture (Dagster-specific; the shared policy is deferred)

Pin `dagster` exactly (the `dagster-dbt` pin was dropped by spec 135 FR-011; the governed dbt
runtime arrives via `seshat-bi[dbt]`); updates via PR only; a definitions-load smoke test as the
minimum CI gate; a small orchestration smoke test once an implementation exists; NO automerge for
Dagster MAJOR versions. The SHARED cross-adapter policy is deferred to F031 (spec 025) / F033
(spec 027).

## Secrets (Principle IX)

The adapter reads credentials from the git-ignored `.env` only (e.g. `DATABASE_URL` or the
`ANALYTICS_DB_*` set); the only committed connection file is a `profiles.example.yml` /
`.env.example` carrying PLACEHOLDER values. No real host, DSN, or credential is ever committed.
Validation runs are READ-ONLY.

## See also

- The decision record: `docs/decisions/0010-dagster-is-orchestration-adapter.md`.
- The run-evidence record shape: `templates/dagster-run-evidence.md`.
- The agent-side companion skill (when / how to invoke; the gate-read posture):
  `.claude/skills/dagster-orchestration-adapter/SKILL.md`.
- The copy-me adapter declaration: `templates/adapter-contract.md`.
- The category parent + the authority matrix: `docs/architecture/product-modules.md`;
  `docs/decisions/0008-core-authority-vs-product-modules.md`.
- The conductor sibling + the sequence it reuses: `.claude/skills/retail-orchestrate/SKILL.md`;
  `specs/005-layer-d-orchestration/spec.md`.
- The transformation adapter it orchestrates through the `seshat.dbt` control layer:
  `.claude/skills/dbt-transformation-adapter/SKILL.md`; `specs/023-dbt-transformation-adapter/` (F029).
- The parked publish adapter it triggers: roadmap F016 (Power BI Execution Adapter).
- The readiness spine + the four-status / no-score vocabulary:
  `docs/readiness/readiness-model.md`; the stage sequence `docs/readiness/readiness-pipeline.md`.
- The spec: `specs/024-dagster-orchestration-adapter/spec.md`. The constitution it instantiates:
  `.specify/memory/constitution.md` (Principles I, II, IV, V, VII, VIII, IX).
- The replay reference (cited, never inlined): a filled worked example under `docs/worked-examples/`.
