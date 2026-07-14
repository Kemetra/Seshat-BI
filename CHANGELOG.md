# Changelog

All notable changes to Seshat BI are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and version numbers follow
`docs/operations/versioning-policy.md` (semver, adapted for a governance kit).

Repository history contains the annotated tag `v0.1.0`, which points to
`b84be67c0316eecab40d35c13640adb2ac202ab3`. That tag records the first tagged kit
snapshot; it does not by itself prove PyPI, GitHub Release, Claude, or Codex public
availability. No index-publication claim is made here without separately captured
public-install evidence. The `[0.1.0]` section below summarizes the repository state
associated with that history. Dates below are merge-to-main dates unless an entry
explicitly identifies a public release event.

## How to update this changelog

- Add new entries under `[Unreleased]`, grouped by `Added` / `Changed` / `Fixed` /
  `Docs` as they land on `main` -- one line per feature/spec, citing the spec number
  and/or PR where practical.
- When the owner bumps the version (per `docs/operations/versioning-policy.md`), the
  `[Unreleased]` section is retitled to the new version number and dated, and a fresh
  empty `[Unreleased]` section is added above it.
- Do not invent or backfill an entry for work that has not merged to `main`. Cite a
  real commit/PR; if you cannot, do not claim it shipped here.
- Keep entries honest about scope: a "docs-only" or "packaging-only" slice is labeled
  as such, matching the spec's own Status line.

## [Unreleased]

Work merged to `main` since `v0.2.0` (`git log v0.2.0..HEAD`):

