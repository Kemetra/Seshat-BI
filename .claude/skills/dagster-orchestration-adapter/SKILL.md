---
name: dagster-orchestration-adapter
description: >-
  Run the medallion sequence UNATTENDED / in CI as a Dagster asset graph -- the
  scheduler sibling of the retail-orchestrate conductor -- running ONLY already-approved
  steps behind every gate, and recording what each asset DID as DERIVED run-evidence.
  Use when someone asks to schedule the pipeline, run the medallion in CI, "orchestrate
  unattended", or wire Dagster in the Seshat BI repo. Dagster RUNS approved steps; Tower
  BI (the gate exit code + the named human) decides whether a stage passed. This skill
  READS committed approvals as the GO signal, EXECUTES approved steps behind STOP /
  HUMAN-SEAM edges, and WRITES run-evidence; it never defines meaning, never moves a stage
  to pass, never publishes Power BI (it only TRIGGERS F016), and HARD-STOPS at every human
  judgment call.
---

# dagster-orchestration-adapter

- **Authority category (F024):** Execution Adapter / `DB-connected` (NOT publish-capable; it
  TRIGGERS F016, it never publishes). The F024 enumerated declaration -- see
  `docs/architecture/product-modules.md`.
- **Roadmap feature:** F030  **On-disk spec:** `specs/024-dagster-orchestration-adapter`
  (dir 024 == F030; when the dir number and the F-number disagree, the roadmap F-number wins).

Dagster is the unattended / CI RUNTIME for the medallion sequence: a scheduler / pipeline runs
the asset graph so a human does not re-type each step. `retail-orchestrate` (F005) is the
INTERACTIVE conductor of the SAME sequence; Dagster is its unattended sibling -- same medallion
sequence, same gate-exit authority, same two human seams, neither self-approving. Tower BI (the
gate exit code + the named human) is the brain; Dagster is the runner. This skill is how the
agent reasons about running the medallion unattended without letting the orchestrator become the
brain. You (the agent reading this) ARE the design surface; this skill is procedure, not an
engine -- the engine, when built, is the separate Dagster project. See
`docs/decisions/0010-dagster-is-orchestration-adapter.md` and
`docs/integrations/dagster-adapter.md`.

> STATUS: the Dagster PROJECT is BUILT (spec 134, activation slice of F030).
> `orchestration/dagster/` exists -- `definitions.py`, the 11-asset graph, `jobs`,
> one STOPPED schedule, one STOPPED sensor, `pyproject.toml` pinning
> `dagster==1.13.14` + `dagster-dbt==0.29.14` TOGETHER -- plus the
> `seshat dagster doctor|run|evidence` control layer. The OPERATIONAL procedure:
>
> 1. `seshat dagster doctor` -- read-only preflight (project, its own venv
>    under `orchestration/dagster/.venv`, the pinned pair, per-table gate
>    state, DSN present/absent). Blockers exit 2; the install remedy is
>    `cd orchestration/dagster && uv venv .venv && uv pip install -p .venv -e ../.. -e ".[dev]"`.
> 2. `seshat dagster run --job <full_sequence_job|through_gold_job> [--table <table>]`
>    -- executes the graph as a shell-free child process in the orchestration
>    venv. A failed/blocked gate halts downstream assets and exits 3 (the CI
>    signal); report it with the recorded blocking_reason + named owner.
> 3. `seshat dagster evidence [--run-id <id>]` -- list runs / render the
>    committed record at `orchestration/dagster/run-evidence/<run-id>.md`.
>
> Without DB credentials the DB-touching assets record a deferred boundary and
> block fail-closed -- report that truthfully; never fake a run.

## Authority declaration (F024) -- the filled adapter contract

This adapter declares EXACTLY ONE of the five F024 authority categories. Quoted verbatim from
`docs/architecture/product-modules.md`: an **Execution Adapter** is "a tool that crosses an
external trust/connectivity boundary to MATERIALIZE or PUBLISH an already-approved artifact. An
adapter MUST declare exactly one connectivity level: `local-only` | `DB-connected` |
`external-service-connected` | `publish-capable`. It is execution-only and gated; it never
defines metrics, mappings, semantic logic, or dashboard design." Dagster's connectivity level is
**`DB-connected`** -- the STRONGEST boundary it itself crosses (it loads bronze, runs
migrations, runs `retail validate` against a live Postgres). It is NOT `publish-capable`: the
terminal asset TRIGGERS the parked F016 Power BI Execution Adapter and Dagster opens no Power BI
connection itself.

