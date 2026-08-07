---
name: dbt-transformation-adapter
description: >-
  Run dbt as the build ENGINE for silver/gold ONLY behind the Mapping Ready gate,
  and record its run/test/parity output as DERIVED evidence -- never as an approval.
  Use when someone asks to build silver/gold for a mapped table with dbt, run dbt
  tests, or check dbt parity against the existing gold tables in the Seshat BI repo.
  dbt is the engine; Seshat BI is the brain. This skill READS the approved map,
  EXECUTES approved dbt steps behind the gate, and WRITES evidence; it never defines
  meaning, never moves a stage to pass, and HARD-STOPS at every human judgment call.
---

# dbt-transformation-adapter

- **Authority category (F024):** Execution Adapter / `DB-connected` (NOT publish-capable).
- **Roadmap feature:** F029  **On-disk spec:** `specs/023-dbt-transformation-adapter`.

dbt is the build ENGINE: it compiles SQL, materializes models, and runs tests. Seshat BI
is the brain: it owns the approved source-map, the metric contracts, and the readiness
spine, and routes every judgment call to a named human. This skill is how the agent runs
dbt without letting it become the brain. You (the agent reading this) ARE the runtime; this
skill is procedure, not an engine -- there is no daemon, no scheduler, no auto-approver.
See `docs/decisions/0009-dbt-is-transformation-adapter.md` and
`templates/dbt-adapter-contract.md`.

> ACTIVATED: feature 133 added the governed runtime under `dbt/`, the pinned
> `dbt-core==1.12.0` + `dbt-postgres==1.10.2` extra, and the `seshat dbt`
> command family. Use that wrapper only; raw dbt commands bypass the accepted-plan,
> selector, shadow-schema, redaction, lock, and evidence contracts.

## Scope boundary (read first)

Invoke-and-record only. This skill runs dbt behind the gate and records its findings as
evidence; it does NOT define source mapping, metric contracts, or semantic logic, does NOT
publish Power BI, and does NOT move a readiness stage to `pass`. Three non-negotiables:

This adapter is not the owner of generic dbt competence. Model-authoring advice, generic
test design, command syntax, documentation lookup, MCP configuration, and troubleshooting
belong to the official dbt Labs agent skills and dbt MCP. Their activation and discovery
must be proven by Phase 6 before routing to them. This skill owns only Seshat's governed
pre-gate, invocation policy, evidence normalization, parity interpretation, and human-stop
seams around the official dbt Core executor; it must not reproduce upstream instructions.

- **The entry gate is the FIRST refusal point** (Principle IV). The canonical gate
  signal is `mappings/<table>/readiness-status.yaml` -> `stages.mapping_ready.status ==
  pass` WITH a matching `approvals[]` entry (RS1); its human-readable mirror
  `unresolved-questions.md` `Gate status: CLEARED` (zero open rows) MUST agree. dbt may
  run NO staging/silver/gold model unless that canonical signal holds -- a missing
  readiness-status file, `mapping_ready != pass`, or a mismatch between the two ->
  Refuse + record a `blocking_reason`. The presence of dbt model files is NOT
  permission to build.
- **A green `dbt test` is EVIDENCE, never an approval** (the governance hinge). Record the
  pass/fail counts as `evidence[]` / `blocking_reasons[]`; Tower readiness + a named human
  move Silver/Gold Ready to `pass`, citing that evidence + the approval. There is NO path
  by which a green run alone writes `pass`.
- **dbt stops at gold** (Principle III). dbt is `DB-connected`, not publish-capable;
  materializing/publishing a Power BI model is the parked F016 adapter, gated separately.

**ASCII only, UTF-8 no BOM** in everything you author (`--`, `->`; no em-dash / smart-quote
/ unicode-arrow).

## Run-state: read mappings/<table>/ FIRST (no new state file)

Compute what you may do from what is already on disk -- there is NO dbt orchestration state
file to create:

| What you observe | Action |
|------------------|--------|
| `mappings/<table>/readiness-status.yaml` missing, or `stages.mapping_ready.status` != `pass`, or its `approvals[]` entry is absent, or the `unresolved-questions.md` `Gate status: CLEARED` mirror does not agree | **REFUSE.** Record a `blocking_reason` ("Mapping Ready not pass"); run no model. |
| `stages.mapping_ready.status == pass` WITH a matching `approvals[]` entry, the `Gate status: CLEARED` mirror agrees, approved `source-map.yaml` present | **Permitted** to run staging/silver/gold models that CITE the approved map. |
| A dbt model builds a meaning (grain/PK/PII/placement) the map does NOT state | **DEFECT.** The model cites the map, it does not extend it; the map is re-approved first. |
| The table is already built by migrations | The dbt mart must pass the **reconciliation parity test** before it can become the build path. |

