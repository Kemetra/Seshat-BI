# Feature Specification: Activate the dagster-dbt Engine Seam

**Feature Branch**: `135-activate-dagster-dbt-seam`

**Created**: 2026-07-17

**Status**: Ratified (Ahmed Shaaban, 2026-07-17)

**Roadmap identity**: A follow-up ACTIVATION of the documented engine seam that
already lives in F030 (Dagster, spec 134, SHIPPED) and F029 (dbt, spec 133,
IMPLEMENTED; activation deferred). It is NOT a new roadmap F-number. Spec 134's
`docs/integrations/dagster-adapter.md` section "The dagster-dbt engine seam
(activates after spec 133 merges)" is the documented contract this spec turns
from prose into a selectable engine. Both prerequisite slices are now on main:
spec 134 shipped the 11-asset graph; spec 133 (PR #299) shipped the `dbt/`
project and the `seshat.dbt` control layer.

**Input**: User description: "Activate the dagster-dbt engine seam: the
silver_tables and gold_tables Dagster assets switch from executing
warehouse/migrations SQL to dagster-dbt assets over the spec-133 governed dbt
project, with IDENTICAL gate semantics (same source_map HUMAN SEAM, same check
exit codes, fail-closed), migrations retained as the parity oracle and rollback
path until a named human separately retires them."

## Purpose and Readiness Stage

This feature activates the one seam spec 134 deliberately left as documentation:
the `silver_tables` / `gold_tables` assets gain a SELECTABLE build engine. The
default engine stays the committed `warehouse/migrations/*.sql` path. When the
dbt engine is EXPLICITLY configured, those two assets run the governed dbt build
through the existing `seshat.dbt` planning/gate machinery instead of applying
migration SQL -- with the SAME gate semantics: still downstream of the
`source_map` HUMAN SEAM, still gated on `seshat check` exit 0, still fail-closed,
still recording a `deferred` boundary without a live profile.

The ACTION inside the two assets changes (apply migrations SQL -> run the
governed dbt build); the GATE does not. `seshat check` reads committed text and
is engine-independent; the `source_map` HUMAN SEAM read, the STOP-edge topology,
and the run-evidence contract are untouched. Dagster remains the runner and
Seshat BI remains the readiness authority: the gate exit code and the named human
decide every stage; Dagster decides none.

The adapter serves **Silver Ready** and **Gold Ready** only, exactly as before.
It never creates mapping truth, never grants an approval, never advances a
readiness stage, and never publishes Power BI. This spec adds one engine choice
inside two existing assets; it changes nothing else in the graph.

The first filled instance is `retail_store_sales`, whose mapping gate is already
cleared on main and whose governed dbt selector (`seshat_table_retail_store_sales`)
already exists. That instance proves the generic mechanism; it is not a universal
schema.

## Scope

One narrow slice: an engine switch inside two existing assets.

IN scope:

1. A per-asset, per-table engine selection for `silver_tables` and `gold_tables`
   -- `migrations` (the default) or `dbt` -- resolved from explicit committed
   configuration, never inferred and never defaulted to `dbt`.
2. A dbt engine branch inside the shared build body that runs the governed dbt
   build via `seshat.dbt` (plan -> accept-plan digest recompute -> build in
   isolated shadow schemas), then runs the SAME `seshat check` gate on exit 0.
3. The orchestration project environment gaining the dbt runtime it needs
   (`seshat-bi[dbt]` plus `dagster-dbt`, already pinned with `dagster`), with the
   main `seshat` package gaining NO new dependency.
4. `seshat dagster doctor` surfacing the resolved engine mode per table
   (migrations vs dbt) truthfully, including the deferred-boundary and
   dbt-not-installed states.
5. Run-evidence continuing to render against the unchanged
   `schemas/dagster-run-evidence.schema.json`: the `gate_command` string and the
   `measured` contents differ under the dbt engine; no schema field changes.

OUT of scope (unchanged from spec 133 / spec 134):

- Making dbt the DEFAULT engine, writing migration-owned `silver`/`gold` from
  dbt, or retiring migrations. Migrations remain the default build path, the
  parity oracle, and the rollback path until a named human separately retires
  them (spec 133 FR-006).
- The spec-133 FR-007 build-path switch decision (parity evidence plus named-human
  approval). Whether engaging the dbt engine for a table IS that switch is an
  open question for a human (see Clarifications); this spec does not answer it and
  invents no parallel approval marker.
- Enabling any schedule or sensor. Both stay STOPPED; enabling is a named-human
  action outside this feature.
- Making any new asset publish-capable. The publish wall and F016 trigger are
  untouched.
- Adding a new readiness stage, a run-state engine, or any numeric health /
  confidence / maturity score.
- Non-Postgres engines, incremental models, and Power BI execution.

The switch coexists with "migrations remain the default build path" precisely
because engine selection is EXPLICIT configuration with a FAIL-CLOSED default:
a table with no engine configured, or a malformed engine value, builds via
migrations. Nothing silently flips to dbt.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The dbt engine builds through the governed path with identical gate semantics (Priority: P1)

An operator configures the dbt engine for a mapped, gate-cleared table and runs
the sequence. `silver_tables` / `gold_tables` run the governed dbt build (through
`seshat.dbt` planning and the accept-plan digest recompute) into isolated shadow
schemas, then run the SAME `seshat check` gate. A non-zero check still fails the
asset and skips everything downstream; a zero check materializes with dbt evidence
recorded. The `source_map` HUMAN SEAM upstream is unchanged, and the STOP-edge
topology is unchanged.

**Why this priority**: identical gate semantics under a changed build action is
the whole point of the seam; if the dbt branch weakened the gate or bypassed the
governed plan, the activation would break the constitutional floor it claims to
preserve.

**Independent Test**: with a fixture table configured `engine: dbt`, gate cleared,
and a fake dbt runner returning success, run the two assets in-process and confirm
(a) the governed plan was computed and the accept-plan digest recomputed (no raw
dbt pass-through), (b) the build targeted shadow schemas only, (c) `seshat check`
ran and exit 0 materialized, (d) a forced non-zero check fails the asset and skips
downstream, (e) no readiness stage, `Gate status`, or `approvals[]` changed.

**Acceptance Scenarios**:

1. **Given** a table configured `engine: dbt` with the mapping gate CLEARED,
   **When** `silver_tables` runs, **Then** the governed dbt build runs through
   `seshat.dbt` (plan + accept-plan digest recompute, no raw selector), into
   shadow schemas only, and the `seshat check` gate runs.
2. **Given** the dbt build ran and `seshat check` returns non-zero, **When** the
   asset completes, **Then** the asset is failed, every downstream asset is
   skipped, and evidence records the non-zero exit -- identical to the migrations
   engine.
3. **Given** the dbt build ran and `seshat check` returns 0, **When** evidence is
   written, **Then** the asset is materialized and the record carries the dbt
   engine, the selector, and the measured dbt result -- never the readiness token
   `pass` and never a score.

---

### User Story 2 - The engine is explicit and fails closed to migrations (Priority: P1)

The build engine for each of `silver_tables` / `gold_tables` is resolved from
explicit committed configuration. A table with no engine configured, an
unrecognized engine value, or a malformed configuration builds via the
`migrations` default. The dbt engine is engaged only when the configuration names
it exactly.

**Why this priority**: "migrations remain the default" is a committed spec-133
constraint (FR-006); an ambiguous or inferred engine would silently move a table
off the retained oracle. The fail-closed default is what lets this seam coexist
with that constraint.

**Independent Test**: fixtures with (a) no engine key, (b) `engine: migrations`,
(c) `engine: dbt`, (d) `engine: <garbage>`; assert (a), (b), (d) resolve to the
migrations build and (c) resolves to the dbt build, with no exception leaking a
path or secret.

**Acceptance Scenarios**:

1. **Given** a table with no engine configured, **When** the build asset runs,
   **Then** it uses the migrations engine and records `engine: migrations`.
2. **Given** a table configured with an unrecognized or malformed engine value,
   **When** the build asset runs, **Then** it fails closed to the migrations
   engine (or blocks with a concrete reason) and never silently runs dbt.
3. **Given** a table configured `engine: dbt`, **When** the build asset runs,
   **Then** and only then is the dbt engine engaged.

---

### User Story 3 - The dbt engine is unavailable or has no live profile (Priority: P2)

A table is configured `engine: dbt` but the orchestration environment lacks the
dbt runtime, or no database credentials are present. The asset does not traceback
and does not fabricate a pass. Missing dbt runtime blocks with a concrete remedy;
a missing live profile records a `deferred` boundary with its timestamp, exactly
as the migrations path and `live_validate` do today.

**Why this priority**: dbt compile is `pending` and live parity has not run
(`dbt-activation-status.yaml`); dagster-dbt 0.29.14 driving dbt-core 1.12.0 is an
unproven live surface. The unattended runtime MUST degrade truthfully, never
claim a live pass it cannot prove.

**Independent Test**: fixture `engine: dbt` with (a) the dbt extra absent and (b)
no DSN; assert (a) blocks with the enable remedy and (b) records `deferred` with a
timestamp, and neither writes a readiness pass.

**Acceptance Scenarios**:

1. **Given** `engine: dbt` and no database credentials, **When** the build asset
   runs, **Then** it records a `deferred` boundary with timestamp and blocks
   fail-closed -- no fabricated pass, no readiness change.
2. **Given** `engine: dbt` and the dbt runtime absent from the orchestration
   environment, **When** the build asset runs, **Then** it blocks with a concrete
   `blocking_reason` and named owner, and emits no traceback.

---

### User Story 4 - The doctor surfaces the resolved engine mode (Priority: P2)

An operator runs `seshat dagster doctor` and sees, per mapped table, which build
engine is resolved (`migrations` or `dbt`) and -- when `dbt` -- whether the dbt
runtime and a live profile are available. The doctor never fabricates readiness;
absent prerequisites are reported concretely.

**Why this priority**: the doctor is the front door; an activated engine seam that
is invisible to the preflight means an operator cannot tell which path a run will
take before it runs.

**Independent Test**: run doctor over fixtures with mixed engine configuration and
confirm each table's resolved engine and dbt availability are reported truthfully,
with no score and no fabricated live pass.

**Acceptance Scenarios**:

1. **Given** a table configured `engine: dbt`, **When** doctor runs, **Then** it
   reports the dbt engine and, when the dbt runtime or DSN is absent, the concrete
   deferred/enable finding.
2. **Given** a table on the default engine, **When** doctor runs, **Then** it
   reports `migrations` and asserts nothing about dbt.

---

### User Story 5 - Migrations remain the untouched parity oracle and rollback (Priority: P1)

Activating the dbt engine for a table changes only what the two assets EXECUTE. It
never deletes, supersedes, or stops applying a migration; it never writes
migration-owned `silver`/`gold` from dbt. Reverting a table to `engine: migrations`
restores the prior behavior byte-for-byte, and the committed migrations remain the
parity oracle for any future FR-007 build-path decision.

**Why this priority**: spec 133 FR-006 makes migrations the retained oracle and
rollback path; if activating dbt mutated or removed migrations, the rollback and
parity story would be gone and the activation would be irreversible -- the exact
failure the medallion gate exists to prevent.

**Independent Test**: with the dbt engine active for a table, assert the
`warehouse/migrations/` files are unmodified and the dbt build wrote only shadow
schemas; flip the config back to `migrations` and assert the migrations build runs
exactly as it did before this feature.

**Acceptance Scenarios**:

1. **Given** a table with `engine: dbt` active, **When** a run completes, **Then**
   no `warehouse/migrations/` file changed and no migration-owned `silver`/`gold`
   relation was written by dbt.
2. **Given** a table reverted to `engine: migrations`, **When** the build asset
   runs, **Then** its behavior is identical to the pre-feature migrations path.

### Edge Cases

- Engine configured `dbt` but the table's mapping gate is NOT cleared: the
  `source_map` HUMAN SEAM upstream blocks `silver_tables` before any engine runs;
  the engine choice never runs around the gate.
- Engine configured `dbt` but the governed dbt selector or model contract for the
  table is missing/stale: the governed `seshat.dbt` gate refuses before invoking
  dbt; the asset blocks with the concrete governance reason, no traceback.
- The accepted plan digest drifts between plan and build (source map revision,
  project fingerprint, versions, selection, target changed): `seshat.dbt` refuses
  the stale digest; the asset blocks fail-closed.
- (RESOLVED by the FR-011 owner decision) dagster-dbt was found to EXCLUDE
  dbt-core 1.12 at solve time (ResolutionImpossible); the unused library is
  removed from the orchestration environment instead of downgrading dbt. Live
  dbt execution stays `[PENDING LIVE PROFILE]`.
- A raw dbt selector, schema override, profile, or arbitrary dbt argument is
  attempted through the asset: rejected by the governed `seshat.dbt` runner before
  dbt is invoked (spec 133 FR-023); the asset never accepts pass-through.
- dbt logs echo profile-derived values in an error: redacted before the text
  reaches dagster run-evidence or console (Principle IX; shared redaction).
- A table is `engine: dbt` for silver but `migrations` for gold (or vice versa):
  each asset resolves its own engine independently; a mixed configuration is
  allowed, recorded per asset, flagged as a doctor WARNING, and marked in the
  evidence record (a migrations layer may be reading a real relation this run's
  dbt layer never rebuilt -- FR-015).
- A dbt-engine run completes green but the operator believes the real warehouse
  was refreshed: the evidence record states `warehouse_updated: false` under the
  dbt engine; the real `silver`/`gold` were last built by a migrations run
  (FR-015).
- The unattended dagster child is killed (timeout, CI cancellation) while holding
  the `seshat.dbt` cross-process lock: a subsequent run must surface a concrete
  redacted lock `blocking_reason` (never a traceback, never a silent hang), per
  the bounded-lock semantics inherited from spec 133.
- Secrets in errors: any DSN/host/credential in a child-process error is redacted
  before it reaches evidence or console output, identical to the migrations path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `silver_tables` and `gold_tables` assets MUST resolve a build
  engine per table from explicit committed configuration with allowed values
  `migrations` (default) and `dbt`. The engine MUST NOT be inferred; any absent,
  unrecognized, or malformed value MUST fail closed to `migrations`. The engine
  flag MUST live inside the table's human-reviewed committed working set
  (`mappings/<table>/`), so flipping an engine is itself a reviewed, committed,
  attributable change; an environment variable, CLI flag, or any runtime input
  MUST NOT select the engine (plan-review R1/F2).
- **FR-002**: When the resolved engine is `dbt`, the build asset MUST run the
  governed dbt build through the existing `seshat.dbt` machinery -- resolve the
  working set and gate, compute an execution plan, recompute and honor the
  accept-plan digest, and run the fixed governed selector for the table. It MUST
  NOT accept a raw dbt selector, schema override, profile, or arbitrary dbt
  argument, and MUST NOT invoke `dagster-dbt` in a way that bypasses
  `seshat.dbt` planning/gate.
- **FR-003**: The dbt engine MUST materialize only isolated shadow schemas and
  MUST NOT write migration-owned `silver` or `gold` (spec 133 FR-005). No code
  path may delete, supersede, or stop applying a `warehouse/migrations/*.sql`
  file (spec 133 FR-006).
- **FR-004**: The GATE MUST be identical across engines: both engines run the SAME
  `seshat check` command and treat exit 0 as the only green; a non-zero exit marks
  the asset failed and skips all downstream assets (the STOP edge is unchanged);
  the `source_map` HUMAN SEAM upstream is unchanged. No engine may run around a
  STOP edge.
- **FR-005**: The dbt engine build MUST be downstream of the `source_map` HUMAN
  SEAM exactly as the migrations engine is; the asset dependency topology
  (deps/edges) MUST NOT change. Only the build body branches on engine.
- **FR-006**: When the resolved engine is `dbt` and no database credentials are
  present, the asset MUST record a `deferred` boundary with timestamp and block
  fail-closed; it MUST NOT fabricate a pass. When the dbt runtime is absent from
  the orchestration environment, the asset MUST block with a concrete
  `blocking_reason` and named owner and emit no traceback.
- **FR-007**: No code path added by this feature may write a readiness `status`,
  a `Gate status`, an `approvals[]` entry, a metric definition, a mapping, or any
  Power BI publish. It MUST NOT grant or record the spec-133 FR-007 build-path
  switch. Derived run-evidence and `evidence[]` / `blocking_reasons[]` surfacing
  are the ONLY writes.
- **FR-008**: The run-evidence record MUST continue to conform to
  `schemas/dagster-run-evidence.schema.json` with NO schema change: under the dbt
  engine only the `gate_command` string and the `measured` object contents differ;
  asset names, outcomes (execution words, never `pass`), and required fields are
  unchanged; no numeric score field is introduced.
- **FR-009**: The dagster run-evidence (under
  `orchestration/dagster/run-evidence/`) and the dbt run-evidence (under
  `mappings/<table>/dbt-evidence/`) MUST remain distinct records. The build asset
  MAY cite the dbt evidence location in its dagster record; it MUST NOT conflate,
  overwrite, or merge the two.
- **FR-010**: `seshat dagster doctor` MUST report, per mapped table, the resolved
  build engine and -- when `dbt` -- whether the dbt runtime and a live profile are
  available, as categorical findings with concrete remedies. It MUST NOT emit a
  numeric score and MUST NOT fabricate a live pass when a prerequisite is absent.
- **FR-011**: The orchestration project environment MUST gain the dbt runtime it
  needs (`seshat-bi[dbt]` bringing the pinned dbt-core/dbt-postgres pair) and
  MUST DROP the `dagster-dbt` pin -- OWNER DECISION (Ahmed Shaaban, 2026-07-17,
  resolving plan-review R3): no released dagster-dbt accepts dbt-core 1.12, and
  the seam's execution path never imports dagster-dbt (the R5 static oracle
  forbids it), so the unused library is removed rather than downgrading the
  spec-133 dbt pins. Every surface asserting the dagster/dagster-dbt "pinned
  pair" (doctor findings, definitions-load smoke, docs, contract tests) MUST be
  reconciled to the dagster-only reality, recording the removal as deliberate.
  The main `seshat` package MUST gain NO dagster or dagster-dbt dependency, and
  its static core import path MUST stay stdlib-only.
