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

### Added
- `seshat pbir-validate-bindings` -- offline, read-only PBIR binding-resolution
  validator: resolves every bound field reference in a report's definition JSON
  (queryState projections, filters, sorts; `From`-alias aware) against the
  semantic model's TMDL, blocking on unknown entities and missing fields (the
  PII-masked-rename class that otherwise ships as Desktop error cards) and
  warning on projection-kind mismatches (the #456 detection side). Fail-closed
  on empty/corrupt inputs; needs no blueprint or binding map, so it covers
  Desktop-owned reports. Grants no approval. (#454)
- `seshat scaffold-design` materializes the Stage-6/7 design + handoff templates
  (dashboard-page-blueprint, visual-spec, report-composition, the 16x9 grid, the
  handoff pack + review checklist) into a workspace, so package-only (pipx /
  marketplace) users reaching Dashboard/Publish Ready have templates to copy.
  Non-destructive; wheel-data-first with a dev-checkout fallback. (#440, #441)

### Changed
- `seshat profile --format json` no longer prints the human progress banner to
  stderr, so a merged-stream pipe (`seshat profile ... --format json 2>&1 | jq`)
  receives pure JSON. The banner is retained in the default (text) output mode;
  DB-boundary errors stay on stderr in both modes. (#436)
- `seshat generate` now accepts an inline aggregation-call denominator
  (e.g. `DIVIDE(SUM(...), DISTINCTCOUNT(...))`) in a `kind: ratio` contract, verified
  through the same L3 shape recognition the `kind: base` path uses, making Average
  Transaction Value and similar ratios machine-generatable inside the
  generate->verify guarantee. Genuinely unrecognized denominators still escalate.
  (#432)

### Fixed
- S4b no longer false-flags a schema-qualified `ALTER TABLE <schema>.<t> ALTER COLUMN
  ... SET NOT NULL` inside a `BEGIN/COMMIT` block as "target schema undetermined". The
  inner `ALTER` keyword of the `ALTER COLUMN` sub-clause was re-evaluated as a
  top-level DDL verb; S4b now only evaluates a DDL verb that starts a statement. (#442)
- `seshat check` no longer crashes with `FileNotFoundError` when a git-tracked file
  is deleted from disk but the deletion is not yet staged; content-scanning rules
  (G3, S-family, B1, G6, R1, TMDL) skip the absent path gracefully, the
  presence-required governance-manifest rules (SC1/SC2, A1/A3, DF1, DR1) fail loud,
  and file-presence rules (AL1/AL2/HR11) still flag a deleted required artifact. (#430)
- `seshat dbt doctor` no longer reports `SESHAT_DBT_PORT`, `SESHAT_DBT_SCHEMA`, and
  `SESHAT_DBT_SSLMODE` as missing required keys; these carry documented
  `env_var(NAME, DEFAULT)` defaults in `profiles.example.yml` and are optional. Only
  the four keys with no default (host/user/password/dbname) are flagged when absent.
  A present-but-empty override (`SESHAT_DBT_SCHEMA=`) is still rejected. (#437)
- `seshat dbt scaffold` fails closed when a `gold_star` dimension attribute, fact
  measure, or degenerate dimension references a column marked `decision: drop` in
  the source map, naming the drop conflict instead of silently materializing (or
  emitting a generic "unresolved") — a dropped column can never appear in a
  generated model or its `_models.yml` contract, in any layout. (#434)
- `seshat dbt scaffold` refuses to write a `.sql` model whose dbt model name (file
  basename) already exists at a different path under `dbt/models/`, instead of
  silently producing a duplicate that breaks `dbt plan` with a
  `DBT_ARTIFACT_INTEGRITY` "two models with the name" error. (#431)
- The six Stage-6/7 design + handoff templates now ship in the wheel
  (`force-include` + sdist) and the marketplace bundle (allowlist), instead of
  existing only in the development tree. (#440, #441)

### Docs
- `bi-sql-knowledge`: added anti-pattern card SQL-AP-061 warning that matching a
  non-ASCII/RTL literal directly on a shell command line silently mismatches (no
  error); use an ASCII code column, an `E'\uXXXX'` escape, or `psql -f` a UTF-8 file.
  (#438)
- `seshat-bi` skill: added a "Resetting / re-running a project" section documenting
  the interim manual reset file-set and the stage-deletions-before-`seshat check`
  workaround (until a native `seshat reset` verb ships). (#439)

## [0.6.1] -- 2026-07-22

### Fixed

- Release audit false positive that blocked the v0.6.0 PyPI publish: a
  fabricated spoof example (`abc://u:s3cret@x`) in the `_postgres_target_label`
  docstring matched the release inspector's credential-bearing-URL pattern. The
  example is rephrased in prose (docstring-only, behavior-neutral); the scanner
  regex is left strict. v0.6.0's tag is frozen by the `v*` immutability ruleset,
  so the fix ships as v0.6.1 (#426).

## [0.6.0] -- 2026-07-22

### Added

- `seshat profile` CLI verb: runs the mechanical Stage-1 profiler over a
  read-only connection and emits the numbers the blank `source-profile.md`
  asks for (row/column count, per-column `'' OR NULL` missingness, distinct
  cardinality, candidate-PK uniqueness proof) as markdown to paste or JSON.
  Closes the gap where `scaffold-source` pointed at the internal
  `seshat.profile.profile()`, unreachable on a pipx install (#400).

### Changed

- `seshat dbt doctor` now prints the exact remediation command
  (`pipx inject seshat-bi --force "<pkg>==<ver>"`, or the pip equivalent) when a
  dbt-core/dbt-postgres version is unsupported or missing, instead of only
  naming the expected version (#407).

### Fixed

- Windows cp1252 crash on UTF-8 ingest: the Dagster run and gate-command
  subprocess readers now decode child output as UTF-8 (not the platform
  default), so non-Latin-1 governed values (e.g. Arabic `billing_type`) no
  longer raise `UnicodeDecodeError` mid-run (#404).

## [0.5.3] -- 2026-07-21

### Added

- Top-level `--version` prints `<prog> <version>` from installed package
  metadata (with a `0+unknown` fallback for an uninstalled source tree), and
  CLI identity now follows the invoked command name (`seshat --help` no longer
  prints `usage: retail ...`) (#378).

### Fixed

- `check` and `doctor` emit a clean stderr error and exit 1 on a broken or
  unlaunchable git (missing binary, corrupt repo), instead of a raw traceback
  (#394).
- `redaction_core` now scrubs three more DSN shapes at the shared decomposition
  -- a mixed-case hostname, URI query-param credentials, and libpq keyword
  conninfo strings -- so every boundary redactor benefits; the repo-root probe
  behind P2 uses `git rev-parse --show-prefix` instead of a path comparison
  that a Cygwin/MSYS git could fail (#392, #393).
- `cli._redact_dsn` is reimplemented on the shared `redaction_core`, closing a
  duplicate that missed the DB name and percent-decoded credential forms; P2 no
  longer errors in a fully non-git workspace (#384, #385).
- `doctor` now honors the same KIT_SELF / foreign-repo skip that `check`
  already applies, so a client's downloaded-into workspace is not warned about
  kit-internal manifests it was never given (#377).
- `scaffold-source` output is self-consistent with its own templates: the
  written `readiness-status.yaml` next_action matches the actual
  `source_ready` stage, and all five sister artifacts declared in
  `source-map.yaml` are materialized (#374, #380).
- `demo run`'s live mode is decided by an actual reachability probe rather than
  `bool(dsn)`, and both `demo run` and `demo load` resolve the DSN from the
  same shared helper (workspace `.env` included); a live-leg connect failure is
  redacted before being reported instead of surfacing a credential-bearing
  traceback (#375, #376, #379).
- `seshat init` no longer crashes on a fresh non-git workspace missing
  `.seshat/kit-source.yaml` (now a bundled template), and `check` no longer
  raises or falsely reports on-disk files as missing in a non-git workspace
  (#370, #371, #372).

### Docs

- Rebrand user-facing `retail check` references to `seshat check` (#390).
- Add a Claude/Codex marketplace client quickstart and a public-catalog
  submission runbook (#373, #382).

## [0.5.2] -- 2026-07-20

### Added

- `seshat dashboard` writes a self-contained, static HTML readiness view of the
  workspace -- a Home page with portfolio KPIs and one per-table card showing the
  seven-stage readiness track -- from the recomputed `readiness-status.yaml`, with
  no server, no external assets, and every value HTML-escaped. The theme CSS is
  inlined into the page, and the verb can write-and-auto-open the file (#358,
  closing the deferred dashboard scope #359 #360 #361). The renderer fails safe on
  a `None` stage or missing source path rather than raising.

### Fixed

- Close three credential-leak paths in the Dagster-adapter and portfolio
  enumeration redaction: a reformatted, schemeless driver error that named only
  the host/user components of a `DATABASE_URL`-shaped secret could survive the
  whole-value replace. URI decomposition now scrubs each component (#362, #364).
- Redact the Dagster adapter's secret environment values from an explicit
  POSITIVE key set (`ANALYTICS_DB_*` credentials + `DATABASE_URL`) instead of a
  prefix scan, so a fixed-vocabulary config word (e.g. `ENGINE=postgres`) is no
  longer over-redacted, while genuine credentials stay scrubbed (#357, #363).
- `seshat-init` workspace writers are hardened and the generated `init-project`
  layout is aligned, closing a set of workspace-scaffold issues (#349 #350 #351
  #352, PR #356).
- Close the time-of-check-to-time-of-use race in `scaffold-source`'s
  `_write_if_absent` per-file write, the follow-up deferred from v0.5.1 (#345,
  PR #355).
- The Dagster command family now loads the workspace `.env` for engine selection
  and connection resolution, matching how `validate` / `value-check` already
  read it (#348, PR #354).

### Changed

- Extract one shared URI-redaction core (`seshat/redaction_core.py`) imported by
  the dbt, Dagster-adapter, and portfolio redactors, replacing three in-place
  copies of the URI decomposition and the fragment-replace helper. Each caller
  keeps its own replacement token; pure refactor, no behavior change (#365,
  PR #366).

## [0.5.1] -- 2026-07-19

### Added

- `seshat scaffold-source <table>` writes the three Stage-1 blank templates
  (`source-profile.md`, `readiness-status.yaml`, `source-map.yaml`) into
  `mappings/<table>/` from bundled package data, so a pip-only workspace can
  produce the first Source-Ready artifact without the development repository
  (#339). The three templates now ship as wheel package data and are required
  by the release-artifact gate; `seshat next`'s fresh-workspace guidance points
  at the new verb. The table name is validated for Windows reserved device
  names, invalid filename characters, and trailing/leading dots or spaces
  (which Win32 trims), and the write refuses a symlinked or non-file output
  path (a symlinked `mappings/` escaping `--repo`, or a directory/FIFO sitting
  where a Stage-1 file belongs), with an `OSError` backstop for the 260-char
  path limit -- so an unsafe name or hostile filesystem state yields the
  documented refusal rather than a traceback or a misleading success. The
  materialized `readiness-status.yaml` carries a truthful initial
  `current_stage: source_ready` (not the `<stage_key>` placeholder), so a
  committed scaffold passes the RS1 governance gate as an honest unstarted
  Source-Ready journey with no fabricated evidence or approvals; its `table`
  and `source_id` identity fields are set to the requested table (so
  `seshat next` attributes the scope to it, not the literal placeholder); and
  the `source-map.yaml` `profiled_from` provenance is retargeted at the
  materialized `mappings/<table>/source-profile.md`; and its `next_action` is a
  concrete Source-Ready step (not the template's Mapping-stage example, which
  `seshat status` would otherwise project as the controlling action). The table
  name rejects ASCII control characters (invalid on Windows; would corrupt the
  line-oriented CLI output), and the write refuses any symlinked destination
  component -- including an in-repo alias (`mappings/foo` -> `mappings/bar`)
  that would pollute the wrong table scope. `scaffold-source --repo <dir>` also
  prints a `seshat next --repo <dir>` follow-up so the guidance targets the
  scaffolded workspace, not the caller's cwd. (A residual TOCTOU race in the
  per-file write is tracked as a scoped follow-up, #345.)

### Fixed
- **`dbt plan` no longer swallows the underlying dbt parse error** (#341): a
  failed non-database PARSE runs under `--log-format json`, so the Compilation
  Error lands as JSON log events on stdout while stderr is empty --
  `_successful` interpolated the empty stderr and emitted a bare
  `DBT_ARTIFACT_INTEGRITY:` with nothing after the colon. It now surfaces the
  most informative available text (stderr, else error-level JSON log `msg`
  events from stdout, else raw stdout, else an explicit log-location marker),
  so the real parse error reaches the operator.
- **`validate` / `drift` / `value-check` now honor the workspace `.env`** (#340):
  the live commands read `os.environ` only -- for BOTH engine selection
  (`ANALYTICS_DB_ENGINE`) and connection resolution (`ANALYTICS_DB_*`) -- so a
  user who put those in the gitignored `.env`, exactly as the error text,
  `.env.example`, and README all instruct, got "no database connection
  configured" or silently the wrong engine. A new
  `seshat.connection_env.applied_dotenv(root)` context manager applies `.env`
  into `os.environ` for the whole command body (so every read -- engine, driver,
  config -- sees it), with real environment variables winning over `.env`, and
  restores `os.environ` exactly on exit (including on error). It reuses the
  governed dependency-free `.env` parser from `dbt.redaction` -- no
  `python-dotenv` dependency. A malformed `.env` -- or a syntactically valid but
  invalid connection VALUE (an unknown `ANALYTICS_DB_ENGINE`, an unparseable
  `ANALYTICS_DB_PORT`) -- now fails clean (exit 1, no traceback) at each command
  boundary. `value-check` reads `.env` from `--repo` (the evaluated workspace),
  not the caller's cwd. (Scoped follow-ups: `drift`'s postgres path is still
  gated on `--dsn` upstream; and the driver hint prints
  `retail[db]` where the installable extra is `seshat-bi[db]`.)

## [0.5.0] -- 2026-07-19

### Added
- **`kpi-contract-builder` verb** (spec 130 follow-through, PR #321): drives the
  shipped `kpi_contracts` engine -- assess answerability, list the decisions to
  approve, preview with per-field provenance, then draft/finalize; never
  self-grants approval. Registered in the kit source and capability inventory.
- **`seshat mapping-mirror` verb** (issue #326, PR #333): guarantees
  `mappings/<table>/unresolved-questions.md` exists -- a CLEARED stub is derived
  only from the COMMITTED readiness status (named-human C4-shaped `mapping_ready`
  approval, non-empty evidence, no blockers); anything less yields an OPEN stub.
  Never overwrites the human-authored ledger. Wired into the `source-mapping`
  skill's gate step, closing the gap where a table could pass the whole readiness
  spine and only then hard-fail the dbt gate (`DBT_MAPPING_MIRROR_MISSING`).
- **`seshat dbt init` and `seshat dagster init` verbs** (issue #325, PR #335):
  materialize the generic governed dbt working set and the table-neutral Dagster
  orchestration project from wheel-bundled templates, so any workspace gains full
  dbt/Dagster capability without the development repository (portable operating
  contract). Only table-neutral content ships (constitution VII); `selectors.yml`
  is generated table-neutral; both inits are per-file non-destructive and ensure
  the secret/run-output ignore baseline.

### Changed
- **dbt parity evidence is table-agnostic and exact** (issue #324/PR #330 +
  issue #331/PR #332): the rss-hardcoded assertion contracts were replaced by
  class-driven validation, and exact fact-subject coverage was restored
  generically -- the approved source map's `gold_star.fact` now REQUIRES
  `business_key` (string or ordered list for composite grains) and
  `additive_money_measures` (explicit `[]` for factless facts) tags, bound into
  the digest-accepted plan (execution-plan `schema_version` is now 2; v1 plans
  fail closed with a re-plan message). Evidence verifies every declared money
  measure reconciles exactly once, the business-key count references exactly the
  declared grain key, and the built fact model IS the approved relation. A
  dbt-path mapping without the new tags now fails closed with
  `DBT_FACT_SEMANTICS_MISSING` until the tags are declared and re-approved.
- **The Dagster GO signal requires a committed gate artifact** (issue #334,
  PR #336): `read_gate_state` reports `UNCOMMITTED` when
  `unresolved-questions.md` is untracked or differs from HEAD (or the workspace
  is not a git repository), so `silver_permitted` fails closed on any clearance
  that never entered audit history; `seshat dagster doctor` names the commit
  remedy. New shared `seshat.gitstate` hardened read-only git probes back both
  this gate and `mapping-mirror`.

### Fixed
- **Windows Unicode crash and multi-table dbt validate** (PR #327): CLI output
  is forced UTF-8 on Windows consoles, and `seshat dbt validate` handles more
  than one governed table.

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
