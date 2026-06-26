# Feature Specification: dbt Transformation Adapter -- dbt is the build engine, Tower BI is the brain

**Feature Branch**: `023-dbt-transformation-adapter`  **Roadmap feature**: F029
(Numbering note: the roadmap F-number is the authoritative identity; the spec-dir
number is the next free on-disk slot. This batch maps F024=spec 018, F025=019,
F026=020, F027=021, F028=022, **F029=spec 023**, F030=024, F031=025, F032=026,
F033=027. When the dir number and the F-number disagree, the roadmap F-number wins.
F024-F033 are a forward batch not yet recorded in the committed roadmap, which today
documents through F016; this spec does not edit the roadmap.)

**Created**: 2026-06-25   **Status**: Shipped (dbt-transformation-adapter skill landed; spec authored no runtime Python by design)

**Input**: "Define how dbt enters as a TRANSFORMATION ADAPTER for Silver/Gold without
becoming the brain. dbt is the build ENGINE; Tower BI is the brain. Entry condition:
dbt may build staging/silver/gold models ONLY after Mapping Ready = pass; dbt models
MUST cite source-map evidence; dbt tests produce evidence; Tower readiness + a named
human decide Silver Ready / Gold Ready. dbt MUST NOT define source mapping, define
metric contracts, publish Power BI, resolve business ambiguity, or silently change
grain. Reconcile against the existing warehouse/migrations build: recommend dbt as an
OPTIONAL alternative transformation engine that must produce output matching the
current gold tables (a reconciliation acceptance test), with migrations remaining the
default until dbt parity is proven. Category (per F024): Execution Adapter,
DB-connected, not publish-capable. Readiness stage affected: Silver Ready, Gold Ready.
Planning-only: enumerate the future dbt project shape and deliverables; create no dbt
files in this slice."

## Clarifications

### Session 2026-06-25

- Q: What is the parity tolerance for additive money sums, and is the parity assertion limited to the fact or extended to the dimensions? -> A: Exact to the cent (an absolute delta <= 0.01 on each additive-measure sum, since silver/gold use `NUMERIC(12,2)`), AND assert per-dimension distinct row counts in addition to the fact's row count and `transaction_id` distinct count. This closes the divergent-unknown-member gap the edge cases flag.
- Q: After a table's build-path switch (migrations -> dbt) is approved, what happens to that table's migration files? -> A: Retain them; the migration files are NOT deleted on switch. They remain the parity oracle and the rollback path, marked superseded-but-kept; retiring a migration is a separate, later named-human decision, not a side effect of the switch.
- Q: After a table is switched to dbt, does the reconciliation parity test run once (at switch) or on every dbt build? -> A: Re-run the parity test on every dbt build for a switched table, against the retained migration oracle, for as long as that oracle is retained. A one-time-at-switch check would let the two paths silently diverge afterward.

## Why this feature exists

The warehouse already builds silver and gold as numbered, idempotent SQL migrations
(`warehouse/migrations/0001_create_silver_*.sql`, `0002_create_gold_star.sql`, and the
per-table pair `0003_create_silver_retail_store_sales.sql` /
`0004_create_gold_retail_store_sales_star.sql`). That hand-authored SQL is the default
build path and it is approved and live. But teams that already standardize on dbt for
warehouse transformation will want to express the same silver/gold build as dbt models,
gaining dbt's dependency graph, incremental materialization, test framework, and
documentation site -- without giving up Tower BI's gate-enforced readiness.

This feature defines the **terms of entry** for dbt as a TRANSFORMATION ADAPTER. It
answers one question precisely: how can dbt build silver/gold tables while Tower BI --
not dbt -- remains the authority that decides whether Silver Ready and Gold Ready are
`pass`? The answer is a clean separation of roles. dbt is the build **engine**: it
compiles SQL, materializes models, and runs tests. Tower BI is the **brain**: it owns
the approved source-map (the only legal source of what each model means), owns metric
contracts, owns the readiness spine, and routes every judgment call to a named human.
A green `dbt test` is **evidence**, never an approval.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **dbt does NOT replace Tower BI's authority.** dbt is a build engine the agent may
  invoke once a gate is cleared; it is not the gate. A passing `dbt build` /
  `dbt test` run does NOT move Silver Ready or Gold Ready to `pass`. Tower readiness +
  a named human decide that, on the evidence dbt produced. (Core Authority owns truth;
  an adapter may EXECUTE approved steps and write DERIVED evidence, never create truth.)