- **FR-012**: All added surfaces MUST be generic (placeholders like `<table>`;
  `retail_store_sales` appears only as the filled first instance), ASCII-only,
  UTF-8 without BOM; secrets only via the git-ignored `.env`. Every surfaced error
  MUST pass the shared redaction (DSN/host/user/password/paths) before output.
- **FR-013**: Every LIVING document claiming the seam is future/documentation-only
  MUST be reconciled to the activated, selectable-engine reality -- at minimum
  `docs/integrations/dagster-adapter.md` (section "The dagster-dbt engine seam")
  and `orchestration/dagster/README.md` -- without erasing history and without
  claiming a live pass that is still `[PENDING LIVE PROFILE]`. Frozen artifacts
  (the spec 134 directory, CHANGELOG history, `docs/releases/*`) MUST NOT be
  reworded (plan-review R4).
- **FR-014**: Under the dbt engine the accept-plan digest functions as a
  DRIFT-GUARD ONLY, not a review record: the unattended asset recomputes the plan
  and self-accepts its own digest, so no per-run human review occurs. The
  compensating control is FR-001's reviewed committed engine flag. The run
  evidence MUST record that the plan was self-accepted-by-recompute
  (plan-review R1).
- **FR-015**: The dbt engine is a governed REHEARSAL into shadow schemas: it does
  NOT rebuild the real `silver`/`gold` relations, and downstream assets continue
  to validate the migration-built warehouse. The run evidence MUST record this
  truthfully (a `warehouse_updated: false` measured field or equivalent) under
  the dbt engine, and `seshat dagster doctor` MUST emit a WARNING finding for any
  table whose layers resolve to MIXED engines (plan-review R2).

