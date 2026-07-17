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

## [0.4.1] -- 2026-07-17

### Added
- **Activated the `dagster-dbt` engine seam** (spec 135, PR #307): `silver_tables` /
  `gold_tables` gain a SELECTABLE build engine -- when a table's committed
  `mappings/<table>/build-engine.yaml` names `dbt` for a layer, that layer's build
  routes through the governed `seshat.dbt` control layer (plan -> self-accepted
  accept-plan digest -> isolated shadow-schema build) instead of the default
  `warehouse/migrations/*.sql` path, with identical gate semantics (same
  `seshat check` exit codes, still downstream of the `source_map` HUMAN SEAM,
  still fail-closed). The unused `dagster-dbt` library pin was dropped from
  `orchestration/dagster/` (FR-011 owner decision, Ahmed Shaaban, 2026-07-17): no
  released `dagster-dbt` accepts `dbt-core` 1.12, and the engine's execution path
  never imports it. The dbt engine remains a governed rehearsal into isolated
  shadow schemas (`warehouse_updated: false`); migrations stay the default, the
  parity oracle, and the rollback path until a named human retires them. Live dbt
  drive stays `[PENDING LIVE PROFILE]` (`docs/operations/dbt-activation-status.yaml`).
- **Governed dependency co-resolution and freshness gate** (spec 136, PR #308):
  a new `dep-integrity` CI workflow resolves every declared install environment
  and cross-product listed in `dependency-environments.yaml` in an ephemeral venv
  (`scripts/dep_coresolve.py --check`), catching on the day it lands the exact
  class of conflict that let the spec-133/134 `dagster-dbt` vs. `dbt-core` pin
  mismatch sit unseen on `main`. A weekly advisory freshness reporter proposes
  latest-stable bumps of governed pins with a solve-proof but changes no pin and
  opens no PR. The previously-unwatched `/orchestration/dagster` pip environment
  is now covered by Dependabot.

### Changed
- **GitHub Sponsors enabled** (PRs #309, #313): `.github/FUNDING.yml` points at
  the verified `Kemetra` Sponsors profile, and the README carries a prominent
  sponsor call-to-action.
- **CI action pins bumped** (Dependabot, PRs #310, #311): `.github/workflows/dagster-smoke.yml`
  moves to `actions/checkout@7` and `actions/setup-python@6`.

### Fixed
- **Stale "unmerged" wording in the dependency co-resolution gate's
  historical-incident note** (`dependency-environments.yaml`,
  `.github/workflows/dep-integrity.yml`, `docs/tools/dep-integrity.md`): the note
  described spec 135 / PR #307 as still unmerged and the
  `root-dbt-plus-orchestration` cross-product as still failing to resolve; both
  merged and the cross-product resolves cleanly, so the note is reworded to the
  past tense without losing the historical record of the incident it proves the
  gate catches.
- **Stale `dagster-dbt` reference in the Dependabot orchestration-coverage
  comment** (`.github/dependabot.yml`): the comment describing the
  `/orchestration/dagster` manifest's named PyPI distributions still listed
  `dagster-dbt`, which spec 135 had already removed from that project's
  `pyproject.toml`; corrected to the current dependency set.
- **Dependabot config referenced two GitHub labels (`dependencies`, `ci`) that do
  not exist in this repository**: set `labels: []` on each `.github/dependabot.yml`
  entry rather than leaving a dangling reference to missing labels. Simply
  deleting the `labels:` key (the initial fix) was wrong -- per GitHub's
  Dependabot config reference, an unset `labels` key falls back to the default
  `dependencies` label and Dependabot creates it if absent, which is the exact
  outcome this change is meant to avoid (caught by automated PR review on
  PR #314). No label was created.

## [0.4.0] -- 2026-07-17

### Added
- **`dagster-workflows` public skill and Dagster surface parity** (PR #303):
  the governed Dagster workflow (doctor -> run -> evidence, hard boundaries,
  exit meanings) ships as a dedicated shared skill in BOTH the Claude and
  Codex bundles; the three `dagster-*` commands and the `seshat-bi` router
  route to it, and the `dagster-orchestration-adapter` capability entry now
  carries dbt-standard references (`runtime_project`, `public_skill`,
  `evidence_schema`, `verified_by`).
- **Dagster orchestration MVP** (spec 134, activates spec 024 / F030): a real
  `orchestration/dagster/` runtime project (`tower_bi_orchestration`,
  `dagster==1.13.14` + `dagster-dbt==0.29.14` pinned together, own venv) running
  the full 11-asset medallion graph behind every gate -- fail-closed STOP edges,
  read-only HUMAN-SEAM approval reads, a publish wall that only TRIGGERS F016 and
  fails closed while F016 is absent, and one daily schedule + one raw-landing
  sensor both shipped STOPPED. New `seshat dagster doctor|run|evidence` lazy CLI
  family (exit codes 0..4), `src/seshat/dagster_adapter/` control layer (gate
  readers, shell-free closed-argv runner, redaction, schema-validated derived
  run-evidence rendered per `templates/dagster-run-evidence.md`),
  `schemas/dagster-run-evidence.schema.json`, three Claude plugin commands
  (`dagster-doctor`, `dagster-run`, `dagster-evidence`), and the
  `.github/workflows/dagster-smoke.yml` definitions-load CI gate (no DB, no
  secrets). The `dagster-dbt` engine seam activates after spec 133 merges.
- **Governed dbt transformation MVP** (spec `133`): exact optional
  `dbt-core==1.12.0` + `dbt-postgres==1.10.2` runtime, a tracked eight-model
  `retail_store_sales` shadow graph with 24 selected tests, Mapping Ready and
  source-map citation validation, immutable accepted plans, invocation locks,
  redacted subprocess handling, normalized parity evidence, `seshat dbt`
  doctor/validate/plan/build/test/inspect-run commands, and the shared
  `dbt-workflows` Claude/Codex skill. Static parse/list and artifact compatibility
  are locally verified; live compile/build/test/parity and named-owner compatibility
  attestation remain `[PENDING LIVE PROFILE]`. Migrations remain the default.
- **Canonical public command surface** (`distribution/public-command-surface.yaml`):
  the single authority for what the generated agent bundles advertise, reconciled
  by the new `tests/contract/test_public_command_surface.py` drift gates and read
  by `scripts/external_agent_acceptance.py` in place of a hardcoded skill count.
- **Eight new Claude Code plugin commands** (`help`, `doctor`, `status`,
  `powerbi-design`, `powerbi-review`, `powerbi-theme`, `powerbi-format`,
  `powerbi-adopt`) and the shared `powerbi-workflows` bundled skill (shipped to
  both the Claude and Codex bundles), all generated through the existing
  allowlist/exporter; the `seshat-bi` router now routes Power BI intents to
  `powerbi-workflows`.

### Changed
- **Normalized command names**: core readiness commands use the bare verb name
  (`/seshat-bi:init`, `:check`, `:status`, `:next`, `:doctor`, `:review`,
  `:help`) since Claude Code already namespaces plugin commands; the four
  v0.2.0-accepted `seshat-*` names remain as deprecated aliases for one release
  cycle, each carrying its canonical body verbatim (contract-tested).

### Docs
- **v0.3.1 public acceptance record** (`docs/releases/v0.3.1-public-acceptance.md`):
  externally verified PyPI clean-install, Claude Code plugin install/behavior/
  pressure-refusal/update/uninstall (headless, with the noted profile-isolation
  gap), and -- newly beyond the v0.2.0 boundary -- Codex CLI governed behavior,
  pressure/refusal, update, and removal. Install docs and the support matrix now
  cite it.
- **Agent self-discovery route** in the bundled `seshat-bi` router: one skill
  name is enough -- the router points to `/seshat-bi:help`, `seshat --help`,
  and `seshat next --format agent` so agents never need memorized command or
  skill names.
- **Agent-driven automation surfaced**: the previously undocumented read-only
  MCP governor (`seshat mcp`, extra `seshat-bi[mcp]`) and its six tools are now
  documented in the agent install guide and routed from the bundled router,
  with the governed loop protocol (next action -> act -> re-check -> stop at
  named-human gates) stated explicitly and a contract test pinning the
  documented tool names to the server source. The `/seshat-bi:auto` command
  codifies that loop as a one-invocation prompt that always stops at the next
  named-human gate.

### Fixed
- **Bundle provenance vs squash-merge** (PRs #301, #302): every bundle-touching
  PR broke main CI after squash-merge because the committed manifests recorded
  the (squashed-away) branch commit as `source_revision`. The everyday
  export/regeneration posture now validates the manifest version claim against
  HEAD's canonical `pyproject.toml` when the recorded revision is orphaned;
  the coordinated-release audit keeps strict ancestry.
- **`capability_feeders.read_dispatch_keys` stale source path**: the feeder read
  the pre-rename `src/retail/cli/__init__.py` and silently discovered no
  `_DISPATCH` keys; it now reads `src/seshat/cli/__init__.py`, with regression
  coverage reconciling it against the independent test oracle.
- **Stale `seshat-bi==0.2.0` claims in active install docs**: the current release
  is stated as the packaged version (guarded by a contract test against
  `pyproject.toml`), while v0.2.0 remains the cited historical external
  acceptance evidence.
- **C1 finding message leaked the literal connection host** (PR #298): the
  parameterized-connection rule echoed the entire matched `*.Database(...)`
  call -- including the literal server/database values -- into its finding
  message, which downstream surfaces such as the `adopt-pbip assess` JSON
  embed verbatim. The message now names only the connector and redacts the
  arguments; the locator still points at the exact source position.

## [0.3.1] -- 2026-07-14

### Fixed
- **`prepare-coordinated-release` commit-subject P2 mismatch**: the workflow's
  auto-generated release-branch commit used the subject `release: prepare
  v${VERSION}`, but `release` is not a registered P2 commit type and the
  subject carries no `[bot]`-style exemption prefix, so CI's `retail check`
  always failed on the workflow's own commit. Changed the template to `chore:
  prepare v${VERSION}`. Both the v0.3.0 and v0.3.1 runs needed a manual amend
  before this fix landed.
- **Release-artifact credential-scan false positives**: two docstrings
  (`seshat/pr_summary.py`'s `mask()`, `seshat/showcase/manifest.py`'s
  `find_residual_absolute_paths()`) used a literal example DSN/path shape
  (`scheme://user:pass@host/db`, `home/Users/var/etc/opt/tmp`) to document a
  known non-coverage gap and a scanner's recognized prefix list, respectively.
  Both incidentally matched `scripts/inspect_release_artifacts.py`'s
  credential-bearing-URL and macOS-user-path content patterns, which blocked
  the v0.3.0 release-candidate build. Reworded both to describe the same shape
  in prose without forming the literal pattern; verified zero matches against
  the scanner's actual regexes and a clean `inspect_release_artifacts.py`
  `pass` on a locally rebuilt wheel/sdist. No behavior change to either
  function -- docstring-only.

## [0.3.0] -- 2026-07-14

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
