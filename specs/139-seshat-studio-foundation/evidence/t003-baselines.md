# T003 — Pre-change baselines

**Task**: T003 (Phase 1, Governance Preconditions) — "Capture baseline results for
static dashboard, B1 imports, bundle regeneration, package contents, unit tests, and
accessibility tooling." [SC-009]

**Captured**: 2026-08-10
**Branch**: `studio`
**Commit**: `6104858` (docs only; `src/`, `tests/`, `pyproject.toml`, and
`integrations/` are byte-identical to `main` at `5b2c2f5`, verified with
`git diff --stat main HEAD -- src/ tests/ pyproject.toml integrations/` returning
empty). These baselines therefore describe untouched production code.

**Purpose**: This is the regression floor. SC-009 requires proving that Studio does
not regress the existing dashboard, the B1 import boundary, or bundle generation. A
baseline captured after editing `src/` could not distinguish pre-existing state from
a regression, so it is recorded before Phase 2 begins.

## Full unit + contract suite

```
PYTHONPATH=src python -m pytest tests/unit tests/contract -q --no-cov
```

| Result | Count |
| --- | --- |
| passed | 5822 |
| failed | 2 |
| skipped | 23 |
| duration | 437.10s (7m17s) |

### The two failures are pre-existing and environmental, NOT regressions

Both reproduce identically on an untouched `main` checkout, confirmed by running the
same two node ids in the main worktree at `5b2c2f5`.

1. `tests/unit/test_agent_verify_version_compatibility.py::test_version_compatibility_works_from_installed_package_boundary`
   — fails with `ModuleNotFoundError: No module named 'seshat'`. The test spawns
   `python -I` (isolated mode), which by design ignores `PYTHONPATH`. It requires a
   real `pip install -e .` in the active interpreter.
2. `tests/unit/test_issue_regression_489_command_safety.py::test_emitted_assessment_command_works_when_run_from_the_repo_root`
   — fails with `FileNotFoundError` spawning `['seshat', 'orchestration-assess', ...]`.
   The `seshat` console script is not on PATH in this worktree.

Both belong to the known "editable install absent from the worktree" class rather than
to Studio. Phase 8's T035 regression gate must be measured against **5822 passed /
2 environmental failures**, not against a clean zero, unless an editable install is
performed first — in which case both are expected to pass and the floor rises to 5824.

## Static dashboard (FR-030 requires it stay unchanged)

```
PYTHONPATH=src python -m pytest tests/unit -k "dashboard" -q --no-cov
```

`92 passed, 1 skipped`. Source of truth: `src/seshat/dashboard/` (`generate.py`,
`render.py`, `theme.py`). Studio must not alter these numbers.

## B1 import boundary (never-execute)

```
PYTHONPATH=src python -m pytest tests/unit -k "never_execute" -q --no-cov
```

`20 passed, 1 skipped`.

`src/seshat/rules/never_execute.py` governs
`_GOVERNED_PREFIXES = ("src/seshat/rules/", "src/seshat/cli/")` and fails closed on a
**module-scope** import of a connection-capable module (`socket`, `http`, `websocket`,
`websockets`, …). `src/seshat/studio/` is outside those prefixes, which is why T005
requires web imports to stay lazy and outside `seshat.cli` / `seshat.rules`. Any
Studio import that leaks into the CLI parser at module scope will trip B1.

## Bundle regeneration

```
python scripts/export_agent_bundles.py --repo .
git status --short integrations/
```

Clean — regeneration is **byte-identical** before any Studio change. T030 must
preserve this property after registering the new capability.

## Package contents

From `pyproject.toml`:

- version: `0.8.2`
- console scripts: `retail`, `seshat` (**no `seshat-studio`** — T005/FR-006 adds it)
- runtime dependencies: 1
- extras (13): `browser`, `db`, `dbt`, `dev`, `files`, `livetest`, `mcp`, `mssql`,
  `mysql`, `report`, `report-pdf`, `snowflake`, `stats`, `stats-change`

**No `studio` extra exists.** T005 adds it; T004's failing package-contract tests
come first and must assert base-install isolation.

## Governance gate

```
PYTHONPATH=src python -m seshat.cli check
```

One pre-existing warning, unrelated to Studio and outside this feature's scope:

```
[warning] RS1 last_checked_at 2026-06-25 predates latest approval 2026-07-23;
a named human must recompute the audit metadata
(mappings/retail_store_sales/readiness-status.yaml)
```

The active-marker contract test
(`tests/contract/test_dbt_documentation.py::test_active_spec_kit_markers_agree_and_resolve`)
passes with the fence on this plan.

## Accessibility tooling — NOT yet available

`npx axe --version` fails (`could not determine executable to run`), and `studio-ui/`
does not exist. This is expected at T003: the frontend workspace and its dev
dependencies are created in T012, and the axe harness is installed as part of that
work. **T032 cannot run until T012 lands**, and this gap is recorded here rather than
reported as a passing baseline.