### Key Entities

- **Build engine selection**: a per-asset, per-table value in `{migrations, dbt}`
  read from explicit committed configuration; the resolution rule (default
  `migrations`, fail-closed on absent/unrecognized/malformed).
- **dbt engine branch**: the alternate body of `silver_tables`/`gold_tables` that
  drives the governed `seshat.dbt` build (plan, accept-plan digest recompute,
  shadow-schema build) in place of `db.apply_sql_file` over migrations.
- **Governed selector**: the fixed spec-133 mapping from one table ID to an exact
  dbt node set (tag `seshat_table_<table>`); it MUST NOT be widened by raw dbt
  syntax through the asset.
- **dagster run-evidence record**: the existing derived record at
  `orchestration/dagster/run-evidence/<run-id>.md`; under the dbt engine it
  carries the dbt `gate_command` and measured contents, same schema.
- **dbt run-evidence record**: the spec-133 sanitized record at
  `mappings/<table>/dbt-evidence/<invocation-id>.json`; a distinct artifact the
  dagster record may cite, never merge.
- **Engine-mode doctor finding**: a categorical `seshat dagster doctor` finding
  reporting the resolved engine and dbt availability per table.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With `engine: dbt` and a fake successful dbt runner, the two build
  assets run the governed plan (accept-plan digest recomputed, no raw selector),
  target shadow schemas only, and gate on `seshat check` exit 0 -- proven
  in-process with no database.