### Added
- **Spec 127 -- Shareable Seshat Proof (showcase bundle)** (PR #281, ratified PR
  #280): composes existing Explorer, Passport, readiness, review, blocker,
  approval, and lineage evidence into a disclosure-safe static offline bundle.
  Delivered skill/composer-only (Option B, ratified 2026-07-14); no new CLI verb.
- **Spec 128 -- Public Extension-Pack Catalog** (`seshat pack search / inspect /
  add`) (PR #281, ratified PR #280): a discovery/retrieval layer over the shipped
  declarative pack scaffold -- a reviewed static git registry (not a hosted
  marketplace), with hash/schema verification, fail-closed handling of invalid,
  incompatible, missing, or tampered packs, and preserved contributor
  attribution. Extends the shipped `pack` CLI verb group; packs remain
  declarative-only and cannot grant readiness or approval.
- **Spec 129 -- Agent Compatibility Certification** (`seshat agent verify`) (PR
  #281, ratified PR #280): a new CLI verb that certifies agent/tool
  compatibility; output stays local-only (no public catalog submission).
- **Spec 130 -- Friendly PR Reviewer** (plain-language PR summary) (PR #281,
  ratified PR #280): a skill-driven, plain-language summary layer over existing
  PR review evidence.
- **Spec 131 -- Portfolio Watch** (`seshat watch build`) (PR #281, ratified PR
  #280): a recurring, read-only portfolio summary aggregating source drift,
  contract/semantic drift, stale or missing approvals, changed readiness,
  dashboard-intent divergence, and blocker deltas into one prioritized next
  action per governed scope. Delivered agent-/skill-driven like its sibling
  `retail-control-room` (ratified `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`,
  Option B); the one deliberate CLI addition is a narrow, read-only,
  machine-readable summary/status surface mirroring the ratified `status
  --format json` precedent -- not a new broad verb family.
- **Governed existing-PBIP-project adoption** (PR #271): a module that adopts an
  already-authored PBIP project into the governance model, split into focused
  submodules, redacting secret values and failing closed on a bad baseline.
- **Coordinated release preparation workflow** (PR #278):
  `.github/workflows/prepare-coordinated-release.yml`, an owner-triggered
  `workflow_dispatch` action that projects an owner-selected SemVer into
  `pyproject.toml`, the Claude marketplace/plugin manifests, the Codex plugin
  manifest, and both generated bundles in one synchronized draft release PR. No
  tag, publication, or catalog submission is performed by the workflow itself.

### Fixed
- **PBIP adoption: literal Power Query M data-source detection** (PR #279):
  the existing shipped C1 connection-literal boundary rule previously matched
  only assignment-form literals (e.g. `Server="..."`) and missed a literal M
  data source such as `Sql.Database("prod.internal", "DW")`, which went
  unflagged until the project was committed. The fallback boundary scan now
  also matches M data-source literal-argument calls (the safe parameterized
  identifier form is still not matched), raising the same existing C1 fact.
  Per `docs/operations/versioning-policy.md`, this restores C1's documented
  intent rather than changing it, but the change **can newly flag an
  already-committed PBIP project that was previously passing**.
- **PBIP adoption: source-reference inventory** (PR #279): a parsed table
  previously emitted measures and relationships but never recorded its
  partition/M source references. Each table now emits one proposed
  source-reference fact per partition source (the raw M body itself is never
  echoed; literal-credential scanning stays a separate check).
- **`speckit-batch` tolerates JSON-string `args`** (PR #277): the batch runner
  previously broke when `args` arrived as a JSON-encoded string rather than a
  native array/object; it now accepts both.

### Docs
- **v0.2.0 install/support guidance + README landing-page rewrite** (PR #269).

## [0.2.0] -- 2026-07-13

Work from the current roadmap arc (`docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`,
Option B ratified 2026-07-07) that has merged to `main` but not yet been bundled into
an owner-approved version bump:

### Added
- **Spec 120 -- agent ecosystem growth** (eight independently releasable phases, all
  merged to this arc's feature branch):
  - **US1 -- offline HTML readiness proof** (`02271e9`): `seshat demo report
    --format html` renders the seven-stage proof as a deterministic,
    disclosure-safe static page with the honest live boundary.
  - **US2 -- reusable review integration** (`d0316ec`): `retail check --format
    review` (changed-state digest, stable JSON) and `--format sarif`
    (SARIF 2.1.0), plus the read-only composite GitHub action under
    `integrations/github-action/`.
  - **US3 -- read-only agent governor** (`a9b126c`): `seshat mcp`, an optional
    stable MCP v1 stdio adapter exposing six read-only governance tools over
    existing services; hard stops enforced in the transport-neutral service.
  - **US4 -- readiness passports** (`7fb9639`): `seshat passport export|verify`;
    portable disclosure-safe evidence snapshots with categorical content-hash
    verification; records approvals, never grants them.
  - **US5 -- extension packs** (`61dbaf9`): `seshat pack scaffold|validate`;
    declarative local packs across six categories with fail-closed validation,
    selection-graph conflict detection, and three generic reference packs.
  - **US6 -- contributor surfaces** (`722e539`): five structured issue forms, an
    evidence-prompting PR template, five bounded starter lanes, and the
    three-document newcomer path.
  - **US7 -- agent safety benchmark** (`fa8a39d`): `seshat benchmark run|report`;
    vendor-neutral categorical scenarios (all named hard stops + six retail
    semantic failure classes), deterministic scripted reference participant,
    FR-041 run disclosure, no aggregate score/rank/leaderboard.
  - **US8 -- static readiness explorer** (`ba25a8c`): `seshat explorer build`;
    self-contained offline HTML portfolio explorer with evidence availability,
    approvals, metric lineage, explicit input-defect reporting, and fail-closed
    disclosure gating.
- **M1 -- `seshat` brand alias** (roadmap M1): `seshat` added to `[project.scripts]`
  alongside `retail`; both resolve to the same `retail.cli:main` entry point. No
  behavior change (`ca0d76c`).
- **M3 -- `seshat init-project`** (spec 107, roadmap M3, PR #217): a stdlib-only
  workspace scaffolder (`src/retail/workspace_init.py`) that creates a fresh, empty
  Retail-BI project tree (`mappings/`, `warehouse/{bronze,silver,gold}/`, `powerbi/`,
  `reports/`, `evidence/`, `README.md`, `.env.example`) for a new user -- idempotent,
  no silent overwrite of existing files.
- **M4 -- `retail status`** (spec 109, roadmap M4, PR #223): a read-only, agent-control
  status surface -- a per-table projection of `current_stage`, `evidence[]`,
  `blocking_reasons[]`, and `next_action` from committed readiness artifacts. Never
  self-grants a stage; reads only.
- **CLI dispatch-table refactor** (PR #222): `cli.py`'s `main()` if/elif chain was
  converted to a dispatch table as part of the CLI-surface decomposition; no CLI
  behavior changed (verified by the existing CLI test suite).

### Docs
- **M2 -- user-facing install docs** (roadmap M2, `6138540`): `docs/install/user-install.md`
  documents the install path and the optional extras (`db`, `mssql`, `mysql`,
  `snowflake`, `files`, `livetest`) without claiming the package is published.
- **M6 -- source-onboarding packaging guide** (spec 110, roadmap M6, docs-only, Option
  B, PR #218): `docs/user/source-onboarding.md`, a user-facing walkthrough over the
  already-shipped source-profiling surface (`retail.profile` / `retail.file_profile`).
  No new CLI verb.
- **M7 -- mapping-review packaging guide** (spec 111, roadmap M7, docs-only, Option B,
  PR #219): a walkthrough over the shipped mapping-governance gate. No new CLI verb.
- **M9 -- evidence-pack packaging guide** (spec 112, roadmap M9, docs-only, Option B,
  PR #220): `docs/user/evidence-pack.md`, a walkthrough over the shipped
  `evidence-pack-generator` (F028) and `approval-evidence-pack` (F035) skills, and
  where a pack lands in the M3 workspace `evidence/` directory. No new CLI verb.
- **M10 -- BI-delivery packaging guide** (spec 113, roadmap M10, docs-only, Option B,
  PR #221): `docs/user/bi-delivery.md`, a delivery-flow walkthrough over the shipped
  dashboard-design skills and PBIR authoring adapters; documents that publish/execution
  stays gated on F016 (hard rule #6). No new CLI verb.
- **M11 -- release & distribution maturity** (this change, spec 108, roadmap M11): this
  file, `docs/operations/versioning-policy.md`, and `scripts/install_smoke_test.py` +
  a new CI `smoke` job.

## [0.1.0] -- shipped foundation (summary, merged across 2026-06 through 2026-07-07)

Everything below has merged to `main` under the on-disk version `0.1.0`. Grouped by
the roadmap's own tiers; see `docs/roadmap/roadmap.md` for the authoritative
per-feature ledger with commit references, and `docs/roadmap/shipped-ideas.yaml` for
the idea-bank sequence's ledger.

### Added -- the original readiness-spine sequence (F005-F015, incl. F011A)
The full seven-stage readiness spine (Source -> Mapping -> Silver -> Gold -> Semantic
Model -> Dashboard -> Publish Ready) and its supporting features shipped as the
original build sequence: the Table Onboarding Wizard (F006), the Business Meaning
Registry + Arabic Retail Dictionary (F007), Grain Confidence + Mapping Diff Reviewer
(F008), the Metric Contract Store + Retail KPI Packs (F009), Semantic Model Readiness
checks (F010), the Power BI Dashboard Design skill (F011) and its Visual Foundation
(F011A), the Data Quality Control Room (F012), the BI Handoff Pack (F013), the Source
Drift Detector (F014), and the Reconciliation Ledger (F015). **F016 (the Power BI
execution adapter) remains the only original feature intentionally NOT built** --
deliberately last, execution-only, and gated on semantic-model readiness (hard rule
#6).

### Added -- the static `retail check` gate
The static governance gate grew from its original rule set to **67 registered rules**
(67 manifest entries in `docs/rules/rules-manifest.json`, live-verified) through the
idea-bank execution sequence and subsequent waves (A1, B1, A3, B3, PP1, SC1, DF1, SC2,
SL1, AL1, DL1-DL6, CT1, DR1, AD1, AQ1, SF1, CB1, and others -- see
`docs/roadmap/shipped-ideas.yaml` for the full per-rule ledger with PR references).
Each rule addition is additive (see `docs/operations/versioning-policy.md`'s MINOR
classification for a new rule).

### Added -- the Companion Modules & Adapters tier (F024-F039, partly shipped)
Six companion Product Modules shipped as docs-first agent skills under
`.claude/skills/` (per hard rule #8 -- a skill is a doc, not runtime Python): the PR
Readiness Reviewer (F025), Readiness Viewer (F026), Approval Console (F027), Evidence
Pack Generator (F028), the dbt Transformation Adapter (F029), and the Dagster
Orchestration Adapter (F030). The Approval Evidence Pack (F035), Cross-Table Lineage
(F036), Consumer-Facing Data Dictionary (F037), and Dashboard Accessibility / RTL
Readiness checklist (F039) shipped later as further docs/skill/template modules. The
Visual Implementation MVP (F034) shipped its authoring slice (trace template +
Dashboard Ready evidence item + review workflow); the built Power BI page itself
remains, by design, a human Desktop action. F024, F031, F032, and F033 remain
spec-only (no consumer yet for the maintenance-automation trio; see
`docs/roadmap/roadmap.md` Tier 5 for the per-feature detail).

### Added -- live-surface / value-proxy fortification
The L4 value proxy (`retail value-check`, recomputes metric values live and compares
to the approved value), the `$$` dollar-quote tokenizer fix, and the F038 Tabular
Editor BPA spike shipped as a closed autonomous-run sequence (2026-06-26).

### Docs -- post-integration stabilization
A docs-only stabilization phase (2026-06-28) summarized the system state, proved one
KPI path end-to-end on paper (Net Sales), and set Big Data scale boundaries as a
report/template (no Spark/Fabric/Databricks/Snowflake/BigQuery adoption).

### Out of scope (by design, unchanged since 0.1.0)
Actually publishing to PyPI, automated release/tag-cutting, the Power BI execution
adapter (F016), Fabric deployment, ML/forecasting, a universal ERP connector, and
fully automated mapping approval remain out of scope. See
`docs/roadmap/roadmap.md` "What is intentionally out of scope."

## See also

- `docs/operations/versioning-policy.md` -- the bump-rule scheme this changelog's
  version headers follow.
- `docs/roadmap/roadmap.md` -- the authoritative delivered ledger (F-numbered rows +
  commit refs).
- `docs/roadmap/shipped-ideas.yaml` -- the structured idea-bank ship ledger.
- `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md` -- the forward-looking
  M-milestone roadmap this `[Unreleased]` section draws from.
