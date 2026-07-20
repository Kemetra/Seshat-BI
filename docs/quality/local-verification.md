# Local verification checklist

How to verify a Seshat BI checkout on your own machine. This mirrors the intent
of CI: static checks, unit tests, and the static governance gate -- plus an
optional live path when a database is available.

> Do not claim CI is green unless GitHub Actions actually shows a successful run,
> and do not claim live validation passed unless it was run against a real
> database. The kit never fakes a pass.

## Prerequisite

- **Python 3.13** (`pyproject.toml` sets `requires-python = ">=3.13"`).

## 1. Editable dev install

```bash
pip install -e ".[dev]"
```

This installs the `retail` package and the dev extras (ruff, pytest, pyyaml).

## 2. Static checks

```bash
ruff format --check src tests
ruff check src tests
```

Both should report clean (formatting matches; no lint findings).

## 3. Unit tests

```bash
pytest -m unit
```

The fast unit suite should pass. The suite is driver-free: it runs without any
database driver installed.

## 4. Retail governance checks

```bash
seshat check
retail semantic-check --repo .
```

- `seshat check` is the static governance gate; its exit code is the authority.
- `retail semantic-check --repo .` reports contract-vs-measure drift (no drift =
  clean).

> [!NOTE]
> **Local P2 scope.** A bare `seshat check` (no `--commit-range`) scopes its P2
> commit-subject rule to the **current/incoming commit only** (`HEAD~1..HEAD`), so
> on a compliant HEAD it exits cleanly and is **not** tripped by aged-out
> nonconforming subjects further back in history. Run bare `seshat check` for
> day-to-day verification of the current change -- its exit code is authoritative
> for what you are about to commit.
>
> CI and the commit-msg hook still enforce P2 on new commits: CI passes an
> explicit `--commit-range` (`merge-base(origin/main, HEAD)..HEAD`), so it scopes
> to the branch's own commits and will honestly flag any nonconforming subject in
> that range; the commit-msg hook validates each incoming subject as it is
> written. Neither path uses the local fallback range.

## 5. Optional DB / live validation path

These run only when a real database connection is configured (the driver import
is lazy, so the rest of the kit works without a DB):

```bash
pip install -e ".[db]"
retail validate --source-map mappings/<table>/source-map.yaml
retail value-check --repo .
```

Replace `<table>` with a mapped table folder under `mappings/` (for example,
`mappings/retail_store_sales/source-map.yaml`).

## Do-not-fake-pass rule

- **If no database exists, live validation is _pending_, not _passed_.** Do not
  record `retail validate` or `retail value-check` as passing without a real run
  against a real DB.
- Do not claim GitHub Actions is green unless a successful run is visible in
  GitHub Actions.
- Readiness is `status` + `evidence` + `blocking_reasons`. A missing check is a
  blocker or a pending item, never a silent pass.

## Local live-validation suite (opt-in, spec 082)

The `tests/live_db/` suite proves `retail validate` / `retail value-check`'s live
checks against a real, local, ephemeral PostgreSQL container -- no cloud, no real
credentials. It is OPT-IN and gated on Docker + the `livetest` extra:

```bash
pip install -e ".[db,livetest]"     # psycopg2 + the Docker-orchestration lib
pytest -m live_db                     # requires a running Docker daemon
```

- **`pytest -m unit` and CI never run these** (they are `live_db`-marked, and CI
  installs only `dev`) -- so the default suite stays repo-only and driver-free.
- **When Docker or the `livetest` extra is absent, these tests SKIP honestly** with
  a named reason (`docker not available`, `driver not installed`, `container failed
  to start`, `port conflict`, `seed failed`) -- never a hidden pass. The
  precondition contract is `specs/082-postgres-live-validation-suite/contracts/live-pass-contract.md`.
- A clean live run is recorded by 057 as `warning` (evidence a human may cite),
  never as a stage `pass` -- see the do-not-fake-pass rule above.