You may READ Mapping Ready; you may NOT write `pass` to any stage (that is the named human's
action). Read the approved map by path + git ref; every model must cite it.

## Fixed sequence (use the governed wrapper only)

| Step | What you do | Authority note |
|------|-------------|----------------|
| 1 Prerequisites | Run `seshat dbt doctor --format json`. It queries no database. | Missing runtime/profile values -> `[PENDING LIVE PROFILE]`. |
| 2 Gate + citations | Run `seshat dbt validate --table <table> --format json`. | Refuses before planning unless Mapping Ready has the named-human approval and every selected model cites it. |
| 3 Immutable plan | Run `seshat dbt plan --table <table> --format json`; review the exact nodes, target, versions, mapping identity, and shadow schemas. | The returned digest accepts execution, not business meaning or readiness. |
| 4 Build | Run `seshat dbt build --table <table> --accept-plan <digest> --format json`. | Recomputes the plan before DB access; drift refuses execution. |
| 5 Test-only rerun | When needed, run `seshat dbt test --table <table> --accept-plan <digest> --format json`. | Evidence, never approval. |
| 6 Offline review | For an existing run directory, run `seshat dbt inspect-run --table <table> --artifacts <run-directory> --format json`. | Revalidates artifacts; it is not a second build. |
| 7 Recommend + STOP | Report normalized evidence and `blocking_reasons`, then stop for a named human. | Never self-approve or switch away from migrations. |

## The reconciliation parity test (four assertions, exact to the cent)

For a table already built by migrations, assert against the migration-built gold fact:

1. equal fact row count;
2. preserved distinct count of the fact's degenerate / business key;
3. each additive money-measure sum equal to the cent -- absolute delta `<= 0.01` per
   additive measure, matching the committed money scale (e.g. `NUMERIC(12,2)`);
4. equal per-dimension distinct member counts -- each conformed dimension's member count,
   including any unknown / sentinel member where the gold model defines one.

A mismatch -> record the measured delta as a `blocking_reason`, keep Gold Ready `blocked`,
keep migrations the default. After an approved switch, the migration files are RETAINED as
the parity oracle; the parity test RE-RUNS on EVERY dbt build while the oracle is retained
(never one-time-at-switch). The cent tolerance is the stated default -- NOT a score.

## HARD-STOP: the Principle V judgment calls (never auto-resolve)

STOP and escalate to a named human; record an owner row -- do not edit around any of these:

- a grain ambiguity, or a model that would change the declared grain (e.g. collapse line
  items) -- forbidden without a re-approved map.
- a sentinel-vs-null choice (e.g. an unknown-member handling that diverges from the
  migration's sentinel -- the parity test catches the divergence; resolving it is a human call).
- a PII publish-safety question on any column.
- a business rollup / segment mapping the map does not answer.
- moving Silver Ready / Gold Ready to `pass` -- always a named-human approval, never a
  green `dbt test`.
- a build-path switch (migrations -> dbt) -- only after parity passes AND a human approves;
  never flip the default on your own; never delete the migration oracle.
- any dbt-core / dbt-postgres major (and, until compatibility tests exist, minor) version
  bump -- a named reviewer approves; no automerge.

## Live and downstream seams (report and stop, never fake)

- **A live dbt run** -- needs the `dbt` extra, a DB, and `SESHAT_DBT_*` values
  in the gitignored `.env`; committed `profiles.example.yml` contains only
  `env_var()` references. Without them, report `[PENDING LIVE PROFILE]`, the
  enable steps, and no compile/build/test/parity success.
- **The Power BI build** -- F016 (parked, publish-capable, gated on Semantic Model Ready);
  dbt stops at gold and does not touch it.

At a seam: state plainly what is deferred, what would unblock it, and STOP.

## See also

- The decision record: `docs/decisions/0009-dbt-is-transformation-adapter.md`.
- The contracts: `templates/dbt-adapter-contract.md`, `templates/dbt-model-contract.md`.
- The integration doc + the governed `dbt/` runtime: `docs/integrations/dbt-adapter.md`.
- The example connection profile: `profiles.example.yml` (placeholders only).
- The category contract: `docs/architecture/product-modules.md`; the copy-me Adapter
  declaration: `templates/adapter-contract.md`.
- The planning history: `specs/023-dbt-transformation-adapter/`; the activation
  implementation: `specs/133-activate-dbt-mvp/`.
- `.specify/memory/constitution.md` (Principles III, IV, V, VI, VII, VIII, IX).
- The filled first-MVP instance is CITED, never inlined: a worked example under `docs/worked-examples/`.