- **dbt does NOT define source mapping.** Every dbt model MUST cite the already-approved
  `source-map.yaml` for the table it builds. dbt models that introduce a column meaning,
  a grain, a PK, a PII decision, or a placement that the approved map does not already
  state are out of scope and forbidden (see Forbidden operations). dbt reads the map; it
  does not author it.
- **dbt does NOT define metric contracts or semantic logic.** Metrics live in the metric
  contract store (F009) and bind to gold columns. A dbt model MUST NOT encode a metric
  formula, a business rollup, or a segment mapping. Those are F009 artifacts decided by
  the metric owner.
- **dbt does NOT publish Power BI.** dbt is DB-connected, not publish-capable (the
  F024 category for this adapter). Materializing or publishing a Power BI model is the
  parked F016 execution adapter, gated separately. dbt stops at gold.
- **dbt does NOT resolve business ambiguity or silently change grain.** A grain
  question, a sentinel-vs-null choice, a PII publish-safety question, or a business
  rollup/segment mapping the map does not answer is a Principle V stop-and-ask: the
  agent recommends, a named human decides. dbt never auto-resolves one, and a dbt model
  may never change the declared grain without a re-approved map.
- **This slice ships NO dbt files and NO runtime code.** It writes ONLY the five
  planning artifacts (this spec, plan.md, tasks.md, two checklists). The dbt project
  shape and the integration docs/decisions/templates/skill are ENUMERATED below as
  PLANNED future outputs -- they are not created now.
- **Generic.** `retail_store_sales` (the C086-adjacent worked example) is CITED as the
  filled first-MVP instance; its specifics never enter the generic dbt-adapter-contract
  or dbt-model-contract templates (Principle VII).

## Relationship to shipped features (scope delta)

- **F024 (Companion Tools / Execution Adapter architecture)** -- DEPENDS ON. F024
  defines the adapter taxonomy and the categories. This feature is one adapter in the
  category **Execution Adapter, DB-connected, not publish-capable**, and inherits F024's
  rules (read evidence, execute approved steps, write derived evidence, create no truth).
  This spec references F024 by roadmap identity only; it does not restate F024's content.
- **F006 (Table Onboarding Wizard) + `warehouse/migrations`** -- RECONCILES WITH. The
  `retail-build-warehouse` skill (the F006 builder seam) authors the silver/gold
  migration SQL from an approved map. dbt is an OPTIONAL ALTERNATIVE to that SQL build
  path, not a replacement: migrations remain the DEFAULT build until dbt parity is
  proven by the reconciliation acceptance test (see FR-006, SC-002). A table may be
  built by migrations or by dbt; it is never built by both into the same gold tables
  without a documented switch and a passing parity check.
- **F005 (Retail Readiness Model)** -- WRITES DERIVED EVIDENCE INTO. dbt run/test
  results and the parity-check result are recorded as `evidence[]` in the table's
  `mappings/<table>/readiness-status.yaml`; the stage status is still decided by Tower
  readiness + a named human, not by dbt's exit code.
- **F009 (Metric Contract Store)** -- BOUNDARY. dbt builds the gold columns that metric
  contracts bind to; dbt never defines a contract. Clean line: dbt produces columns,
  F009 defines meaning over them.
- **F016 (Power BI Execution Adapter, parked)** -- DISJOINT. F016 is publish-capable and
  gated on semantic-model readiness; dbt is DB-connected and stops at gold. They are
  different adapter categories and never overlap.

## Architecture (planning posture)

Planning-only this slice. The shippable artifacts are the five spec-kit files. The
feature, WHEN BUILT in a later slice, is a DB-connected execution adapter plus its
governing docs and a thin agent skill that orchestrates dbt behind the gate:

- A **dbt project** (`dbt/`) that expresses staging -> silver -> gold as models, with a
  `sources` layer that points at the already-built bronze/silver and a `marts` layer
  that reproduces the gold star. NOT created this slice -- shape enumerated in plan.md.
- A `profiles.example.yml` (example only, NO secrets) documenting the connection profile
  shape; the real `profiles.yml` is git-ignored and supplied by the operator.