- **SC-002**: A forced non-zero `seshat check` under the dbt engine fails the
  asset and skips all downstream assets, identical to the migrations engine
  (asserted in-process).
- **SC-003**: Every engine-resolution fixture (absent / `migrations` / `dbt` /
  malformed) resolves as specified: only the exact `dbt` value engages dbt; all
  others use migrations.
- **SC-004**: With `engine: dbt` and no DSN, the asset records `deferred` with a
  timestamp and blocks; with the dbt runtime absent it blocks with the enable
  remedy -- neither fabricates a pass (asserted in-process, no database).
- **SC-005**: A reviewer can grep the diff and find zero writes to readiness
  `status:` fields, `Gate status:` lines, `approvals[]` entries, or an FR-007
  build-path switch by adapter code, and zero numeric score fields in any evidence
  artifact.
- **SC-006**: `git diff` shows no change to `schemas/dagster-run-evidence.schema.json`
  and no change to the asset dependency topology; the definitions-load smoke and
  US1-US3 fixture tests pass with no database and no secrets.
- **SC-007**: `warehouse/migrations/` files are unmodified by any dbt-engine run,
  and reverting a table to `engine: migrations` reproduces the pre-feature
  behavior.
- **SC-008**: The full existing test suite plus the new tests pass; ruff
  format/lint clean; `seshat check` (static governance) reports no new findings;
  the main `seshat` package imports with no dagster / dagster-dbt / dbt module
  loaded.

