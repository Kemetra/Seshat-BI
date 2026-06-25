# Feature Specification: Adapter Maintenance and Auto-Update Policy -- how dependencies and adapters are updated safely without ever bypassing a readiness gate

**Feature Branch**: `025-adapter-maintenance-policy`  **Roadmap feature**: F031

> Numbering note (spec-dir vs roadmap F-number). The roadmap F-number is the
> authoritative feature identity. The spec *directory* number is the next free
> on-disk slot when drafted, so the two can differ. This feature is roadmap
> **F031**, drafted into spec directory **025**. When the directory number and the
> F-number disagree, the roadmap F-number wins. F031 is part of a planning batch
> ahead of the committed roadmap ledger (which currently records F005-F016); this
> spec does not imply F031 is already in that ledger.

**Created**: 2026-06-25   **Status**: Planned (spec only -- no runtime code, no CI config, no policy docs this slice)

**Input**: "Define how dependencies and adapters are updated safely. Updates are PR-based; low-risk dev dependencies may automerge ONLY with green CI; dbt/Dagster/Power BI adapter updates require human review; major versions require an explicit compatibility review; no update may bypass a readiness gate; no update may introduce secrets or local paths. Encode three update lanes (A allowed-auto, B human-review-required, C never-automerge) and the required checks every update PR must pass. Category (per F024): Maintenance Automation. Readiness stage affected: none directly -- it protects ALL stages from update drift."

## Why this feature exists

The kit is built on a deliberate Constitution Principle II ("Depend, Never Fork"):
the opinion lives in this repo, the engine is borrowed and independently
upgradeable, and there must be no "fork tax". That principle is only true in
practice if there is a SAFE, repeatable way to take an upstream upgrade. Without a
written policy, every dependency bump is an ad-hoc judgment call: a dev tool patch
and a major Postgres driver change and a Power BI execution-adapter upgrade all flow
through the same undisciplined door, and the easiest path -- "merge it, tests are
green" -- is exactly the path that can silently regress a gate, strand the repo on a
snapshot, or pull a transitive secret/local-path into a tracked file.

This feature is the policy that makes Principle II operational: it classifies every
update into one of three lanes by blast radius, fixes the checks an update PR must
pass before it can merge, and states the one invariant that keeps the whole thing
inside the Constitution -- **no update in any lane may bypass a readiness gate or
move any stage to `pass`.** It is the maintenance discipline that lets the kit stay
current on its borrowed engines (dbt, Dagster, the Power BI execution adapter, the
Postgres driver, the dev toolchain) without ever letting an upgrade become a quiet
change to truth.

## What this feature is NOT (the scope wall)

This is the load-bearing constraint, stated up front so the spec cannot drift:

- **It writes NO policy doc, NO CI config, and NO runtime code THIS slice.** The
  deliverables (`docs/operations/dependency-update-policy.md`,
  `docs/operations/adapter-update-policy.md`,
  `docs/decisions/0009-safe-auto-updates.md`, and the OPTIONAL planned
  `.github/dependabot.yml` / `renovate.json`) are FUTURE outputs this spec
  ENUMERATES. This slice authors only the five Spec-Kit planning files.
- **Automerge lives entirely BELOW the readiness spine.** This is the resolution of
  the apparent tension with "no tool self-approves" (Principle V / Core Authority).
  Automerging a low-risk dev-tool bump on green CI is a mechanical change in the
  dependency/CI plane only: it does NOT define business meaning, approve a metric or
  mapping, publish Power BI, or move any readiness stage to `pass`. The lanes ARE
  the encoding of where human judgment is mandatory (Lane B always; Lane C never
  automerge) versus where green gates suffice (Lane A). No automerge, in ANY lane,
  may touch the readiness spine.
- **No update may bypass a readiness gate.** An update that could regress a gate
  (silver/gold build, semantic-model checks, `retail check`, `retail validate`) must
  RE-PASS the gates it could affect before merge. It never auto-promotes a stage and
  never clears a blocker.
- **No update may introduce a secret, a credential, a DSN/token, or a local machine
  path** into a tracked file (Principle IX). This is a hard required check, not a
  best-effort one.
- **Generic.** No worked-example specifics. C086 / `retail_store_sales` are filled
  examples cited as references, never baked into this policy (Principle VII). The
  policy uses placeholders such as `<adapter>`, `<dependency>`, `<lane>`.
