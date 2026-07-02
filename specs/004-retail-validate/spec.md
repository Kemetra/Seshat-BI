# Feature Specification: retail validate -- the live-validator surface

**Feature Branch**: `004-retail-validate` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Build the deferred `retail validate` live-validator surface: the four checks that need a running DB (PK uniqueness RC2, date-dim coverage RC15-live, 0 orphan FKs RC16, penny-exact cross-layer reconciliation RC16). Driver-free check logic + a lazy psycopg2 connection seam; reuse Finding/Severity; ERROR severity (proven defects). Fixture-tested this slice; the live run against the real DB is deferred."

## Why this feature exists

The static checker (`retail check`, 26 rules) proves everything provable from committed text.
But four ADR defaults can only be proven against **materialized data** -- the compliance
matrix Sec 8 and constitution Principle VIII name them as the deferred **`retail validate`**
live surface. This feature builds that surface. It is the live complement to the static core:
e.g. S7 proves `dim_date` is *built from* `generate_series` (pattern); `retail validate` proves
the calendar *actually spans* every real `sale_date` (coverage) -- complementary halves of RC15.

**Severity asymmetry (intentional, stated):** static rules are WARNING (suspect patterns; ADR
"override when" clauses). Live checks prove **actual defects** -- a real orphan FK, a real PK
duplicate, a real penny mismatch -- and RC16 says "assert 0 orphans before declaring done." So
live findings are **ERROR**. Suspect -> WARN; proven -> ERROR.

## The four live checks

| Check | ADR | Proves (on materialized rows) |
|-------|-----|-------------------------------|
| PK uniqueness | RC2 | row count == distinct-PK count, 0 NULL PK on the transformed table |
| Date coverage | RC15 (live half) | the generated calendar spans every real fact date; 0 dates missing |
| Orphan FKs | RC16 | 0 fact rows whose FK has no matching dim row (beyond the -1 member) |
| Cross-layer reconciliation | RC16 | each measure total matches source -> silver -> gold to the penny |

## Architecture (the seam that keeps the static core stdlib-only)

- **Driver-free logic** lives in `src/retail/validate.py`: the four checks are pure functions
  over a **`QueryRunner` Protocol** (`run(sql, params) -> list[tuple]`), returning `Finding`s
  (reused from `core.py`). No `import psycopg2` anywhere in this module or its import path.
- **The connection seam** (`import psycopg2`, read `.env`/doctl, build a real `QueryRunner`)
  is imported **lazily inside the `validate` subcommand handler** -- never at `cli.py` module
  scope. So `retail check` (and CI, which installs no driver) never imports the driver.
- **psycopg2 is an optional-dependency extra** (`[project.optional-dependencies] db`), NOT a
  core or dev dependency. The static core keeps `dependencies = []`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live checks are driver-free and fixture-testable (Priority: P1)

The four checks run against any object implementing the `QueryRunner` Protocol, so they are
fully unit-testable with a tiny fake runner -- no database, no driver.

**Why this priority**: this is the architectural keystone -- if the checks aren't driver-free,
the static core's stdlib-only invariant breaks and CI dies on `retail check`.

**Independent Test**: Inject a fake `QueryRunner` returning canned rows; assert each check emits
the right `Finding`s for both the clean case and the defect case. Run the whole suite with
psycopg2 ABSENT (dev deps have no driver) -- it passes, proving the logic is driver-free.

**Acceptance Scenarios**:

1. **Given** a fake runner where `silver` row count != distinct-PK count, **When** the PK check
   runs, **Then** it emits an ERROR Finding naming the duplicate/NULL count (enforces RC2).
2. **Given** a fake runner reporting N fact dates missing from `dim_date`, **When** the coverage
   check runs, **Then** it emits an ERROR Finding with N (enforces RC15-live).
3. **Given** a fake runner reporting orphan FK rows, **When** the orphan check runs, **Then** it
   emits an ERROR Finding per affected dim (enforces RC16).