## Clarifications

Each item below is a genuine ambiguity in the feature. Resolved items record the
RECOMMENDED answer with one-line reasoning. Items that grant, approve, or retire
anything are left UNANSWERED under "Open for human".

### Resolved (recommended)

- **Q: Does the dbt engine become the ACTIVE producer of the real Power BI
  `silver`/`gold` reads, or a selectable engine that still writes shadow schemas?**
  A: A selectable engine writing SHADOW schemas only. Reasoning: spec 133 FR-005
  forbids dbt writing migration-owned `silver`/`gold`; making dbt the real
  producer would contradict committed governance and require the FR-007 named-human
  switch this spec cannot make.

- **Q: What is the default engine, and how is a missing/malformed engine value
  handled?**
  A: Default `migrations`; absent/unrecognized/malformed fails closed to
  `migrations`. Reasoning: spec 133 FR-006 keeps migrations the default build path;
  a fail-closed default is the only way the seam coexists with that constraint.

- **Q: How does the unattended asset obtain the accept-plan digest that spec 133
  requires for a governed build?**
  A: It recomputes the plan and passes its own digest; the drift-guard still holds
  (a stale digest refuses). Reasoning: spec 133 FR-023/FR-025 forbid raw dbt
  pass-through and require digest recompute; the asset must go through
  `seshat.dbt` planning, not a raw `dagster-dbt` CliResource. AMENDED per
  plan-review R1: this makes the digest a drift-guard only (no per-run human
  review); the compensating control is the reviewed committed engine flag
  (FR-001), and evidence records the self-acceptance (FR-014).

