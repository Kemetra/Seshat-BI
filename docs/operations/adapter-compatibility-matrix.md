# Adapter Compatibility Matrix -- the version-truth record the maintenance policy enforces against

- **Status:** Authored (the F032 enumerated deliverable; docs/templates, no runtime code).
- **Authority category:** Maintenance Automation  *(sub-axis: none / `--`)* -- per
  `docs/architecture/product-modules.md` (the five-category contract, F024 / on-disk spec 018).
  Maintenance Automation runs WITHOUT a per-invocation human trigger and emits ONLY derived
  evidence (this record); it never creates truth and never self-approves. It carries no
  Module capability level and no Adapter connectivity level -- those sub-vocabularies belong
  to the Product Module / Execution Adapter categories, not to this one.
- **Roadmap feature:** F032  **On-disk spec:** `specs/026-adapter-compatibility-matrix`.
  When the spec-dir number (026) and the roadmap F-number (F032) disagree, the F-number wins.
- **Readiness stage affected:** none directly (see the closing section).
- **The row template:** `templates/adapter-version-record.md` (the copy-me shape of one row).

## What this is

The kit pins a set of external adapters -- a dbt transformation adapter (F029), a Dagster
orchestration adapter (F030), and the parked Power BI execution adapter (F016) -- each of
which binds the kit to external tools (Python, Postgres, dbt-core, dbt-postgres, Dagster,
dagster-dbt, the Power BI PBIP/TMDL assumptions) whose versions move independently of the
kit. This matrix is the single, committed, reviewable answer to: "which version of each of
these is verified-compatible with this kit, and what smoke test proves it?"

For every adapter/dependency it carries one row: the SUPPORTED version RANGE, the NAMED
required smoke test, that test's last result (status), the LAST VERIFIED date, and the
NAMED OWNER who attested it. It is the version-truth the F031 maintenance policy reads and
enforces against. The matrix advances no readiness stage; it protects the kit's ability to
run the stages at all.

## The two boundaries (read first -- they are load-bearing)

### Record / policy boundary (F032 vs F031)

> F032 is the RECORD: what is verified-compatible (supported ranges + smoke-test status +
> last-verified dates + owners). F031 (Adapter Maintenance Policy) is the POLICY: what a
> dependency-update PR must DO about a violation, when to re-verify, and what to block.

This matrix carries NO PR gate, NO CI fail condition, NO merge block, NO enforcing check.
It does not gate a PR, block a merge, or fail a build. It states the version-truth; F031
reads it and decides what to do when a PR violates it. Putting enforcement logic into this
matrix is rejected -- that is the F031 lane.

### Record / build boundary (F032 vs F029 / F030 / F016)

> F032 RECORDS the supported versions of the F029 dbt adapter, the F030 Dagster adapter,
> and the F016 Power BI execution adapter. It MUST NOT author, modify, or execute any of
> those adapters' runtime code, connection logic, or transformations.

It NAMES the required smoke test and records its last result + date; it does NOT author or
run the smoke test, nor wire it into CI. The adapters own their own implementation; the
smoke tests are authored/run by the adapter features and a later automation slice. F032
names them and pins their version boundaries only.

## The status vocabulary (no fake confidence)

Status is recorded with EXACTLY the four readiness statuses from
`docs/readiness/readiness-model.md` PLUS `unknown` for the compatibility sense:

| Status | Meaning in this matrix |
|--------|------------------------|
| `not_started` | the adapter is named but its verification has not begun |
| `blocked` | a required artifact, smoke-test run, or attestation is missing -- see `blocking_reasons` |
| `warning` | verified with a non-fatal issue recorded (e.g. an accepted deviation) |
| `pass` | a named owner attested a PASSED smoke test; evidence = smoke-test result + run date + owner |
| `unknown` | untested: no smoke-test run, or an untested bound -- NEVER supported, NEVER inferred |