4. **Given** a fake runner where a measure total differs silver vs gold, **When** the
   reconciliation check runs, **Then** it emits an ERROR Finding naming the measure + the gap.
5. **Given** all checks pass (clean fake), **Then** zero Findings.

### User Story 2 - The static core stays stdlib-only (Priority: P1)

Adding `retail validate` MUST NOT pull a DB driver into `retail check`'s import path.

**Why this priority**: protects the shipped, CI-green static gate.

**Independent Test**: import `retail.cli` and run `retail check` with psycopg2 not installed;
both succeed. A guard test asserts `retail.validate` imports with no driver present.

**Acceptance Scenarios**:

1. **Given** psycopg2 is not installed, **When** `import retail.cli` and `import retail.validate`
   run, **Then** neither raises (the driver import is lazy, inside the handler only).
2. **Given** `retail check` is invoked, **Then** it completes without importing psycopg2.

### User Story 3 - A `retail validate` command exists (live run deferred) (Priority: P2)

The CLI exposes `retail validate` as a sibling of `check`; wiring the real DB connection is
present but the actual live run against the production DB is a deferred follow-up.

**Independent Test**: `retail validate --help` lists the subcommand and its flags
(`--database`, target args); the handler's connection path is covered by the seam, the live
execution against the analytics DB is documented as the deferred step.

**Acceptance Scenarios**:

1. **Given** the CLI, **When** `retail validate --help` runs, **Then** the subcommand and its
   flags are shown.
2. **Given** no DB credentials, **When** `retail validate` is invoked, **Then** it fails with a
   clear "DB connection required / install the `db` extra" message, not a traceback.

### Edge Cases

- psycopg2 absent + `retail validate` invoked -> a clear actionable error ("install `retail[db]`"),
  never an ImportError traceback.