- An **adapter contract** (`templates/dbt-adapter-contract.md`) and a **model contract**
  (`templates/dbt-model-contract.md`) that bind every dbt model to its source-map
  evidence and to the readiness gate -- generic templates, no `retail_store_sales`
  values baked in.
- A **decision record** (`docs/decisions/0009-dbt-is-transformation-adapter.md`) that
  records the optional-alternative posture and the parity requirement.
- An **integration doc** (`docs/integrations/dbt-adapter.md`) that documents how dbt plugs
  in as an optional engine behind the Mapping Ready gate.
- A **skill** (`.claude/skills/dbt-transformation-adapter/SKILL.md`) that lets the agent
  run dbt ONLY behind the Mapping Ready gate and record its output as derived evidence.

The agent is the runtime that invokes dbt; Tower readiness + a named human are the
authority that interprets dbt's evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - dbt may build only after Mapping Ready = pass (Priority: P1)

The agent is asked to build silver/gold for a table using dbt. Before any dbt model runs,
the adapter checks the table's `mappings/<table>/readiness-status.yaml`: if Mapping Ready
is not `pass`, the adapter refuses and records the blocking reason. dbt never builds from
an unmapped or unapproved source.

**Why this priority**: this is the single entry condition that keeps dbt a build engine
and not a back-door around the mapping gate (Principle IV). Without it the adapter would
let dbt define meaning by building it. It is the MVP boundary.

**Independent Test**: point the planned adapter at a table whose Mapping Ready is
`not_started`/`blocked`/`warning`; confirm the documented behavior is REFUSE + record a
`blocking_reason`, and that no dbt model is permitted to run. Then set Mapping Ready to
`pass` and confirm the adapter is permitted to proceed.

**Acceptance Scenarios**:

1. **Given** a table whose Mapping Ready is not `pass`, **When** a dbt build is requested,
   **Then** the adapter refuses, records a `blocking_reason` ("Mapping Ready not pass"),
   and runs no model.
2. **Given** a table whose Mapping Ready is `pass`, **When** a dbt build is requested,
   **Then** the adapter is permitted to run staging/silver/gold models that cite the
   approved map.
3. **Given** a dbt model that introduces a meaning (a grain, PK, PII flag, or placement)
   the approved map does NOT state, **When** it is reviewed, **Then** it is a defect: the
   model must cite the map, not extend it (Principle V; the map is re-approved first).

---

### User Story 2 - Every dbt model cites its source-map evidence (Priority: P1)

Each dbt staging/silver/gold model carries, in its model contract, a reference to the
exact `source-map.yaml` rows that justify its columns, grain, and placement. A reviewer
can trace any model column back to an approved map entry.

**Why this priority**: this is what keeps dbt a reader of truth, not an author of it. The
citation is the proof that dbt did not invent meaning. Equal-MVP with US1.

**Independent Test**: take one planned staging model contract; confirm it names the table,
the approved map version (a git ref), and the map rows for each column/grain it builds, and
that a reviewer can follow each reference to a real, approved map entry.

**Acceptance Scenarios**:

1. **Given** a dbt model, **When** its model contract is read, **Then** it cites the
   table's approved `source-map.yaml` (by path + git ref) and the specific rows for grain,
   PK, and each column it builds.
2. **Given** a model that builds a column with no corresponding approved map row, **When**
   it is reviewed, **Then** the missing citation is a defect that blocks the model.
3. **Given** the approved map changes (a new version), **When** the dbt models are rebuilt,
   **Then** the model contracts must re-cite the new map version; a stale citation is a
   defect (reconciles with F008 mapping-diff review).

---

### User Story 3 - dbt tests produce evidence; readiness + a human decide (Priority: P1)

The first-MVP dbt models carry basic tests: `unique(transaction_id)`, `not_null(
transaction_id)`, `relationships` from the fact's foreign keys to each dimension, and a
**reconciliation test** comparing the dbt-built mart to the existing gold tables. dbt
runs the tests and the adapter records the pass/fail counts as `evidence[]` in the
readiness status. The stage status (Silver Ready / Gold Ready) is moved to `pass` only
by Tower readiness + a named human reading that evidence -- never by dbt's exit code.

**Why this priority**: this is the governance hinge of the whole feature. Conflating a
green `dbt test` with an approved gate is exactly how a DB-connected adapter rots into
the brain. Equal-MVP.