- **Q: Where does the dbt runtime dependency live?**
  A: In the orchestration project environment only (`seshat-bi[dbt]` plus the
  already-pinned `dagster-dbt`); the main `seshat` package gains nothing.
  Reasoning: spec 134 FR-001 keeps the main package's static core stdlib-only and
  dagster out of it.

- **Q: Does the run-evidence schema change under the dbt engine?**
  A: No. Only the `gate_command` string and `measured` contents differ; asset
  names, outcomes, and required fields are unchanged. Reasoning: `measured` is an
  open object and asset names are engine-independent in the committed schema.

- **Q: Are the two evidence systems merged?**
  A: No -- dagster run-evidence and dbt run-evidence stay distinct; the dagster
  record may cite the dbt record's location. Reasoning: they are different
  categories (run log vs invocation record) with different schemas and owners.

- **Q: Can silver and gold have different engines for the same table?**
  A: Yes; each asset resolves its own engine independently and records it.
  Reasoning: the assets are distinct build steps; a mixed configuration is a valid
  intermediate state and is simpler than a coupled table-wide flag. AMENDED per
  plan-review R2: a mixed configuration has a semantic trap (a migrations layer
  can read a real relation this run's dbt layer never rebuilt), so doctor MUST
  warn on mixed engines and the evidence record marks the mix (FR-015); mixed
  stays allowed but never silent.

### Open for human (UNANSWERED -- Principle V)

- Whether engaging the dbt engine for a table CONSTITUTES the spec-133 FR-007
  build-path switch (which requires passing parity evidence plus a named-human
  approval) or is a separate orchestration-configuration decision. This maps onto
  the EXISTING FR-007 seam; this spec does not answer it and invents no parallel
  approval marker.

- Whether flipping the build engine to `dbt` for a table needs its own named-human
  approval, and if so, who owns it and where it is recorded.

- Whether the dbt engine may EVER write real (migration-owned) `gold`, and if so,
  under what named-human authority.

- When and how the retained migrations are RETIRED for a table once dbt is proven.
  This is explicitly NOT this spec's call (spec 133 FR-006 keeps migrations until a
  named human retires them).

