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
  (`pipx inject seshat-bi psycopg2-binary` or `pip install "seshat-bi[db]"`, set
  `DATABASE_URL` or `ANALYTICS_DB_*` in the gitignored `.env`), mark numbers
  `[PENDING LIVE PROFILE]`, and STAY USEFUL
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
Active plan: `specs/149-pbi-mcp-write-adapter/plan.md` (F016 slice 5 -- the approval-gated
Power BI MCP write adapter, ratified 2026-08-18). Implementation MERGED (#659) and every
post-write validation follow-up CLOSED: #657 (#670), #663 (#672), #661 + #663 (#674).
#658 stays OPEN but is down to ONE item of its three: the env allowlist shipped
(`allowed_vendor_environment`, applied at the spawn site) and #679 recorded the resolved
`serverInfo.version` in evidence, so an unpinned run is at least attributable. The
runtime-version PIN is blocked until Microsoft publishes a non-prerelease (re-measured
2026-08-21: still only `0.5.0-beta.2`..`.12`, `latest` = `0.5.0-beta.12`) -- which is why
the marker rests here rather than on newer work.
**Spec 155 (guided setup execution) is IMPLEMENTED, awaiting ratification** -- `seshat
integrations setup --derived` selects only the components a project's committed evidence
needs, then provisions them through the existing installer behind spec 154's committed
`governance` approval. `DEFAULT_PROFILE` and every `--profile` run are untouched; the
bridge is `integrations/guided_setup.py`, deliberately NOT `derivation.py`, because two
shipped spec-153 tests assert that file holds no execution or approval call site. Its
spec.md is still `Draft`: implementation shipped on the owner's instruction, and no agent
may write the `ratified` line.
**Specs 153 and 154 are COMPLETE** -- capability derivation with requirement strength and
declines, and the committed named-human provisioning approval read at HEAD (`--apply` is
intent; `--yes` only suppresses the prompt; neither authorizes).
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