**Independent Test**: read the adapter contract; confirm it states that dbt test results
are recorded as evidence, that the stage status is decided by Tower readiness + a named
human, and that no path exists by which a green `dbt test` alone writes `pass`.

**Acceptance Scenarios**:

1. **Given** a completed `dbt build` + `dbt test` with all tests green, **When** the
   adapter records results, **Then** it writes test pass counts as `evidence[]` and leaves
   the stage status unchanged pending Tower readiness + a named human approval.
2. **Given** a `dbt test` failure (e.g. a non-unique `transaction_id`), **When** the
   adapter records results, **Then** it records a `blocking_reason` with the measured
   failing count and Gold Ready stays `blocked`.
3. **Given** all tests green AND a named human approval recorded, **When** Tower readiness
   evaluates the stage, **Then** Silver/Gold Ready may move to `pass` with the dbt evidence
   + the approval cited; the dbt run alone never did this.

---

### User Story 4 - dbt output must reconcile to the existing gold tables (Priority: P2)

For a table already built by migrations, the dbt marts must reproduce the SAME gold
output. A reconciliation test compares the dbt-built mart to the migration-built gold
table (`gold.fct_sales_rss` for the worked example): row count equal, `transaction_id`
uniqueness preserved, and the additive money measure sums (e.g. `total_spent`) equal
within a stated tolerance. Until parity passes, migrations remain the default and dbt is
not the source of the gold tables Power BI reads.

**Why this priority**: parity is what lets dbt be an OPTIONAL alternative without a silent
divergence between two build paths. It is high-value but follows the gating + citation
MVP (US1-US3), since parity is only meaningful once dbt is allowed to build at all.

**Independent Test**: define the parity check between a dbt mart and the matching
migration gold table; confirm it asserts equal fact row count, preserved `transaction_id`
distinct count, additive-measure-sum equality to the cent (absolute delta `<= 0.01` per
measure), and equal per-dimension distinct row counts, that a mismatch keeps Gold Ready
`blocked` and keeps migrations as the default, and that after an approved switch the check
re-runs on every dbt build while the migration oracle is retained.

**Acceptance Scenarios**:

1. **Given** a dbt-built mart and the migration-built `gold.fct_sales_rss`, **When** the
   reconciliation test runs, **Then** it asserts equal fact row count, equal
   `transaction_id` distinct count, `SUM(total_spent)` equal to the cent (absolute delta
   `<= 0.01`), and equal per-dimension distinct row counts (each conformed dimension's
   member count, including the `-1` unknown member where present).
2. **Given** any parity assertion fails, **When** results are recorded, **Then** the
   measured delta is a `blocking_reason`, Gold Ready stays `blocked`, and migrations
   remain the default build path.
3. **Given** parity passes AND a named human approves the switch, **When** the build path
   is changed, **Then** the decision (dbt becomes the build path for that table) is
   recorded as evidence with the parity result + the approver; the agent never flips the
   default on its own; and that table's migration files are RETAINED (not deleted) as the
   parity oracle and rollback path.
4. **Given** a table already switched to dbt with its migration oracle retained, **When**
   any subsequent dbt build runs, **Then** the reconciliation parity test re-runs against
   that oracle and a new divergence keeps Gold Ready `blocked` until a named human resolves
   it; the parity check is not a one-time-at-switch event.

---

### Edge Cases

- **dbt models exist but the map was never approved**: the adapter refuses to run (US1);
  the presence of model files is not permission to build.
- **The dbt unknown-member handling diverges from the migration's -1 sentinel**: the
  reconciliation test catches the row-count/sum mismatch; resolving sentinel-vs-null is a
  Principle V stop-and-ask, not a dbt default.
- **A dbt model would change the declared grain** (e.g. collapsing line items): forbidden
  without a re-approved map; the model contract's grain citation would no longer resolve.
- **`profiles.yml` contains a real DSN/secret**: forbidden in any tracked file; only
  `profiles.example.yml` (placeholders, no secrets) is committed; `profiles.yml` is
  git-ignored.
- **A dbt-core / dbt-postgres auto-update opens a major-version PR**: no automerge; a
  named human reviews, and no minor/major merges until compatibility tests exist (FR-010).
