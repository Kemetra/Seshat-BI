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
retail check
retail semantic-check --repo .
```

- `retail check` is the static governance gate; its exit code is the authority.
- `retail semantic-check --repo .` reports contract-vs-measure drift (no drift =
  clean).

> [!NOTE]
> **Known P2 finding on the current tree.** `retail check`'s P2 rule scans the
> recent commit range (`HEAD~20..HEAD`) and currently flags two pre-existing
> nonconforming commit subjects -- `Add agent compass and knowledge router (#48)`
> and `Add BI DAX knowledge skill v0.2 (#42)` -- so on a clean checkout of `main`
> the gate exits `1` for that reason. This is a recorded, known condition that
> predates this release, not a fresh failure. Do not record `retail check` as
> exiting cleanly while those two historical subjects are in range; the remaining
> surfaces in the sequence above exit cleanly.
>
> `HEAD~20..HEAD` is the **local fallback** range only. CI passes an explicit
> `--commit-range` (such as `origin/main..HEAD`), so the gate scopes to the PR's
> own commits and is not tripped by these older subjects -- which is why the CI
> `check` job can be green while a bare local `retail check` exits `1`.

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