The filled `templates/adapter-contract.md` declaration follows.

---

### Adapter Contract -- Dagster Orchestration Adapter

- **Authority category:** Execution Adapter
- **Connectivity level:** `DB-connected`  *(exactly one -- the STRONGEST it uses; it TRIGGERS the publish-capable F016 but never publishes itself)*
- **Product layer:** `1`  *(Layer D / orchestration -- the functional axis; it SEQUENCES all seven readiness stages and DECIDES none)*
- **Roadmap feature:** `F030`  **On-disk spec:** `specs/024-dagster-orchestration-adapter`
- **Owner:** orchestration / platform owner (a named human; Dagster never self-approves)
- **Status:** BUILT (spec 134 activation slice: the `orchestration/dagster/` runtime project + the `seshat dagster` control layer + CI definitions-load smoke; automations ship STOPPED)

#### What it does (one line)

> Runs the already-approved medallion sequence unattended / in CI as an asset graph, behind
> every gate, and records what each asset DID as derived run-evidence -- deciding no stage and
> publishing nothing (it only TRIGGERS F016 once `publish_ready = pass`).

#### Gate it is DOWNSTREAM of

An orchestrator runs MANY gated steps, so the gate is PER-ASSET, not one stage. Each gated asset
runs only after its own gate is satisfied; the asset fails closed / blocks if it is not. The
load-bearing gates:

- **Gated on stage (per asset):** `silver_tables` is gated on **Mapping Ready** (the committed
  `Gate status: CLEARED` + zero open rows); `semantic_model` is gated on the committed
  semantic-model / metric approval; `dashboard_blueprint` is gated on **Semantic Model Ready**;
  `publish_execution_evidence` is gated on **`publish_ready = pass`**. The mechanical STOP nodes
  (`silver_tables`, `gold_tables`, `semantic_model`) are gated on a literal gate exit 0.
- **Required approval / evidence:** for human-seam assets, the committed approval read from disk
  (the `Gate status` field; the `approvals[]` owner+date in
  `mappings/<table>/readiness-status.yaml`). For mechanical assets, the `retail check` /
  `retail validate` exit 0.
- **Fail-closed behavior:** a failed gate asset HALTS and propagates the stop to every
  downstream asset (a STOP edge); a human-seam asset whose approval is absent BLOCKS and runs
  nothing. In both cases the run terminates with a non-zero / failed Dagster run status (the CI
  signal) and records the concrete blocker + named owner. See the asset graph below.

#### Boundaries it CROSSES (connectivity)

- Opens a connection to a live database to load bronze and run silver/gold migrations or dbt
  builds (DB-connected).
- Connects to the live database (read-only) to run `retail validate` (DB-connected).
- TRIGGERS the publish-capable F016 adapter when `publish_ready = pass` -- it does NOT itself
  cross the publish boundary (no Power BI connection; F016 owns publish).
- No other external boundary.

#### Approved artifact it MATERIALIZES / PUBLISHES

The definition MUST already exist in Core Authority. The adapter executes it; it does not author
it.

- Materializes silver / gold from the APPROVED `source-map.yaml` (after Mapping Ready) -- via
  `dagster-dbt` where dbt is adopted (F029), or via SQL-migration assets otherwise; identical
  gate semantics either way.
- Generates the handoff pack from already-approved upstream evidence.
- Publishes NOTHING itself; the terminal asset TRIGGERS the already-approved F016 publish once
  `publish_ready = pass`.

#### Derived run-evidence it WRITES

A RUN RECORD (what ran, when, with what result) as derived evidence. Never a new truth or
approval.

- A per-run record at `orchestration/dagster/run-evidence/<run-id>.md` (a filled copy of
  `templates/dagster-run-evidence.md`): per-asset gate command + exit code + measured numbers +
  outcome (`materialized` / `failed` / `skipped` / `blocked` -- never the readiness token
  `pass`), timestamps, commit sha, and per blocked/skipped asset the concrete `blocking_reason`
  + named owner.