- **dbt `sources` freshness or a test passes but Tower readiness has not been evaluated**:
  the stage stays at its prior status; a green dbt run never advances the stage by itself.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The adapter MUST refuse to run any staging/silver/gold dbt model for a table
  whose `mappings/<table>/readiness-status.yaml` does not record Mapping Ready = `pass`,
  recording a `blocking_reason` instead (Principle IV; entry condition).
- **FR-002**: Every dbt model MUST cite, via its model contract, the approved
  `source-map.yaml` (path + git ref) and the specific map rows justifying its grain, PK,
  and each column. A model column with no approved map citation is a defect.
- **FR-003**: dbt MUST NOT define source mapping, metric contracts, business rollups, or
  segment mappings; MUST NOT change the declared grain without a re-approved map; and MUST
  NOT resolve any Principle V judgment call (grain ambiguity, sentinel-vs-null, PII
  publish-safety, business rollup) -- these stop-and-ask for a named human.
- **FR-004**: dbt test results (counts of passing/failing tests, the failing rows' measured
  numbers) MUST be recorded as `evidence[]` / `blocking_reasons[]` in the readiness status.
  A green `dbt test` MUST NOT move Silver Ready or Gold Ready to `pass`; Tower readiness +
  a named human do that, citing the dbt evidence + the approval.
- **FR-005**: The first MVP to PLAN (not implement) is one `retail_store_sales` staging
  model + one mart model + basic tests: `unique(transaction_id)`, `not_null(
  transaction_id)`, `relationships` from the fact FKs to each dimension, and a
  reconciliation test against the existing gold tables.
- **FR-006**: dbt MUST be specified as an OPTIONAL ALTERNATIVE transformation engine.
  `warehouse/migrations` remains the DEFAULT build path; dbt becomes a table's build path
  ONLY after the reconciliation parity test passes AND a named human approves the switch.
  Both paths MUST NOT silently feed the same gold tables. After an approved switch, that
  table's migration files MUST be RETAINED (not deleted) as the parity oracle and the
  rollback path, marked superseded-but-kept; retiring a migration is a separate later
  named-human decision, never a side effect of the switch. While the migration oracle is
  retained, the reconciliation parity test (FR-007) MUST re-run on EVERY dbt build for that
  table -- a one-time-at-switch check is insufficient because it would let the two paths
  silently diverge afterward.
- **FR-007**: The reconciliation parity test MUST assert, for a table already built by
  migrations, against the migration-built gold table (`gold.fct_sales_rss` for the worked
  example): equal fact row count, preserved `transaction_id` distinct count, additive
  money-measure sum equality (e.g. `SUM(total_spent)`) to the cent (absolute delta
  `<= 0.01` per additive measure, since silver/gold use `NUMERIC(12,2)`), AND equal
  per-dimension distinct row counts (each conformed dimension's member count, including the
  `-1` unknown member where present) -- the per-dimension count closes the
  divergent-unknown-member gap the Edge Cases flag.
- **FR-008**: Only `profiles.example.yml` (placeholders, NO secrets, NO DSN, NO tokens)
  MAY be committed. The real `profiles.yml` MUST be git-ignored. No connection string,
  credential, or host MAY appear in any tracked file (Principle IX).
- **FR-009**: dbt MUST be DB-connected and NOT publish-capable: it stops at gold and MUST
  NOT materialize or publish a Power BI model (that is the parked F016 adapter, gated
  separately). The adapter category is F024 "Execution Adapter, DB-connected".
- **FR-010**: The auto-update policy MUST pin `dbt-core` + `dbt-postgres` TOGETHER:
  patch/minor versions open PRs; a major version requires named-human review; NO automerge
  for dbt minor or major until compatibility tests exist. The policy MUST be recorded in
  the adapter contract / decision record.
- **FR-011**: This slice MUST create NO dbt files and NO runtime code. The dbt project
  shape and the docs/decisions/templates/skill MUST be ENUMERATED as planned future outputs
  in plan.md / tasks.md, never written now (Principle VIII -- this slice is planning-only).
- **FR-012**: All generic artifacts (the two contract templates, the decision record, the
  skill) MUST be GENERIC: `retail_store_sales` is CITED as the filled first-MVP example,
  never inlined into a generic template (Principle VII).

### Key Entities *(include if feature involves data)*

