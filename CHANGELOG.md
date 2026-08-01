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
- **PBIP X-Ray -- `seshat xray` and `seshat model-diff`** (#549, #550, #551).
  Two advisory, read-only CLI verbs over a committed PBIP project. `xray` builds
  a model graph by resolving measure/column references across parsed TMDL, reads
  PBIR visual bindings, and reports findings X0-X4; `model-diff` classifies TMDL
  changes as semantic / cosmetic / additive / removed. Supporting work extended
  the TMDL parser with relationship endpoints, cardinality, and measure/column
  metadata. Ships with a `pbip-xray` skill front door, a capability-inventory
  entry, and compass routing. Advisory only: neither verb grants an approval,
  moves a readiness stage, or emits a confidence score.
- **The ten compass verbs now ship in the Claude and Codex bundles** (spec 138
  US2+US3, #547, #548). The packaged plugin bundles previously carried 11 skills
  and none of the ten compass verbs the kit's own orientation text names; they
  now carry 21, behind a portability gate, with the inventory as the authored
  source of what ships. The plugin also declares the read-only governor (US1),
  backed by the shipped `src/seshat/allowlist_derivation.py`. Spec 138 remains
  **partially implemented** -- US2 and US3 delivered; it is not complete.
- `seshat readiness-diff` -- compare committed readiness state across two git
  revisions (#536).
- `seshat cvd-evidence` -- read-only colour-vision-deficiency simulation
  evidence for one theme (#541).
- `seshat profile` accepts a landed CSV/TSV/Excel file, not only a DB table
  (#535).
- Readiness blockers now name **who acts** on each one, from a committed
  allowlist (#538).
- Machine-written, server-confirmed live-DB provenance on readiness evidence
  (#512, spec 485 A2), replacing the interim "this carries no DB provenance"
  disclosure.
- `seshat next` surfaces the adapter checkpoint and the source-map shape (#506),
  and open approval requests via the authoritative path (#522).
- Shadow-vs-migrations column-shape drift is reported as an advisory (#501).
- Power BI theme spec sections 5/6/7, with the blueprint preview styled from
  tokens (#518).
- The agent-facing rule fix table is generated, so it cannot drift from the
  registered rules (#543); the spec status vocabulary is closed and implemented
  claims are locked (#544); acceptance transcript fixtures are bound to the
  bundle they exercised (#542).
- Expanded knowledge layers -- analyst narrative reasoning, DAX semantic
  diagnostics, PostgreSQL plan reasoning, Python validation and dataframe
  reasoning routes, governed KPI decision packets, and Big Data operational
  evidence, with standardized handoffs between layers (#496).
- An assessment of the Power BI MCP read-only family and core-only sufficiency
  (#537).
- Governed statistical evidence engine -- a locally executable Product Module
  with eight closed methods (`describe`, group comparison, proportions,
  correlation, associational regression, anomaly detection, change-point
  detection, and forecast), strict schemas, immutable derived evidence,
  categorical outcomes, deterministic pending-human review, a fail-closed local
  CSV provider, and a PostgreSQL-only read-only Gold adapter. This capability
  supersedes the former universal statistical/forecasting exclusion: knowledge
  cards still do not compute models, autonomous ML/deployment and causal claims
  remain excluded, and no result grants approval or changes readiness.
- `seshat tmdl-doc-comment-lint` -- an offline, read-only lint for **one** TMDL
  rule: a `///` documentation block must be followed by a declaration, never a
  blank line and never EOF. An unattached block makes Power BI Desktop reject the
  whole project (`InvalidLineType` / `Unexpected line type: Empty!` ->
  `DataModelLoadFailed`), and no existing check saw it -- `pbir-validate-bindings`
  emitted byte-identical output before and after the defect, and `parse_tmdl` is
  an extractor that tolerates unrecognized lines. Walks the entire
  `definition/**/*.tmdl` tree (the reported defect was in
  `definition/relationships.tmdl`, which a `tables/`-only walk misses),
  BOM-tolerant, fails closed on a missing/empty/unreadable input, grants no
  approval. Deliberately narrow and deliberately **not** named as a TMDL
  validator: it is NOT a TMDL syntax validator, and a pass does NOT mean the
  model loads in Desktop. ADR 0001's headless exclusion of the
  `TmdlSerializer`/TOM path is untouched (pure stdlib text reading), so issue
  #494's broader TMDL-validation gap remains open (partial fix for #494).

### Changed
- **HR1 `gold_placement` resolution now ERRORs on an unresolvable prefix**
  (#499, #505). Every `columns[].gold_placement` in the reference map named a
  LOGICAL dimension while `gold_star.dimensions[].name` is PHYSICAL and
  schema-qualified, so the two never matched and `_attr_silver_types` silently
  returned `{}` for every dimension. The fix resolves each placement prefix from
  the PHYSICAL **bare** dimension name -- the declared `name:` with any
  `<schema>.` prefix stripped -- and turns an unresolvable prefix into an ERROR.
  **This can newly fail a consumer repo that was passing only because the
  resolution was silently empty.** Per `docs/operations/versioning-policy.md`,
  this is the bug-fix-restores-intended-behavior row; the owner classified its
  blast radius as PATCH-class and kept this release MINOR rather than MAJOR.
  A consumer hitting it should write the bare physical name, not a
  schema-qualified one: for a dimension declared `gold.dim_product_rss`, the
  placement is `dim:dim_product_rss.item`. A schema-qualified
  `dim:gold.dim_product_rss.item` does NOT work -- the prefix is parsed up to
  the first `.`, so only `gold` would be read and the placement is rejected.
- HR1 now degrades like HR13 on an unreadable source-map instead of dropping it
  (#508, #511), and an unreadable map is reported rather than silently skipped.
- `seshat semantic-check` gained `--require-inputs`, which exits 1 when NO
  semantic input is discovered instead of reporting `[not_started]` and exiting
  0; it is wired into the CI step. The flag is on `semantic-check`, not on
  `seshat check`. The default remains exit 0, so this is additive for existing
  callers.

### Fixed
- Statistical evidence now records the exact installed versions of each
  method's numerical libraries, missing change-point dependencies produce the
  specified `unavailable` outcome, and recovery guidance names the actual
  `stats` / `stats-change` extras. The optional PostgreSQL Gold-adapter test
  also proves a read-only session and compiler-only `SELECT` statements; it
  remains `[PENDING LIVE PROFILE]` when its live-test dependencies are absent.
- Connection-string redaction now redacts by SPAN rather than by substring
  fragment, redacts quoted values whole, and keeps punctuation inside bare libpq
  conninfo values (#527, #528). Five further reviewed security findings closed --
  fail-opens, git-hardening drift, and the DSN wrapper.
- Installation guidance emits pipx commands that actually work in the documented
  lane, including one that MODIFIES an existing install (#507, #510); enabling an
  extra no longer replaces the installed Seshat build (#513); and `seshat mcp`
  shows the install hint instead of a raw traceback.
- A date dimension contributes its attributes, not just its table name (#491),
  resolved through one shared resolver (#497, #502).
- A verified live state now requires the committed run record (#493, #504).
- Power BI theme token and preview fidelity -- page/chrome colours derived into
  the dark seed, the non-text ground composited, the tokens degrade split
  honoured, transparency validated at the gate, collisions no longer
  misattributed, theme cards pruned per-property/per-entry, and malformed tokens
  rejected (#520, #521, #523, #524, #525, #526).
- Gate hardening: `narrative-check` validates the frozen v1 schema it claims to
  enforce (#474), the `pbi-mcp` preflight binds to its declared target and
  transport shape (#477), the PBIR binding validator names what it cannot
  classify (#475), and measure sync compares measure names case-insensitively
  (#476).
- The KIT_SELF tier is scoped to the kit, and the approval gate states what it
  requires (#490).
- Malformed `.pbir` manifests are guarded, and hierarchies keep the declared
  table spelling (#551).
- The spec-136 A3 hole is closed so github-actions bot PRs can pass P2, and the
  setup-python supply-chain assertion is repinned to the v7.0.0 digest (#531).

### Docs
- **Spec 137 -- the Finance GL genericity proof** (#545, #546). A deterministic
  Finance GL fixture generator, 9 defect variants, 6 judgment scenarios, and a
  full set of mapping artifacts stopped at the gate, plus the genericity ledger
  and defect matrix. This is **evidence, not shipped runtime**: it landed under
  `mappings/`, `docs/worked-examples/`, and `benchmark/scenarios/`, with no
  change to `src/seshat/`. It exists to show the engine is not retail-specific.
- The `retail_store_sales` worked example is completed through the three-way
  gate, with a narrative brief template and the owner decision package (#514,
  #516, #519).
- The four-track engine program design (#540) and an enterprise KPI knowledge
  reference (#530).
- The v0.7.1 acceptance record, with the catalog runbook refreshed to 0.7.1
  (#483).
- The test suite is hermetic against global git config (#539).

### Dependencies
- `dagster` 1.13.14 -> 1.13.15 in `/orchestration/dagster`, with its pin mirrors
  co-updated (#532); `actions/setup-python` 6.3.0 -> 7.0.0 (#531). Dependabot no
  longer proposes MCP major ceiling widenings (#534).

## [0.7.1] -- 2026-07-24

### Fixed
- Release inspector false positive that blocked the v0.7.0 PyPI publish: the
  macOS-user-path detection pattern in `seshat/pbi_mcp/scan.py` spelled the
  literal byte shape (`/Users/...`) that `scripts/inspect_release_artifacts.py`
  scans shipped source for. `scan.py` is itself the secret scanner, so the
  detector tripped on its own detection regex; no real path leaked (the matched
  text was `/Users/[^/`, regex syntax, and a repo-wide scan found one hit). The
  pattern is now assembled from fragments so the literal never appears in
  shipped bytes -- the compiled regex is identical and every detection case
  still fires. The inspector regex is left strict; no release guard was
  weakened. v0.7.0's tag is frozen by the `v*` immutability ruleset, so the fix
  ships as v0.7.1 (#478).

## [0.7.0] -- 2026-07-24

### Added
- `seshat narrative-check` -- offline, read-only checker for the analyst
  narrative brief (`mappings/<table>/narrative-brief.md`) against the frozen
  `seshat.narrative-brief/v1` schema: grounded-only MEASURE cites (each must be a
  declared approved contract), fresh contract revision shas, unique question ids,
  valid framing + stage literals, story-order coverage + stage-match + non-empty
  overview, the overview-headline comparison rule, the guardrail-basis-present
  rule, and [GAP]-not-framed-as-a-question. Fails closed on a
  missing/unreadable/malformed brief; emits named categorical findings; grants no
  approval. Out of v1 scope: dimension-cite grounding (the frozen dotted-dimension
  grammar does not match the bare-column profile format; a follow-up owner
  reconciliation). Phase C of spec 021; delivers User Story 3. (#452)
- `seshat narrative-check --binding-map` -- Phase B, opt-in design-stage mode:
  checks the THREE-way binding map (visual -> contract -> decision-question) at
  `mappings/<table>/design/visual-contract-binding-map.md` against the new
  `seshat.binding-map/v1` schema. Finds orphan visuals in EITHER direction (a
  visual whose `contract` is missing or not a declared approved contract, or whose
  `decision_questions` is empty or undeclared -- FR-005), brief decision-questions
  that no visual answers (`unanswered_question`, FR-005), pages that serve no owner
  decision, and bare-total headline visuals (a `headline: true` KPI-card visual
  answering no `overview` question -- FR-006, transitive to the brief's
  overview-comparison rule). `decision_questions` is list-valued (a visual may
  answer more than one decision). Fails closed on a missing/malformed map or an
  absent referenced brief; opt-in so brief-stage (US1) callers are not broken.
  Grants no approval. Delivers spec 021 User Story 2 (T010). (#452)
- `bi-analyst-knowledge` skill pack (spec 021, Phase A + D) -- the analyst
  judgment layer between semantic-model readiness and dashboard layout: a
  derivation route (approved contracts + committed profile -> ranked
  decision-questions), eight domain-neutral framing cards, a story-order rule,
  and two worked examples, plus the frozen narrative-brief schema the checker
  consumes. Docs-only; propagated to the distribution/integration bundles and
  the public-knowledge allowlist alongside the other knowledge packs. The
  Phase-B design-gate arming shipped separately (see Changed, below). (#452)
- `seshat pbi-mcp doctor|generate-config|preflight` -- the read-only Power BI
  MCP doctor family (#450 slices 2-4, the F016 slot; same Option-B narrow
  adapter-family shape as `seshat dagster doctor`). `doctor` detects the local
  environment without network (Node runtime, vendored modeling MCP, `.mcp.json`
  mode, PBIP on disk, `semantic_model_ready` state) and implements the issue's
  section-7 recommendation matrix as a pure decision function -- a not-passed
  gate is a blocked recommendation naming `semantic_model_ready`; the advisory
  record `.seshat/powerbi-mcp-recommendation.yaml` is written only under
  `--write-advisory` and is write-once. `generate-config` emits placeholder-only
  read-only `.mcp.json` templates (local stdio / remote HTTP) plus the generated
  `docs/generated/powerbi-mcp-setup.md`, every byte passing a C1/C2-style secret
  scan before emission, refusing overwrites. `preflight` does capability
  discovery + target-allowlist validation through a transport Protocol whose
  real runtime is deliberately absent (graceful "runtime not present" skip),
  hard-refuses `--skipconfirmation`/write-mode configs, blocks on unsupported
  protocol versions (unknown is never compatible), and records
  `.seshat/powerbi-mcp-preflight.json` -- the F016 row's smoke-test evidence
  shape in the adapter-compatibility matrix. New `pbi-mcp-doctor` companion
  skill in both public bundles. No mutation path exists; F016 stays parked
  pending the owner-ratified ADR (slice 5). (#450)
- `seshat reset <table>` -- tear ONE table back to a fresh Source stage by
  removing its complete derived file-set: `mappings/<table>/` (incl.
  `dbt-evidence/`), the exact-token silver/gold DDL migrations (full
  `_create_(silver|gold)_<table>` token match with a prefix-collision guard --
  `orders` never sweeps `orders_archive`), generated `warehouse/gold`/
  `warehouse/schema` outputs, the three nested `dbt/models/*/<table>/` folders,
  only this table's rows in the shared dbt files (surgical, byte-faithful edit
  of `dbt/selectors.yml` + `dbt/models/sources/_sources.yml`), and the
  table-scoped dagster run evidence under `.seshat/dagster/runs/` (never the
  materialized `orchestration/dagster/` project). Preserves the bronze landing
  and every other table; never touches a live database. The whole plan is
  validated (containment, no symlink escapes) BEFORE anything is removed; the
  deletions are staged (`git add -A -- <paths>`) so `seshat check` runs clean
  afterwards (the #430 workaround made native); post-reset verification
  inspects the actual artifacts and `seshat next --table` reports a fresh
  Source stage. `--dry-run` prints the exact plan; interactive confirm with
  `--yes` for automation (fail-closed refusal on non-interactive stdin);
  `--format json` emits the stable reset document. The consolidated skill's
  "Resetting / re-running a project" section now points at the verb first,
  keeping the manual set as fallback. (#433)
- `seshat adopt-pbip measure-sync` -- governed, file-only upsert of APPROVED
  metric-contract measures into one table of an already-adopted PBIP semantic
  model. Serves only models recorded by an accepted adoption manifest
  (`assess` -> `scaffold` first); each measure passes the owner-approval
  inventory gate and re-verifies through the generate->verify chain (L3 +
  D1-D11) before any write; the upsert is idempotent (insert/update/skip),
  atomic (one bad contract refuses the whole run), and proves the
  partition/M-source region byte-identical after every write. `--dry-run`
  prints the plan; partition/M content is never echoed to any output. (#457)
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
- **Hardened Dagster and semantic/readiness boundaries** (2026-07-22 main review
  remediation). Semantic readiness now depends on a validated approved-contract
  inventory (new `metric_contract_inventory`): an L3 gate requires each base metric
  contract to carry a `semantic_model_ready` approval with `metric_owner` authority
  whose note names that contract, so an unnamed blanket approval no longer binds.
  Dagster boundary safety is consolidated into shared helpers for output handling,
  child environments, and run-path identity: redaction always precedes truncation and
  serialization, and child processes receive a positive environment allowlist rather
  than an ambient copy of `os.environ`. Run evidence rejects dirty (uncommitted)
  evidence and gains freshness signals; the terminal live gate stays
  `[PENDING LIVE PROFILE]` with no DSN/driver. Filesystem-derived inputs are
  repository-contained and tracked-only in git workspaces, with a documented
  non-git fallback. No stage is ever changed to `pass` and no readiness approval is
  self-granted. The highest-churn CLI hotspot is split behind behavior-preserving
  tests (`cli/parser.py` -> `parser_core` / `parser_dagster` / `parser_validation`).
  (#429)
- **The `dashboard-design` skill is now narrative-gated (spec 021, Phase B, T009).**
  It STOPs unless a committed `mappings/<table>/narrative-brief.md` (frozen
  `seshat.narrative-brief/v1`) exists before any layout/visual guidance -- absence
  is the named blocker `narrative_brief_missing`, not a warning (FR-004). Its
  binding map is upgraded from two-way (visual -> contract) to THREE-way
  (visual -> contract -> decision-question); an orphan in either direction, a page
  serving no decision, or a bare-total headline visual is a defect (FR-005,
  FR-006). The same gate + route language is mirrored in the marketplace
  `powerbi-workflows` skill, which now also routes to `bi-analyst-knowledge` for
  the framing catalog (T011). The `visual-contract-binding-map.md` template gains a
  machine-readable `seshat.binding-map/v1` front section. This ARMS enforced
  behavior on already-shipped skills; it was owner-gated pending this build. (#452)
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
- `seshat narrative-check`'s contract-revision guard now resolves contracts in
  `mappings/<table>/metrics/` -- the F009 contract-store convention the rest of the
  kit already uses (`gap_detector`, `dashboard_coordinator`, the `--metrics-dir`
  default) -- instead of a `contracts/` directory that no real workspace ships. The
  wrong path made every real brief fail closed on `stale_contract_revision: cannot be
  located`, so the freshness rule was unreachable on real data. (#471)
- `seshat dashboard-gaps` no longer fails open on an unusable `--page-intent`: the
  four unusable shapes (missing, unreadable, invalid YAML, valid-YAML-but-wrong-shape
  -- e.g. a Markdown file, whose bullets parse as a YAML list) now get four distinct
  named errors and CLI exit 2 (a usage error; classification outcomes still always
  exit 0, no gate added). A wrong-format file previously collapsed into the
  misleading "not found or unreadable" + "No required items were classified" with
  exit 0 -- false comfort on a QA surface. A copyable
  `templates/page-intent.example.yaml` now ships, and the shape is documented in the
  `powerbi-workflows` skill routing. (#453)
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
- `powerbi-workflows` skill: documented the PBIR external-edit reload protocol --
  Desktop serves its in-memory session and restores cached view state from
  `.pbi/localSettings.json`, so agent-authored on-disk PBIR edits stay invisible
  until Desktop is fully quit (`PBIDesktop.exe` AND `msmdsrv.exe` gone),
  `localSettings.json` is moved aside for both `.Report` and `.SemanticModel`, and
  the project is reopened via File Explorer (not the Recent list; "Don't Save" on
  the stale-session prompt). The `pbip-workflow` gotcha row now points at the full
  protocol instead of the insufficient "restart Desktop" tip. (#455)
- Docs-only slice 1 for the parked F016 Power BI execution adapter: fixed
  `.mcp.json.example` to default to `--readonly` (was write-enabled with a
  misspelled `--read-write` flag); added `templates/pbi-mcp-adapter-contract.md`
  (the generic adapter-contract skeleton specialized for F016) and
  `docs/integrations/pbi-mcp-adapter.md` (disambiguates Seshat's own governor
  MCP server, the gitignored vendored Power BI Modeling MCP binary, and
  Microsoft's official local/remote Power BI MCP servers, both public preview
  with no published release); updated `docs/powerbi-connection.md` and
  `docs/operations/adapter-compatibility-matrix.md` to point at the new doc.
  No runtime code, no new CLI verb, no MCP call; F016 remains parked pending an
  owner-ratified ADR. (#450)

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