- Those measured results are ALSO surfaced as `evidence[]` / `blocking_reasons[]` on the
  affected table's `mappings/<table>/readiness-status.yaml`. Whether that evidence MARKS any
  stage `pass` is Core Authority's record, never Dagster's write.

#### Secrets handling (Principle IX)

- **Credentials:** reads the git-ignored `.env` keys only -- e.g. `DATABASE_URL` or the
  `ANALYTICS_DB_*` set; NEVER inline real values.
- **Committed example only:** a `profiles.example.yml` / `.env.example` with placeholder values
  only -- never a real host / DSN / credential.

#### Forbidden operations (the matrix says NO)

These hold for EVERY Execution Adapter regardless of connectivity level:

- MUST NOT define metrics, mappings, semantic logic, grain, rollup, segment, PII disposition, or
  dashboard design (execution-only).
- MUST NOT create truth or grant approval / move a stage to `pass`; MUST NOT write a readiness
  `status` or a `Gate status: CLEARED`; MUST NOT invent a parallel approval marker (named-human
  / Core Authority only).
- MUST NOT execute a gated asset when its required approval / evidence is absent -- it fails
  closed.
- MUST NOT publish a Power BI model or open a Power BI connection; the connectivity level is
  `DB-connected`, not `publish-capable` (it may only TRIGGER F016).