## Assumptions

- Spec 134's authority text, asset graph, forbidden-operations matrix, and
  run-evidence schema are FIXED inputs; this spec activates the documented engine
  seam without redefining them.
- Spec 133 is MERGED (PR #299): the `dbt/` project, the governed selector
  (`seshat_table_retail_store_sales`), and the `seshat.dbt` control layer
  (gate/planning/runner/evidence/redaction) are on main and are the machinery this
  seam drives. Their governance (FR-005 shadow-only, FR-006 migrations-default,
  FR-007 named-human switch) is a FIXED constraint this spec does not override.
- `retail_store_sales` has a cleared mapping gate on main and serves as the filled
  first instance.
- dbt runtime activation remains `[PENDING LIVE PROFILE]`
  (`docs/operations/dbt-activation-status.yaml`: compile pending, live parity
  pending, compatibility-owner attestation missing). This feature ships the
  selectable-engine WIRING; live dbt execution stays deferred and records
  `deferred` without a live profile.
- dagster-dbt is REMOVED from the orchestration environment (FR-011 owner
  decision); the seam executes through `seshat.dbt` only. Live dbt drive is
  verified only when a disposable Postgres profile is available.
- Python 3.13 is the floor for both the main package and the orchestration
  project.
- Enabling schedules/sensors, F016 publish, dbt-as-default, real-gold writes, and
  numeric scoring stay out of scope (spec 133 / spec 134 deferred decisions
  unchanged).