There is NO sixth status. `parked` is NOT a status value -- it is a NOTE recorded in a
row's `blocking_reasons[]` explaining WHY that row is `unknown` (the adapter is not yet
exercised). There is NO numeric / maturity / confidence score anywhere in this matrix, and
none may be added (hard rule #9 / Principle IX).

## The matrix

One row per adapter/dependency the kit pins. No named adapter may be absent. Every row
carries a version RANGE and a NAMED smoke test; a row missing either is a defect the review
catches. Every cell is either an explicit value or `unknown` -- a blank never implies
"fine". The values below are GENERIC placeholders (Principle VII): concrete version strings
in a real filled matrix are environment facts, not worked-example specifics, and a maintainer
fills them from attested evidence via `templates/adapter-version-record.md`.

| Adapter / dependency | Supported range | Required smoke test | Smoke-test status | Last verified | Owner |
|----------------------|-----------------|---------------------|-------------------|---------------|-------|
| Seshat BI Kit version | `>=<X>,<<Y>` | `<kit-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| Python version | `>=<X>,<<Y>` | `<python-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| Postgres version | `>=<X>,<<Y>` | `<postgres-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| dbt-core version/range | `>=<X>,<<Y>` | `<dbt-core-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| dbt-postgres version/range | `>=<X>,<<Y>` | `<dbt-postgres-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| Dagster version/range | `>=<X>,<<Y>` | `<dagster-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| dagster-dbt version/range (row retired: removed from the orchestration environment by the spec-135 owner decision, 2026-07-17 -- excluded dbt-core 1.12, sat on no execution path) | `removed` | `n/a` | `removed` | `2026-07-17` | `Ahmed Shaaban` |
| Power BI PBIP/TMDL assumptions | `<assumed PBIP/TMDL shape; floor tested, ceiling unknown>` | `<pbip-tmdl-smoke>` | `<status>` | `<YYYY-MM-DD \| unknown>` | `<named owner \| UNASSIGNED>` |
| Power BI MCP adapter status (F016, parked) | `<unknown -- not yet exercised>` | `<pbi-mcp-smoke>` | `unknown` | `unknown` | `UNASSIGNED` |

### Feature 133 dbt candidate verification (derived evidence only)

This candidate record does not replace the named-owner attestation required by
the matrix. The agent ran the reproducible checks and records their derived
outcome; it does not self-promote the adapter to supported.

| Candidate | Exact version | Derived check | Status | Verified | Owner |
|---|---|---|---|---|---|
| Python | `3.13.12` | editable `.[dev,dbt]` install | `blocked` | `2026-07-16` | `UNASSIGNED` |
| dbt Core | `1.12.0` | governed parse/list and repeated `seshat dbt plan` | `blocked` | `2026-07-16` | `UNASSIGNED` |
| dbt Postgres | `1.10.2` | adapter load plus manifest v12 parse | `blocked` | `2026-07-16` | `UNASSIGNED` |

Derived evidence:

- exact optional dependency resolution succeeded on Python 3.13.12;
- `dbt parse` emitted manifest schema v12 with 8 governed models and 24 tests;
- the sanitized fixture is
  `tests/fixtures/dbt_artifacts/manifest-pinned-v12.json`;
- repeated planning kept the semantic graph fingerprint and plan digest stable
  while dbt's raw manifest checksum changed with invocation metadata;
- strict fixture readers accept manifest v12 and run-results v6;
- `tests/live_db/test_dbt_retail_store_sales.py` now defines one-container matching
  parity plus fact-row, business-key, money-total, and dimension-member divergence
  proofs through the real `seshat dbt` CLI and a temporary local Git clone;
- the existing mocked precondition suite remains green (8 tests), and the new live
  module self-skipped with the explicit `[PENDING LIVE PROFILE]` reason.

`blocking_reasons[]`:

- `[PENDING LIVE PROFILE]` -- `dbt compile` opens a Postgres connection for
  this graph even with `--no-introspect`; no DSN was available;
- `[PENDING LIVE PROFILE]` -- Docker is not installed/on `PATH` and the isolated
  environment does not contain the `livetest` extra, so the ephemeral-Postgres
  proof did not execute and is not counted as a live pass;
- live build/test/parity and run-results v6 production are not yet verified;
- a named compatibility owner has not attested the candidate rows.

Enable the disposable proof by installing Docker Desktop with its Linux engine,
installing `.[db,dbt,livetest]`, and rerunning
`python -m pytest tests/live_db/test_dbt_retail_store_sales.py -m live_db -v`.
For an operator-provided database, put only `SESHAT_DBT_*` values in the gitignored
`.env` and rerun compile/live parity. Until then, these rows remain `blocked`, not
`pass`.

### Per-row evidence and blocking reasons

Each row's `evidence[]` (for a `pass`) and `blocking_reasons[]` (for `blocked` / `unknown`)
live in its `templates/adapter-version-record.md` copy. The load-bearing fixed entries:

- **Power BI MCP adapter status (F016):** status `unknown`; `blocking_reasons[]` records
  the note "adapter parked, not yet exercised -> unknown (parked is a note, not a status)".
  It is NOT marked supported and is NOT omitted. `pbi-cli` is no longer the preferred path
  -- the official Power BI MCP / connection is the preferred future adapter, and this matrix
  tracks its STATUS, not its implementation (record/build boundary).
- **Any row with an untested ceiling:** the range states the tested floor and marks the
  ceiling `unknown`; `blocking_reasons[]` records "upper bound untested -> ceiling unknown,
  not assumed compatible". Newer-is-fine is never assumed.
- **Any row whose smoke test has not run:** status `unknown`; `blocking_reasons[]` records
  "smoke test not run -> unknown". A named-but-unrun smoke test does not make a version
  supported.
- **Any attested row missing an owner:** the owner cell reads `UNASSIGNED` and the row is
  flagged; a supported status requires a named attesting owner.

## The rules

- **UNKNOWN is never compatible.** An untested version, an unverified range, or a cell with
  no smoke-test evidence is recorded `unknown` -- NEVER as supported, NEVER as `pass`, NEVER
  inferred from "it probably works". This is hard rule #9 / Principle IX, instantiated for
  this matrix. If asked to "just mark it compatible", the matrix declines, records `unknown`,
  and records the missing smoke-test run as the blocker.
- **Range required.** Every adapter row carries a version RANGE (a floor and, where tested,
  a ceiling), not a single bare pinned point with the rest left implicit. An untested bound
  is `unknown`, never assumed.
- **Smoke test required.** Every adapter row names its required smoke test. A row with no
  smoke test is a defect. F032 names the smoke test and records its last result; it does NOT
  author or run it.
- **No numeric score.** The matrix records explicit status + evidence (smoke-test result +
  last-verified date + owner) only. A numeric / maturity / confidence score is forbidden.
- **Owner attests to promote.** A row reaches a SUPPORTED status ONLY with a named owner
  attesting a PASSED smoke test, recorded as evidence (owner + run date). The agent
  RECOMMENDS and RECORDS; the named owner DECIDES and ATTESTS. The agent never self-attests
  as owner and never self-promotes a cell to supported (Principle V posture).
- **The judgment call here is narrow.** The classic data judgment calls (grain / PII /
  business rollup) are N/A for a version record -- they are not fake-fitted. The only
  judgment call is "is this version verified by a passed smoke test?".

## How F031 reads this matrix

F031 (the Adapter Maintenance Policy) reads this matrix as its source of version-truth and
enforces against it:

- A dependency-update PR that changes a supported version MUST update the matrix. F032 states
  the matrix is the record that such a PR updates; ENFORCING that requirement -- failing the
  PR, requiring re-verification, blocking the merge -- is F031's policy. F032 does not gate
  the PR itself.
- When a PR bumps a tool past the recorded supported range, the matrix RECORD shows the bump
  now sits outside the verified range; deciding what the PR must do about it (re-verify,
  block, accept) is F031, not F032.
- When a transitive dependency moves but a direct adapter version is unchanged, the matrix
  does not silently keep `pass` for an unverified state -- a broken smoke test flips that
  adapter's status to `blocked` / `unknown` at next verification.

## Readiness stage affected

**None directly.** F032 advances no stage of the readiness spine (Source -> Mapping ->
Silver -> Gold -> Semantic Model -> Dashboard -> Publish). It is a Maintenance Automation
record (per the F024 category) that protects the kit's durability -- its ability to run the
stages at all -- rather than gating any single stage. This is stated plainly rather than
force-fitting a spine stage.

## See also

- The per-row template (copy-me): `templates/adapter-version-record.md`.
- The policy half of the pair (enforces against this record): F031 Adapter Maintenance
  Policy, `specs/025-adapter-maintenance-policy/`.
- The category home (Maintenance Automation): F024 Companion Tools Architecture,
  `docs/architecture/product-modules.md`, `docs/architecture/core-vs-modules-and-adapters.md`,
  `specs/018-companion-tools-architecture/`.
- The four-status vocabulary + no-fake-confidence rule: `docs/readiness/readiness-model.md`.
- The tracked adapters (recorded here, NOT built here): F029 (dbt) `specs/023-dbt-transformation-adapter/`,
  F030 (Dagster) `specs/024-dagster-orchestration-adapter/`, F016 (Power BI execution adapter).
- The roadmap row + hard rules 7/8/9: `docs/roadmap/roadmap.md` (F032).
- The constitution: `.specify/memory/constitution.md` (Principles V, VII, VIII, IX).
- The spec: `specs/026-adapter-compatibility-matrix/spec.md`.