- A measure total that is NULL on one layer -> treated as a reconciliation defect, not a crash.
- The check **targets** (PK columns, FK->dim map, measures) are parameters this slice; where they
  come from per-table is deferred (the natural source is the kit's `source-map.yaml`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `src/retail/validate.py` with four check functions, each
  `Callable[[QueryRunner], Iterable[Finding]]`, reusing `Finding`/`Severity` from `core.py`.
  The module MUST be importable with no DB driver installed (stdlib-only import path).
- **FR-002**: Define a `QueryRunner` Protocol (`run(sql: str, params: tuple) -> list[tuple]`).
  All DB access in the checks goes through it; tests inject a fake.
- **FR-003**: Live findings are **Severity.ERROR** (proven defects). State the suspect->WARN /
  proven->ERROR asymmetry vs the static rules in a module docstring.
- **FR-004**: The four checks enforce RC2 (PK uniqueness), RC15-live (date coverage), RC16
  (0 orphan FKs), RC16 (penny-exact cross-layer measure reconciliation). Each names its RC.
- **FR-005**: The DB connection seam (`import psycopg2`, read `.env`/doctl, build a real
  `QueryRunner`) MUST be lazy -- imported only inside the `validate` subcommand handler, never
  at `cli.py` module scope. `retail check` MUST NOT import psycopg2.
- **FR-006**: `psycopg2` is an **optional-dependency** (`[project.optional-dependencies] db`),
  NOT a core or dev dependency. `dependencies` stays `[]`.
- **FR-007**: Add a `retail validate` argparse subcommand (sibling of `check`). Invoked without
  a usable connection / driver, it MUST print a clear actionable message and exit non-zero --
  never a raw traceback.
- **FR-008**: Tests (TDD, first) cover each check pass+fail with a fake runner, plus a guard
  test that the validate/cli import works with psycopg2 absent. Targets (PK/FK/measures) are
  passed as parameters; per-table sourcing from `source-map.yaml` is deferred.
- **FR-009**: The **live run** against the real DB (the analytics DB) is **out of scope this slice**
  -- the surface is built and fixture-verified; executing it live is the deferred follow-up.

### Key Entities

- **QueryRunner (Protocol)**: `run(sql, params) -> list[tuple]`. The seam between driver-free
  check logic and a real/fake DB.
- **Live check**: a `Callable[[QueryRunner], Iterable[Finding]]` proving one ADR default on
  materialized data; emits ERROR Findings.
- **Connection seam**: the lazy, psycopg2-backed `QueryRunner` builder in the CLI handler.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full unit suite passes with **psycopg2 NOT installed** -- proving the check
  logic and `retail.cli`/`retail.validate` imports are driver-free.
- **SC-002**: `retail check` still reports **26 rules** and **exits 0**; it imports no psycopg2
  (a guard test asserts this).
- **SC-003**: Each of the four checks has a fake-runner pass test and a defect test; all green.
- **SC-004**: `retail validate --help` shows the subcommand; invoked without driver/creds it
  exits non-zero with an actionable message (no traceback).
- **SC-005**: `dependencies = []` unchanged; psycopg2 appears only under
  `optional-dependencies.db`; dev deps unchanged (so CI installs no driver).
- **SC-006**: Constitution at **v1.4.0**; "deferred `retail validate`" language updated to
  "surface built; live run deferred" across Principle VIII, architecture Sec 7/8, and the
  reconciliation-report template.

## Assumptions

- Live execution against the production DB is deferred (option B): this slice builds + fixture-
  tests the surface; the real run against the analytics DB (read-only, creds from gitignored `.env`)
  is a clean follow-up needing a DB window.
- Check targets (PK columns, FK->dim map, measures) are parameters now; the per-table source is
  the kit's `source-map.yaml` (deferred wiring, named not built).
- `psycopg2` is the driver (matches `pipelines/load_bronze.py`, the repo's established DB access).
- Work on `main`; constitution amendment in scope (Principle VIII names the surface).

## Deferred decisions (future specs / issues -- recorded, not built)

The connection layer was discussed as a possible "general BI tool" reaching beyond
Postgres. Scoped decision (this slice): **any Postgres host only** -- fits constitution
Principle III (Postgres-first), no amendment needed. The broader ideas are parked as
explicit future work, each its own spec/issue when prioritized:

- **[NEEDS CLARIFICATION: multi-engine DBs]** MySQL / Snowflake / BigQuery / etc.
  Needs per-engine drivers + dialect-specific SQL (the checks use Postgres `FILTER`,
  `generate_series`, `sum`). Requires a constitution amendment to Principle III
  (no longer Postgres-only). The `QueryRunner` Protocol already leaves the seam open.
- **[NEEDS CLARIFICATION: local files in multiple formats]** CSV / Parquet / Excel as
  validation sources. This reframes the kit from "governed Postgres medallion" toward a
  general BI tool over arbitrary sources -- a constitution-IDENTITY (MAJOR) change, and it
  revisits the deliberately-rejected Parquet-first decision. Largest scope; needs its own
  product decision before any spec.
- **[NEEDS CLARIFICATION: per-table target sourcing]** Where PK/FK/measure targets come
  from per table -- the natural source is the kit's `source-map.yaml` (named, not wired here).
- **[NEEDS CLARIFICATION: live execution]** Actually running the checks against a real DB
  (FR-009) -- needs the `db` extra + credentials; deferred follow-up.

## See also

- The static counterpart: `src/retail/rules/sql.py` (S5/S6/S7), `retail check`.
- What needs live proof: `docs/c086-adr0002-compliance.md` Sec 8; worked example Sec 8.
- The blank this fills: `templates/reconciliation-report.md`.
- DB access pattern: `pipelines/load_bronze.py` (psycopg2 + doctl, outside the static core).
- Constitution Principle VIII (the static-now / live-deferred taxonomy -> v1.4.0).