- **dbt model**: a single transformation (staging / intermediate / mart) that materializes
  one table. It cites the approved map; it never authors meaning.
- **dbt model contract** (`templates/dbt-model-contract.md`, planned): the per-model record
  binding a model to its source-map citations, its grain, and the tests it carries.
- **dbt adapter contract** (`templates/dbt-adapter-contract.md`, planned): the
  feature-level contract stating the entry gate, the evidence-not-approval rule, the
  parity requirement, the no-secrets rule, and the auto-update policy.
- **Reconciliation parity test**: the assertion that a dbt mart reproduces the
  migration-built gold table (fact row count, `transaction_id` distinct count,
  additive-measure sums to the cent -- absolute delta `<= 0.01` per measure, and
  per-dimension distinct row counts). Its result is evidence; a human approves any
  build-path switch. After a switch it re-runs on every dbt build while the migration
  oracle is retained.
- **Readiness status** (`mappings/<table>/readiness-status.yaml`, F005, ADR 0004): where
  dbt run/test/parity evidence is recorded; Tower readiness + a named human own the stage
  status. dbt writes derived evidence, never truth.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader of the spec + planned contracts can state, unambiguously, that dbt
  may NOT run a model for any table whose Mapping Ready is not `pass`, with no exception.
- **SC-002**: The parity requirement is concrete: a reviewer can name the four assertions
  (fact row count, `transaction_id` distinct count, additive-measure sum to the cent --
  absolute delta `<= 0.01` per measure, and per-dimension distinct row counts) and the
  migration target (`gold.fct_sales_rss` for the worked example) the dbt mart must match
  before dbt can become a table's build path, and that the test re-runs on every dbt build
  while the migration oracle is retained.
- **SC-003**: There is NO path by which a green `dbt test` alone moves Silver Ready or Gold
  Ready to `pass`: every such transition cites dbt evidence PLUS a named human approval.
- **SC-004**: 100% of the planned generic artifacts contain ZERO `retail_store_sales` /
  C086 specifics; `retail_store_sales` appears only as a cited filled example (Principle
  VII).
- **SC-005**: This slice adds 0 dbt files and 0 lines of runtime code; the only files
  written are the five spec-kit planning artifacts (verifiable by the diff).
- **SC-006**: The no-secrets rule holds: a reviewer confirms only `profiles.example.yml`
  (placeholders) is planned for commit and `profiles.yml` is enumerated as git-ignored;
  no DSN/credential/host appears anywhere.
- **SC-007**: The auto-update policy is explicit: `dbt-core` + `dbt-postgres` pinned
  together, patch/minor -> PR, major -> human review, no automerge for minor/major until
  compatibility tests exist.

## Human approval boundary

- **The named human (table/data owner) approves** any move of Silver Ready or Gold Ready to
  `pass`, citing the dbt run/test/parity evidence. The agent + dbt recommend; the human
  decides.
- **The named human approves any build-path switch** (migrations -> dbt) for a table, only
  after the parity test passes. The agent never flips the default on its own. The switch
  RETAINS the table's migration files as the parity oracle/rollback; **retiring a retained
  migration is a separate later named-human decision**, never a side effect of the switch.
- **The named human resolves every Principle V judgment call** (grain ambiguity,
  sentinel-vs-null, PII publish-safety, business rollup/segment) the map does not already
  answer. dbt never auto-resolves one.
- **A named reviewer approves any dbt-core / dbt-postgres major (and, until compatibility
  tests exist, minor) version bump.**

## Allowed operations

- Read the approved `source-map.yaml` and `readiness-status.yaml` for a table (read truth).
- Once Mapping Ready = `pass`, run dbt staging/silver/gold models + `dbt test` (execute
  approved steps) against the DB.
- Run the reconciliation parity test comparing a dbt mart to the migration gold table.
- Write DERIVED evidence (dbt run/test/parity results, measured counts) into the readiness
  status `evidence[]` / `blocking_reasons[]`.
- Recommend a stage transition or a build-path switch for a named human to decide.

## Forbidden operations

- Running any dbt model for a table whose Mapping Ready is not `pass`.
- Defining source mapping, grain, PK, PII flags, or placement in a dbt model (authoring
  truth the map does not state).