- MUST NOT emit a numeric / maturity / confidence score in run evidence (hard rule #9).
- MUST NOT run a gate around a failed upstream gate (no run-around of a STOP edge).
- MUST NOT commit real hostnames / DSNs / credentials (Principle IX).

#### How it handles a missing definition or approval

When the artifact it would execute is undefined, or the gate it is downstream of is not `pass`,
the adapter SURFACES it as a blocker, HALTS the affected asset, and terminates the run `failed`
(the CI signal) -- it never invents the definition, self-approves, or executes past the missing
gate (Principle V; stop-and-ask). A judgment call surfaced mid-run (grain / PII / rollup /
segment / sentinel-vs-null) HALTS the affected asset and escalates to the named owner.

---

## Scope boundary (read first)

Sequence-and-record only. This skill RUNS approved steps behind the gate and records what each
asset did as evidence; it does NOT define source mapping, metric contracts, or semantic logic,
does NOT publish Power BI, and does NOT move a readiness stage to `pass`. Three non-negotiables:

- **The gate exit code is the SOLE pass authority** (Principle I -- agent proposes, gate
  disposes). A Dagster asset's success means "the command ran and returned this exit," NEVER
  "the stage is now `pass`." A green `retail check` / `retail validate` asset records exit-0
  EVIDENCE; Core Authority's process (and a named human at the human-seam stages) records the
  stage `pass`. There is NO path by which a green asset alone writes `pass`.
- **Two hard human seams you MUST halt at** (mirrored from `retail-orchestrate`):
  1. **Mapping gate (Principle IV):** no `silver_tables` until the map is reviewed and approved.
     Read approval from existing state -- you may READ `Gate status`; you may not write
     `CLEARED` yourself (approval is the reviewer's action). Do NOT invent a parallel
     "APPROVED-FOR-SILVER" marker -- that forks an existing field into two sources of truth.
  2. **Judgment calls (Principle V):** grain, PII publish-safety, business rollup, the
     authoritative returns column, sentinel-vs-null -- HALT the affected asset and escalate to a
     named human; do not decide them to make a finding go away.
- **Dagster stops at the publish wall** (Principle II). It is `DB-connected`, not
  publish-capable; the terminal asset only TRIGGERS F016 once `publish_ready = pass`. Even when
  `publish_ready = pass` but F016 is parked / absent, the publish asset FAILS CLOSED -- it
  records `blocking_reason` "F016 publish adapter not available" with the named owner and
  publishes nothing as a fallback.

**ASCII only, UTF-8 no BOM** in everything you author (`--`, `->`; no em-dash / smart-quote /
unicode-arrow).

## Run-state: read mappings/<table>/ FIRST (no new state file)

Compute what each asset may do from what is already on disk -- there is NO Dagster orchestration
state file to create; the GO signal is the EXISTING committed gate state, exactly as the
conductor reads it:

| What you observe | Action |
|------------------|--------|
| No `mappings/<table>/` dir | The `source_map` asset is not yet reachable; the front door is `retail-onboard-table` -> `source-mapping`. Run no silver. |
| `Gate status: OPEN` (or any open row) in `mappings/<table>/unresolved-questions.md` | **`source_map` HUMAN SEAM blocks.** `silver_tables` does not materialize; record the open mapping blocker + named owner; write no approval. |
| `Gate status: CLEARED` and zero open rows | The `source_map` seam is satisfied; `silver_tables` is PERMITTED to run (the read of committed approval is the only GO signal). |
| `silver`/`gold` built; a gate asset returns non-zero | **STOP edge.** The asset is `failed`; every downstream asset is `skipped`; the run terminates `failed`. |
| `publish_ready` not `pass` in `readiness-status.yaml` | The `publish_execution_evidence` asset BLOCKS and triggers nothing; record the missing publish approval. |

You may READ `Gate status` / `approvals[]`; you may NOT write `CLEARED` or a stage `pass` to any
artifact (that is the named human's / Core Authority's action). Read approvals by path + git ref.

## The asset graph (gate semantics, not just names)

The planned graph is eleven assets. Each dependency edge is a STOP edge (a failed gate halts all
downstream assets) or a HUMAN-SEAM edge (reads a committed approval and halts if absent -- never
writes it). The full enumerated graph + project shape lives in
`docs/integrations/dagster-adapter.md`; the gate semantics:

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

Mechanical STOP nodes (`silver_tables`, `gold_tables`, `semantic_model`) gate on a literal gate
exit 0. HUMAN-SEAM nodes (`source_map`, `semantic_model` publish-safety, `publish_execution_evidence`)
gate on a committed human approval. The terminal asset TRIGGERS the parked F016 adapter; Dagster
never publishes itself.

## Fixed sequence (run only behind the gate; the SAME commands CI runs)

| Asset | What it runs | Authority note |
|-------|--------------|----------------|
| `bronze_<table>` | Load the raw landing into bronze. | Execute an approved step (DB write). |
| `source_profile` | Profile the source; write profile evidence. | DERIVED evidence only. |
| `source_map` | READ `Gate status` + `approvals[]`. If not CLEARED -> HALT, record the open mapping blocker. | HUMAN SEAM (Principle IV); never self-grant. |
| `silver_tables` | Build silver (dbt via `dagster-dbt`, or SQL migrations); then `retail check`. | STOP edge; gated on `source_map` CLEARED. |
| `gold_tables` | Build the gold star; then `retail check`. | STOP edge; mechanical. |
| `metric_contracts` | READ the approved metric contracts (authors none). | Reads truth; never authors it. |
| `semantic_model` | `retail check` + contract-binding read; READ the semantic-model approval. | STOP + HUMAN SEAM. |
| `dashboard_blueprint` | Produce design evidence. | Gated on `semantic_model` ready. |
| `handoff_pack` | Generate the BI handoff bundle; write evidence. | DERIVED evidence only. |
| `publish_execution_evidence` | READ `publish_ready`. If `pass` -> TRIGGER F016. If F016 absent -> FAIL CLOSED. | Publish wall (Principle II); triggers F016 only. |
| (every asset) | Write the run-evidence record; surface results as `evidence[]` / `blocking_reasons[]`. | DERIVED evidence; never a `pass`. |

At every mechanical gate node, run the SAME command CI runs (`retail check`, and
`retail validate` once creds exist) so the unattended run behaves identically to the conductor's
gate. Validate evidence is recorded; a `deferred-boundary` (no creds / DB unreachable) is
recorded with its timestamp and NEVER fabricated into a pass.

## Fail-closed: a halted run also FAILS the Dagster run status (the CI signal)

A failed gate asset HALTS all downstream assets, which are recorded `skipped` -- not run around.
Beyond writing the run-evidence record, a halted / fail-closed / human-seam-blocked run MUST
itself terminate with a non-zero / failed Dagster run status so an unattended scheduler surfaces
the blocker rather than exiting silently. That failed run status is DERIVED evidence ABOUT the
execution -- it flips NO readiness stage.

## HARD-STOP: the Principle V judgment calls (never auto-resolve)

HALT the affected asset and escalate to a named human; record an owner row in
`mappings/<table>/unresolved-questions.md` -- do not edit around any of these:

- a grain ambiguity, or any step that would change the declared grain.
- a sentinel-vs-null choice; the authoritative returns column.
- a PII publish-safety question on any column.
- a business rollup / segment mapping the approved map does not answer.
- moving Mapping Ready / Silver Ready / Gold Ready / Semantic Model Ready / Publish Ready to
  `pass` -- always a named-human or gate-exit action, never a green Dagster asset.
- triggering a publish when `publish_ready` is not `pass`, or publishing yourself when F016 is
  absent -- FAIL CLOSED.
- any `dagster` / `dagster-dbt` MAJOR version bump -- a named reviewer approves; no automerge
  (pin the pair TOGETHER; the shared policy is F031 / F033).
- any finding you cannot confidently classify -> default to escalate.

## Auto-update posture (Dagster-specific; the shared policy is deferred)

Pin `dagster` + `dagster-dbt` TOGETHER (no independent bumps); updates via PR only; a
definitions-load smoke test as the minimum CI gate; a small orchestration smoke test once an
implementation exists; NO automerge for Dagster MAJOR versions. The SHARED cross-adapter
update/maturity policy lives in F031 (spec 025, adapter-maintenance-policy) and F033 (spec 027,
release-maturity); this skill states only Dagster's adapter-specific needs and DEFERS the rest.

## Seams (deferred by design -- report and park, never fake)

- **A live unattended run** -- needs the DB + a git-ignored credential set (only
  `profiles.example.yml` / `.env.example` with placeholders is committed; Principle IX). Without
  it, report the boundary + the enable steps (supply credentials in the git-ignored `.env`);
  never traceback, never fake a pass.
- **The Power BI publish** -- F016 (parked, publish-capable, gated on Publish Ready); the
  terminal asset TRIGGERS it once `publish_ready = pass` and never publishes itself. If F016 is
  absent, FAIL CLOSED.
- **The dbt build internals** -- F029 owns HOW the silver/gold transformations are defined and
  validated; this adapter owns the SEQUENCING and gate-respecting execution of them via
  `dagster-dbt`. Do not redefine dbt's internals here.

At a seam: state plainly what is deferred, what would unblock it, and STOP. One invocation does
NOT produce a finished, published deliverable -- that is the named-seam design, not a bug.

## See also

- The decision record: `docs/decisions/0010-dagster-is-orchestration-adapter.md`.
- The integration doc + the enumerated `orchestration/dagster/` shape + asset graph:
  `docs/integrations/dagster-adapter.md`.
- The run-evidence record shape: `templates/dagster-run-evidence.md`.
- The copy-me adapter declaration: `templates/adapter-contract.md`.
- The category parent (the five authority categories + the matrix):
  `docs/architecture/product-modules.md`; the decision
  `docs/decisions/0008-core-authority-vs-product-modules.md`.
- The conductor sibling (the gate-read + human-seam posture this mirrors):
  `.claude/skills/retail-orchestrate/SKILL.md`; `specs/005-layer-d-orchestration/spec.md`.
- The transformation adapter it orchestrates via `dagster-dbt`:
  `.claude/skills/dbt-transformation-adapter/SKILL.md`; `specs/023-dbt-transformation-adapter/` (F029).
- The verbs it sequences: `.claude/skills/{retail-onboard-table,source-mapping,retail-build-warehouse,retail-validate,retail-semantic-check}/SKILL.md`.
- The spec + posture: `specs/024-dagster-orchestration-adapter/spec.md`;
  `.specify/memory/constitution.md` Principles I, II, IV, V, VII, VIII, IX.
- The method + exit gates: `docs/medallion-playbook.md`. The readiness spine:
  `docs/readiness/readiness-model.md`. The replay reference (cited, never inlined):
  a worked example under `docs/worked-examples/`.