- **No fake confidence.** This policy emits no health/maturity/confidence score for a
  dependency. An update PR carries explicit check results (pass/fail per required
  check) and explicit lane + reviewer evidence, never a fabricated number (hard rule
  #9). A maturity score is OPTIONAL and DEFERRED.

## Relationship to shipped features (scope delta)

This feature governs HOW the kit's borrowed engines and toolchain are upgraded; it
does not re-spec any of them.

- **F024 Companion Tools Architecture (spec 018)** -- defines the "Maintenance
  Automation" category this feature belongs to. F031 DEPENDS on F024; it is one
  instance of that category, not a redefinition of it.
- **F029 dbt Transformation Adapter (spec 023)** and **F030 Dagster Orchestration
  Adapter (spec 024)** -- the medallion-build and orchestration engines. Their
  dependency updates (`dbt-core`, `dbt-postgres`, `dagster`, `dagster-dbt`) are
  governed here as **Lane B** (human review required). This feature does not define
  what those adapters do; it defines how they are upgraded.
- **F016 Power BI Execution Adapter (parked)** -- the execution-only, publish-capable
  adapter. Its updates are governed here as **Lane C** (never automerge). This
  feature adds no execution behavior; it only constrains how that adapter is bumped.
- **F032 Adapter Compatibility Matrix (spec 026)** -- this feature PAIRS with F032:
  a major-version update (Lane B/C) triggers an explicit compatibility review, and
  the recorded result lives in F032's matrix. F031 routes the trigger; F032 owns the
  durable compatibility record.
- **The static gate `retail check` and the live gate `retail validate`** -- this
  feature consumes them as required checks for an update PR; it adds no rule and no
  validator to either (no scope bleed into the gate definitions).

## Architecture (planning posture: policy docs + one ADR + optional planned config)

Consistent with the docs-first features (010, 013): this slice is **planning text
only**. The future shape this spec PLANS is:

- Two operations docs under a new `docs/operations/` home: a
  **dependency-update-policy** (the lanes + required checks for the toolchain and
  drivers) and an **adapter-update-policy** (the lanes + compatibility-review trigger
  for the dbt / Dagster / Power BI execution adapters specifically).
- One ADR, **`docs/decisions/0009-safe-auto-updates.md`**, recording the decision
  "automerge is allowed for Lane A on green CI and lives below the readiness spine;
  Lane B requires human review; Lane C never automerges" with its alternatives and
  rationale. (ADR numbers 0007/0008 are claimed by sibling features in this batch;
  0009 is this feature's, named here, created later.)
- OPTIONAL planned config (`.github/dependabot.yml` or `renovate.json`) that ENCODES
  the lanes as bot rules -- planned, not created, and itself subject to the policy.

The runtime is the existing CI workflow (`.github/workflows/ci.yml`, which already
runs ruff format check, ruff lint, `pytest -m unit`, and `retail check`) plus a
human reviewer. This feature defines the policy those runtimes enforce; it builds no
new runtime.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every update is classified into a lane before it can merge (Priority: P1)

A maintainer (or an update bot) opens a PR that bumps a dependency, a GitHub Action,
or an adapter. The policy classifies the change into exactly one lane -- A
(allowed-auto), B (human-review-required), or C (never-automerge) -- by what the
change can affect, and the lane determines whether a human review is mandatory.

**Why this priority**: lane classification is the feature -- without it, blast radius
is undefined and the "merge on green" shortcut applies uniformly, which is exactly
the unsafe default. This is the spine of the policy.

**Independent Test**: given a set of representative update PRs (a Ruff patch bump, a
GitHub Action minor bump, a `dbt-core` minor bump, a `psycopg2` change, a major DB
driver bump, a Power BI execution-adapter bump), the policy assigns each to exactly
one lane per the lane table, and only Lane A items are eligible for automerge. No PR
is unclassified; no Lane B/C item is automerge-eligible.

**Acceptance Scenarios**:

1. **Given** a Ruff / Pytest / pre-commit / docs-tooling / GitHub Actions
   patch-or-minor bump, **When** the policy classifies it, **Then** it is Lane A and
   eligible for automerge ONLY if every required check is green.
2. **Given** a `dbt-core` / `dbt-postgres` / `dagster` / `dagster-dbt` / `psycopg2` /
   Postgres-driver / Power BI modeling-utility update, **When** the policy classifies
   it, **Then** it is Lane B and a named human review is required before merge --
   automerge is forbidden.
3. **Given** an update to the official Power BI MCP / execution adapter, anything
   publish-capable, a major DB-driver change, anything touching credentials/auth, or
   anything that changes semantic-model behavior, **When** the policy classifies it,
   **Then** it is Lane C and may NEVER automerge under any condition.

### User Story 2 - An update PR merges only when all required checks are green (Priority: P1)

For any update PR in any lane, a fixed set of required checks must pass before merge.
Lane A may automerge when they are all green; Lane B/C require the same green checks
PLUS the lane's mandatory human review. A red check blocks the merge regardless of
lane.

**Why this priority**: the lanes decide WHO must approve; the required checks decide
WHETHER it is safe at all. Without enforced checks, even a correctly classified Lane
A bump could regress a gate. This is the safety half of the policy.

**Independent Test**: given an update PR with one required check failing (e.g.
`retail check` non-zero, or a secret-scan hit), the policy blocks merge -- including
Lane A automerge -- and records which check failed; given the same PR with all
required checks green and (for Lane B/C) a named reviewer recorded, the policy allows
merge.

**Acceptance Scenarios**:

1. **Given** any update PR, **When** it is evaluated, **Then** the required checks are
   exactly: ruff format check, ruff lint, `pytest -m unit`, `retail check`,
   `retail validate` fixture mode (if available), semantic check fixture mode (if
   available), dbt compile/build smoke (once dbt exists), Dagster definitions-load
   smoke (once Dagster exists), no-secrets scan, no-raw-data scan, and a recorded
   dependency-invariants note -- and ALL must pass.
2. **Given** a Lane A PR with every required check green, **When** automerge is
   evaluated, **Then** it may merge with no human in the loop (the bump is in the
   dependency/CI plane, below the readiness spine).
3. **Given** any PR with a failing required check, **When** merge is evaluated,
   **Then** merge is blocked, the failing check is named in the PR, and no lane can
   override it.

### User Story 3 - A major-version or adapter update triggers an explicit compatibility review (Priority: P2)

A major-version bump (Lane B/C), or any adapter update, triggers an explicit
compatibility review whose result is recorded -- and which hands the durable
compatibility record to F032. The review is a named human's decision; the policy
routes the trigger and records the evidence, it does not self-decide compatibility.

**Why this priority**: major versions are where the silent regression and the
fork-tax risk concentrate. A patch bump rarely changes behavior; a major bump can
change the adapter's contract with the gates. Routing this to a human review (and to
F032's matrix) is what keeps Principle II's "no fork tax, no stranding" promise.

**Independent Test**: given a major-version bump of an adapter, the policy marks it
Lane B or C, requires an explicit compatibility-review record (which gates the PR
could regress, who reviewed, the outcome), and references F032 as the home of the
durable matrix entry. The policy never records a compatibility verdict on its own.

**Acceptance Scenarios**:

1. **Given** a major-version bump of `dbt-core` (Lane B), **When** the policy
   evaluates it, **Then** it requires an explicit compatibility review naming the
   gates it could regress and a named reviewer, and points the durable record to
   F032's compatibility matrix.
2. **Given** a Power BI execution-adapter update (Lane C), **When** the policy
   evaluates it, **Then** it requires the compatibility review AND records that
   automerge is forbidden under any check state.
3. **Given** any compatibility review, **When** the policy runs, **Then** it routes
   the trigger and records the evidence, but the compatibility verdict is the named
   reviewer's -- the policy makes no self-verdict (Principle V).

### Edge Cases

- **A Lane A bump pulls a Lane B/C transitive change** (e.g. a "dev tool" update that
  bumps a publish-capable or driver dependency transitively): the change is
  RECLASSIFIED upward to the highest lane any affected package falls in -- the
  highest blast radius wins. A Lane A label never shields a Lane C effect.
- **A required check is unavailable** (e.g. `retail validate` fixture mode or dbt
  smoke before that adapter exists): the policy marks that check "not applicable yet"
  with a reason; it does NOT silently treat a missing check as passed, and it does
  NOT let its absence unblock a merge that another required check is blocking.
- **An update would change a readiness gate's behavior** (e.g. a `retail check` rule
  dependency, a validator library): it is at minimum Lane B, the affected gate must
  re-pass, and the PR must state which gate it touches. No such update is Lane A.
- **A secret / DSN / token / local path appears in the diff** (often via a lockfile
  or a vendored sample): the no-secrets / no-paths check fails the PR in every lane;
  per the security rule, STOP, do not merge, and sweep for similar (Principle IX).
- **The update bot proposes a change with no green CI** (CI broken for an unrelated
  reason): no automerge -- Lane A automerge is conditional on ALL required checks
  green, so a red or absent CI run blocks it.
- **A force-merge / gate-skip is attempted** (`--no-verify`, admin override,
  force-push): forbidden by this policy as by the global git rules; an update that
  cannot pass the gates does not merge.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The policy MUST define exactly three update lanes and classify every
  update PR into exactly one: **Lane A (allowed auto PR, automerge-eligible later if
  all required checks pass)** -- Ruff, Pytest, pre-commit/dev tools, GitHub Actions
  patch/minor, docs tooling; **Lane B (PR required, human review required)** --
  `dbt-core`, `dbt-postgres`, `dagster`, `dagster-dbt`, `psycopg2`, Postgres-driver
  changes, Power BI modeling utilities; **Lane C (never automerge)** -- the official
  Power BI MCP / execution adapter, anything publish-capable, major DB-driver
  changes, anything touching credentials/auth, anything that changes semantic-model
  behavior.
- **FR-002**: All updates MUST be PR-based. No update may be applied by direct push
  to a protected branch, and no update may use `--no-verify` or any gate-skip.
- **FR-003**: Automerge MUST be restricted to Lane A and MUST be conditional on ALL
  required checks being green. Lane B and Lane C MUST NEVER automerge.
- **FR-004**: The policy MUST fix the required checks for ANY update PR: ruff format
  check, ruff lint, `pytest -m unit`, `retail check`, `retail validate` fixture mode
  (if available), semantic check fixture mode (if available), dbt compile/build smoke
  (once dbt exists), Dagster definitions-load smoke (once Dagster exists), a
  no-secrets scan, a no-raw-data scan, and a recorded dependency-invariants note. All
  required checks MUST pass before merge.
- **FR-005**: The policy MUST state the invariant that NO update in ANY lane may
  bypass a readiness gate or move any readiness stage to `pass`. An update that could
  regress a gate MUST re-pass that gate before merge; automerge lives below the
  readiness spine and never touches it.
- **FR-006**: The policy MUST forbid any update from introducing a secret, credential,
  DSN, token, or local machine path into a tracked file; the no-secrets / no-paths
  check is a hard merge blocker in every lane (Principle IX).
- **FR-007**: A major-version bump MUST require an explicit compatibility review --
  naming the gates it could regress, the named reviewer, and the outcome -- and MUST
  reference F032 (spec 026) as the home of the durable compatibility-matrix entry.
  The policy routes the trigger and records the evidence; the verdict is the human's.
- **FR-008**: The transitive-escalation rule MUST hold: if a lower-lane update pulls a
  higher-lane change (transitively or via lockfile), the PR is reclassified to the
  highest affected lane -- highest blast radius wins. A Lane A label never shields a
  Lane B/C effect.
- **FR-009**: A required check that does not yet exist (e.g. dbt smoke before dbt
  exists) MUST be marked "not applicable yet (<reason>)", never silently treated as
  passed, and its absence MUST NOT unblock a merge another required check is blocking.
- **FR-010**: The policy MUST emit NO health/maturity/confidence score for a
  dependency or adapter. An update's status is the explicit per-check pass/fail plus
  the lane and the named reviewer (for B/C) -- never a fabricated number (hard rule
  #9). Any maturity score is DEFERRED.
- **FR-011**: The policy MUST be generic: lanes and checks are stated with placeholders
  (`<adapter>`, `<dependency>`, `<lane>`); concrete package names appear only as the
  lane-membership examples enumerated in FR-001, with no worked-example (C086 /
  `retail_store_sales`) specifics (Principle VII).
- **FR-012**: The OPTIONAL planned config (`.github/dependabot.yml` / `renovate.json`)
  MUST, if later created, ENCODE these lanes (Lane A auto-eligible, Lane B/C
  review-required) and is itself subject to this policy. It is PLANNED, not created in
  this slice.

### Key Entities

- **Update lane** (A / B / C): the classification of an update by blast radius;
  determines automerge eligibility and whether a named human review is mandatory.
- **Update PR**: the only allowed unit of update; carries a lane label, the required
  checks' results, and (for B/C) the named reviewer + compatibility-review record.
- **Required check**: a named gate an update PR must pass (ruff format, ruff lint,
  `pytest -m unit`, `retail check`, `retail validate` fixture, semantic check fixture,
  dbt smoke, Dagster smoke, no-secrets, no-raw-data, dependency-invariants note).
- **Compatibility review**: the explicit, named-human evaluation triggered by a
  major-version or adapter update; its durable record lives in F032's matrix.
- **Governed adapters (existing/planned, unchanged here)**: the dbt adapter (F029),
  the Dagster adapter (F030), and the Power BI execution adapter (F016). INPUTS to
  the policy; this feature redefines none of them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The two planned operations docs and the ADR are FULLY enumerated in
  plan.md's "Repository artifacts this feature PLANS (not created)" list with their
  exact paths; zero of them are created in this slice (the slice ships only the five
  Spec-Kit files).
- **SC-002**: The lane table is total and unambiguous: each example package class in
  FR-001 maps to exactly one lane, and a reviewer can classify any of the six
  representative update PRs (US1 independent test) with no tie and no gap.
- **SC-003**: The required-checks list is exact and enforceable: every check is either
  already in `.github/workflows/ci.yml` (ruff format, ruff lint, `pytest -m unit`,
  `retail check`) or marked "once that adapter exists / if available", and a PR with
  any required check red is provably non-mergeable in every lane.
- **SC-004**: The no-bypass invariant is provable: the policy text states, and the
  governance checklist verifies, that no lane (including Lane A automerge) can move a
  readiness stage to `pass`, clear a blocker, or skip a gate -- automerge is confined
  to the dependency/CI plane.
- **SC-005**: A request for a "dependency health score" is DECLINED with the
  no-fake-confidence rationale; the artifacts carry explicit per-check pass/fail +
  lane + reviewer evidence only, and contain no C086 / `retail_store_sales` specifics.

## Human approval boundary

- **Lane A**: no human approval required to merge IF all required checks are green
  (mechanical bump below the readiness spine).
- **Lane B**: a NAMED human reviewer MUST approve before merge; green checks are
  necessary but not sufficient.
- **Lane C**: a NAMED human reviewer MUST approve AND automerge is forbidden under any
  check state.
- **Any lane**: moving a readiness stage, clearing a blocker, approving a metric /
  mapping / PII publish, or publishing Power BI remains the named human owner's
  decision via the existing gates -- an update PR can never do any of these.

## Allowed operations

- Classify an update into a lane by its blast radius (read-only analysis of the diff,
  the changed packages, and their transitive effects).
- For Lane A on green CI: automerge the dependency/CI-plane bump.
- Run the required checks and record their pass/fail per PR.
- Route a major-version / adapter update to a human compatibility review and record
  the evidence (gates affected, reviewer, outcome) -- with the durable record in F032.
- Enumerate the lanes as bot rules in the OPTIONAL planned config (future slice).
- Re-run the readiness gates an update could regress and require them to re-pass.

## Forbidden operations

- Automerging any Lane B or Lane C update, or any update with a red/absent required
  check.
- Bypassing, skipping, or weakening any readiness gate (`retail check`,
  `retail validate`, silver/gold build, semantic-model checks) via an update.
- Moving any readiness stage to `pass`, clearing a blocker, or self-approving --
  through an update PR or its automerge (Core Authority owns truth).
- Introducing a secret, credential, DSN, token, or local machine path into a tracked
  file via any update.
- Self-deciding a compatibility verdict for a major-version / adapter update
  (Principle V): the policy routes and records; the human decides.
- Emitting a dependency/adapter health/maturity/confidence score (hard rule #9).
- Forking, vendoring, or re-implementing an adapter to take an update (Principle II:
  depend, never fork -- no fork tax).
- `--no-verify`, gate-skip, admin force-merge, or force-push to a protected branch.

## Evidence required

- **Lane label** on every update PR, with the transitive-escalation rule applied.
- **Required-checks results**: explicit pass/fail for each required check, with
  "not applicable yet (<reason>)" for any check that does not yet exist.
- **No-secrets / no-raw-data / no-local-paths** scan result (a hard blocker if red).
- **Dependency-invariants note**: the documented invariants the update must preserve
  (e.g. gold-only read surface, no new runtime dependency unless intended).
- **For Lane B/C**: the named reviewer and approval.
- **For a major-version / adapter update**: the compatibility-review record (gates
  affected, reviewer, outcome) with its durable entry referenced in F032's matrix.

## Readiness stage affected

**None directly.** This policy advances no single readiness stage. It is
cross-cutting: it PROTECTS all seven stages (Source -> Mapping -> Silver -> Gold ->
Semantic Model -> Dashboard -> Publish Ready) from update drift, by requiring that
any update which could regress a gate re-pass that gate before merge, and by
forbidding any update from moving a stage to `pass`. (Mirrors F012's "all stages"
cross-cutting framing.)

## Dependencies

- **F024 Companion Tools Architecture (spec 018)** -- defines the "Maintenance
  Automation" category this feature instantiates. Hard dependency.
- **F029 dbt Transformation Adapter (spec 023)** and **F030 Dagster Orchestration
  Adapter (spec 024)** -- the Lane B adapters whose updates this governs.
- **F016 Power BI Execution Adapter (parked)** -- the Lane C adapter whose updates
  this governs.
- **F032 Adapter Compatibility Matrix (spec 026)** -- the paired feature that owns the
  durable compatibility record a major-version review produces.
- The existing CI workflow (`.github/workflows/ci.yml`) and the static/live gates
  (`retail check`, `retail validate`) as the required-check runtimes.

## Non-goals

- Implementing the bot config (`.github/dependabot.yml` / `renovate.json`) -- planned,
  not built.
- Adding any `retail check` rule, validator, or CLI subcommand.
- Defining adapter behavior (owned by F016 / F029 / F030).
- Building a dependency dashboard or a maturity/health score (deferred; see F033 /
  hard rule #9).
- Automating the human review or the compatibility verdict (Principle V keeps both
  with a named human).

## Assumptions

- Policy docs + one ADR + optional planned config; the runtime is the existing CI
  plus a human reviewer. No new runtime is built (same posture as 010/013).
- The required checks already partly exist in CI (ruff format, ruff lint,
  `pytest -m unit`, `retail check`); the dbt/Dagster/fixture-mode checks become
  applicable only once those adapters/modes exist, and are marked so until then.
- Branch protection and a no-`--no-verify` rule are in force (global git rules); this
  policy assumes, not re-establishes, them.
- F032 exists (or will) to hold the durable compatibility-matrix record; this feature
  references it rather than duplicating that store.

## Deferred decisions (recorded, not built)

- **The concrete bot config** (`.github/dependabot.yml` vs `renovate.json`, grouping
  rules, schedule): DEFERRED to the implementation slice; this spec fixes only that it
  must encode the lanes.
- **A dependency maturity/health score**: DEFERRED (hard rule #9; aligns with the
  release-maturity feature F033). Until scoring rules exist, status is explicit
  checks + lane + reviewer only.
- **Auto-applying low-risk security patches faster than the normal cadence**:
  DEFERRED; any such expedited lane is still bound by the no-bypass invariant and the
  required checks.

## See also

- The principle this operationalizes: Constitution Principle II ("Depend, Never
  Fork") and Principle IX ("Secrets and Reproducibility");
  `.specify/memory/constitution.md`.
- The category: F024 (spec 018, Companion Tools Architecture).
- The governed adapters: F029 (spec 023, dbt), F030 (spec 024, Dagster), F016 (parked
  Power BI execution adapter).
- The paired compatibility store: F032 (spec 026, Adapter Compatibility Matrix).
- The required-check runtimes: `.github/workflows/ci.yml`; the `retail-govern` /
  `retail check` static surface and the `retail-validate` / `retail validate` live
  surface.
- The cross-cutting "all stages" framing: F012 (spec 013, Data Quality Control Room).
- The future deliverables this spec enumerates: `docs/operations/dependency-update-policy.md`,
  `docs/operations/adapter-update-policy.md`, `docs/decisions/0009-safe-auto-updates.md`,
  and the optional planned `.github/dependabot.yml` / `renovate.json`.