- Defining metric contracts, business rollups, or segment mappings in a dbt model.
- Moving Silver Ready / Gold Ready to `pass` on a green `dbt test` alone (self-approval).
- Switching a table's default build path from migrations to dbt without a passing parity
  test AND a named human approval.
- Deleting or retiring a table's migration files as a side effect of a build-path switch
  (they MUST be retained as the parity oracle/rollback; retirement is a separate human call).
- Skipping the reconciliation parity re-run on a dbt build for a switched table whose
  migration oracle is still retained (the parity check is not one-time-at-switch).
- Silently changing the declared grain, or auto-resolving any Principle V judgment call.
- Publishing or materializing a Power BI model (that is F016, parked + gated separately).
- Committing `profiles.yml` or any DSN/credential/host/token in a tracked file.
- Automerging any dbt-core / dbt-postgres minor or major bump (and any major without a
  named-human review).
- Creating any dbt file or runtime code in THIS planning-only slice.

## Evidence required

- For a stage move to `pass`: the dbt run/test results (measured pass counts), the
  reconciliation parity result, AND the named human approval (owner + date).
- For a build-path switch: the passing parity result + the named human approval.
- For a blocked stage: the measured failing test/parity numbers as `blocking_reasons[]`.
- Each dbt model: its source-map citations (path + git ref + rows).

## Readiness stage affected

**Silver Ready** and **Gold Ready**. dbt builds the silver and gold tables; the parity
test feeds Gold Ready. dbt does NOT affect Source Ready, Mapping Ready (its entry gate),
Semantic Model Ready, Dashboard Ready, or Publish Ready.

## Dependencies

- **Upstream**: F024 (adapter taxonomy/category -- this is a DB-connected, not
  publish-capable Execution Adapter); F005 (readiness spine + status template); the
  approved `source-map.yaml` per table (Mapping Ready = `pass` is the entry gate);
  `warehouse/migrations` (the default build + the parity target). Principles III, IV, V,
  VII, VIII, IX.
- **Downstream**: F009 metric contracts bind to the gold columns dbt builds; F015
  reconciliation ledger may durably record the parity results over time. Neither is in
  scope here.

## Non-goals

- Implementing the dbt project, models, tests, macros, or skill (planning-only this slice).
- Replacing `warehouse/migrations` (dbt is an optional alternative; migrations stay default).
- Publishing or materializing Power BI (F016, parked + gated).
- A universal/other-engine transformation adapter (only dbt-core + dbt-postgres here).
- Defining numeric readiness scores (deferred; rule #9).

## Assumptions

- The DB is the same DigitalOcean Postgres the migrations target; dbt-postgres is the
  adapter. Auto-adopted default; recorded, reversible.
- Filled dbt models for the worked example live under the planned `dbt/models/` tree;
  generic templates live under `templates/`. Recorded in plan.md.
- The parity tolerance for additive money sums is exact to the cent (absolute delta
  `<= 0.01` per additive measure), since silver/gold use `NUMERIC(12,2)`; this is the
  stated default recorded in the adapter contract (clarified 2026-06-25), still
  human-confirmable when the adapter is built.
- Mapping Ready = `pass` is a precondition that already exists for the worked example
  (the migrations were built from an approved map).

## Deferred decisions

- (Resolved 2026-06-25) The parity tolerance is exact to the cent (absolute delta
  `<= 0.01` per additive measure) and dimension row counts ARE asserted beyond the fact
  (per-dimension distinct member counts). See FR-007 / SC-002. Still owner-confirmable at
  build time, but no longer an open default.
- Whether dbt incremental materialization is used for large facts (vs full refresh) --
  deferred to the build slice; does not change the gate or the parity rule.
- Whether the reconciliation ledger (F015) consumes the parity results durably -- a later
  integration, not this slice.

## See also

- `warehouse/migrations/0003_create_silver_retail_store_sales.sql`,
  `0004_create_gold_retail_store_sales_star.sql` (the parity target + the worked example).
- `docs/roadmap/roadmap.md` (the spine; F024-F033 are a forward batch, not yet recorded).
- F024 spec (adapter taxonomy/category) -- referenced by roadmap identity only.
- F005 readiness spine, F009 metric contracts, F016 (parked Power BI execution adapter).
- `.specify/memory/constitution.md` (Principles III, IV, V, VII, VIII, IX).
