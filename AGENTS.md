# AGENTS.md -- operating rules for agents in this repo

Seshat BI is **agent-first**: you (the agent) are the interface; the CLI
gates (`seshat check`, `retail validate`) are helpers you CALL, never the product.
This file is the short operating contract. The full law is
`.specify/memory/constitution.md`; the spine is `docs/readiness/readiness-model.md`.

> **Naming.** The product is **Seshat BI** (package alias `Seshat_BI`). It was
> previously developed under the internal name *Tower BI Agent Kit*; the
> governance spine is still the **Readiness System**. Same product, one brand.

## Decide from readiness state

- Read the table's **readiness status** (`templates/readiness-status.yaml` shape)
  to find `current_stage` and `next_action`. Launch the workflow for THAT stage
  only -- never skip ahead.
- The seven stages, in order: Source -> Mapping -> Silver -> Gold -> Semantic
  Model -> Dashboard -> Publish. A stage is entered only when the prior is `pass`.
- The `retail-orchestrate` conductor sequences the verbs; the readiness status
  records the state. Recompute `current_stage` from committed artifacts +
  `Gate status` + migration presence -- there is no separate run-state engine.

## Hard stops (never cross these)

- **Do NOT proceed to silver when `mapping_ready` is `blocked`** (or `Gate status`
  is not `CLEARED`). No `silver.*` SQL before an approved map (Principle IV).
- **Do NOT point Power BI at gold before `retail validate` passes** (Principle VIII).
- **Do NOT design dashboards before metric contracts exist** (roadmap rule 5).
- **Do NOT run the Power BI execution adapter** (the official Power BI MCP /
  connection; `pbi-cli` no longer the preferred path) -- that is feature 016, last
  and gated on `semantic_model_ready` (Principle II). It is a later, EXECUTION-ONLY
  adapter (it cannot define metrics, mappings, semantic logic, or dashboard design);
  no current stage depends on it.
- **Do NOT self-grant an approval.** Approvals are named human actions
  (Principle V): grain, PII publish-safety, business rollups, sentinel-vs-null.

## Report blockers explicitly

- A `blocked` stage MUST carry `blocking_reasons` -- a concrete fact, not "needs
  work". Record it in the status + `blocking-reasons.md`; then STOP.
- Readiness is `status + evidence + blockers`, NEVER a fabricated confidence
  number. A `pass` MUST cite `evidence`. Do not emit a score (scoring is deferred).
- `seshat check` exit 0 is NECESSARY, not SUFFICIENT -- semantic correctness is
  proven only by the live `retail validate`. Do not let green read as "correct".

## Live DB steps -- graceful deferred mode

- The live boundary (`retail validate`, profiling against a DSN) needs the `db`
  extra + a DSN. If absent: report the boundary + the enable steps
  (`pip install 'retail[db]'`, set `DATABASE_URL` or `ANALYTICS_DB_*` in the
  gitignored `.env`), mark numbers `[PENDING LIVE PROFILE]`, and STAY USEFUL
  (author artifact structure). NEVER traceback, NEVER fake a pass.
- Secrets only in the gitignored `.env`. NEVER commit a real host/DSN. Power BI
  params use the `<placeholder>` form -- `G6` + `C2` block a real host at the gate.
  (Power BI Desktop re-writes the real host into `expressions.tmdl` on save;
  revert `powerbi/` before committing.)

## C086 is an example, never a schema

- C086 is the first worked example / a filled instance -- evidence the gate works.
  NEVER treat it as a universal schema. Generic templates carry no pharmacy
  specifics (billing codes, segment rollups, insurance PII). The questions and
  gates generalize; the answers are per-table (Principle VII).

## The verbs you compose

`retail-orchestrate` (conductor) -> `source-mapping` (the gate) ->
`retail-build-warehouse` (authors silver/gold SQL, stops before executing) ->
`retail-validate` (live checks) -> `retail-govern` (static check) ;
`pbip-workflow` (PBIP git/TMDL). Each verb does its job and STOPS; the self-heal
loop lives only in the conductor.

Kit / tooling verbs (outside the medallion sequence): `retail-init` (bootstrap the
Compass-Driven kit substrate + route a new user to a first profile) ;
`retail-scaffold` (author a NEW `seshat check` rule, or `--doctor` an existing rule's
wiring -- the authoring sibling of `retail-govern`, which interprets rule findings).

## See also

- Compass: `COMPASS.md`.
- Constitution: `.specify/memory/constitution.md` (Principles I, IV, V, VII, VIII).
- Readiness: `docs/readiness/readiness-model.md`, `readiness-pipeline.md`.
- Roadmap: `docs/roadmap/roadmap.md`. Architecture: `docs/architecture/`.
- Repo rules (secrets, PBIP, Windows): `CLAUDE.md`.
<!-- SPECKIT START -->
Active Spec Kit implementation plan: `specs/134-activate-dagster-mvp/plan.md`.
<!-- SPECKIT END -->
<!-- SESHAT-KIT START -->
**Seshat BI kit router** (v0.2.0) -- generated from `.seshat/kit-source.yaml`; do not edit here.

Orient first: *What readiness stage am I serving?* State lives in `readiness-status.yaml (per TABLE, recomputed)` (recomputed; this file stores none).

Verbs the agent drives:
- `retail-orchestrate` -- conductor -- sequence the medallion verbs, self-heal against the gate
- `first-hour-compass` -- first-arrival worked-example offer + single-source seam list + single-table orientation card
- `retail-onboard-table` -- Source->Mapping front door; owns the Stage-1 read-only DB-backed profile (grain candidates, column types)
- `retail-discover-portfolio` -- metadata-only portfolio discovery -> governed domain/scope proposals -> selected-table onboarding -> interview handoff
- `business-knowledge-interview` -- after DB discovery, interview the owner into the Decision Store (batch low-risk, explicit critical); records decisions, never self-grants approval
- `source-mapping` -- the mapping gate -- produces source-map.yaml
- `kpi-contract-builder` -- drive the shipped kpi_contracts engine: assess answerability, list the decisions to approve, preview with per-field provenance, then draft/finalize -- never self-grants approval
- `retail-build-warehouse` -- author silver/gold SQL; stop before executing
- `retail-validate` -- live checks; needs db extra + DSN, else [PENDING LIVE PROFILE]
- `retail-govern` -- static check (seshat check)

Hard-stops (orientation the agent reads; enforcement is the lint rules + G6/C2, not this file):
- never_self_grant_approval
- no_silver_before_mapping_cleared
- no_dashboard_before_metric_contracts
- never_fabricate_a_confidence_score
<!-- SESHAT-KIT END -->
