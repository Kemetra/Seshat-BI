# T1 — Hermetic Git Test Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pytest` immune to the developer's global git configuration, so the 13
temp-repo tests that currently die on commit signing pass on any machine.

**Architecture:** Add a session-scoped autouse fixture in a new `tests/conftest.py`
that points `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` at throwaway config files for
the duration of the test session. Every `git` subprocess the suite spawns then reads a
known-empty system config and a known-good global config, regardless of what the
developer has configured. This replaces the approach in the spec's T1 Design section
(see *Deviation from the spec* below).

**Tech Stack:** Python 3.13, pytest 8, `subprocess`, git.

## Global Constraints

- Committed text is ASCII / UTF-8 without BOM (rules `G3`/`G4`).
- Commit subjects are `<type>: <description>`, **scope-free** (rule `P2`). Allowed
  types: `feat fix refactor docs chore build ci perf test style revert brand`.
- Branch off `main`; never push directly to `main`.
- Type annotations on every function signature.
- Do not edit the developer's real global git config. The fixture must set environment
  variables only, and must restore them afterwards.
- Commit signing fails in this environment (1Password, no `SSH_AUTH_SOCK`). Signing was
  authorized off for this session's commits via `git -c commit.gpgsign=false commit`;
  do not add `--no-verify`, and do not change any git config outside the test fixture.

## Deviation from the spec

`docs/superpowers/specs/2026-07-30-engine-program-design.md` T1 Design says to repoint
the five files at `_gitfix.make_git_repo`. That is not viable as written, and this plan
supersedes it:

`make_git_repo(tmp_path)` hardcodes `repo = tmp_path / "repo"` and calls `repo.mkdir()`
(`tests/unit/_gitfix.py:11-12`), returning the new subdirectory. All five failing sites
instead initialize git **in place** at a caller-supplied root:

| Site | Wrapper shape |
|---|---|
| `tests/unit/dbt/test_project.py:264` | `_git(root, *args)` → `git -c user.email=t@t -c user.name=t …`, `cwd=root` |
| `tests/unit/dbt/test_scaffold_conformed_orchestration.py:24` | identical `-c` shape, `cwd=root` |
| `tests/unit/test_workspace_init.py:40` | `_git(cwd, *args)` → `git -C <cwd> …`, then `config user.email`/`user.name` |
| `tests/unit/test_portfolio_watch_invariants.py:128` | `_init_repo_with_commit(root)`, inits at `root` |
| `tests/unit/test_portfolio_watch_summary.py` | same pattern inline |

Adopting the helper would therefore require either a new in-place variant or reshaping
what each test asserts on, since the tests pass `tmp_path` itself as the repo root to
the code under test. The hermetic-environment fix is one new file, covers all 13
failures plus `tests/integration/test_watch_cli.py`, and immunizes future tests instead
of relying on every author remembering the rule.

The spec's static-sweep claim that the helper has no capability gaps was wrong; this
mismatch is the gap.

## File Structure

| File | Responsibility |
|---|---|
| `tests/conftest.py` (**create**) | Session-scoped hermetic git environment for the whole suite. Nothing else — no shared fixtures, no imports from `seshat`, so it cannot affect the lazy-import guard tests. Placed at `tests/` rather than `tests/unit/` so `tests/integration/` is covered too. Verified compatible: `tests/unit/conftest.py` only re-exports two `dep_coresolve` stub fixtures and `tests/live_db/conftest.py` is scoped to live-DB runs, so neither declares an autouse fixture or patches the environment. Requires git ≥ 2.32 for `GIT_CONFIG_SYSTEM`; measured 2.45.1 here. |
| `tests/unit/test_hermetic_git_env.py` (**create**) | Proves the environment is hermetic and that a bare temp repo can commit with no per-test git config. |
| `CONTRIBUTING.md` (**modify**, "Before you commit" section) | One line telling contributors the suite is hermetic, so nobody re-adds per-test signing config. |

`tests/unit/_gitfix.py` is **not** modified. The five failing test files are **not**
modified.

---

### Task 1: Hermetic git environment for the test session

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/unit/test_hermetic_git_env.py`
- Modify: `CONTRIBUTING.md` ("Before you commit" section, currently lines 54-75)

**Interfaces:**
- Consumes: nothing from earlier tasks (this is the first task).
- Produces: a session-scoped autouse fixture named `hermetic_git_config`, yielding the
  `pathlib.Path` of the global config file it wrote. No test needs to request it by
  name — it is `autouse=True` — but requesting it is how the guard test asserts on it.

**Prerequisite — refresh the editable install.** Four unrelated tests
(`tests/unit/statistical/test_registry.py`, `tests/unit/test_cli_analyze.py`,
`tests/unit/test_cli_dagster.py`, `tests/unit/test_metric_drift.py`) spawn a clean
subprocess that imports `seshat.rules`, and fail with
`ModuleNotFoundError: No module named 'seshat.rules'` when the installed package
predates the `retail` → `seshat` rename. They are not this task's scope, but the suite
cannot be read as green until they pass.

- [ ] **Step 1: Refresh the editable install and confirm those four pass**

```bash
pip install -e ".[dev]"
python -m pytest tests/unit/statistical/test_registry.py::test_importing_registry_does_not_import_numerical_libraries tests/unit/test_cli_analyze.py::test_cli_import_does_not_load_numerical_statistics "tests/unit/test_cli_dagster.py::TestLazyImportGuard::test_importing_the_cli_never_imports_the_adapter" tests/unit/test_metric_drift.py::test_importing_retail_rules_does_not_pull_metric_drift -q --no-cov -p no:cacheprovider
```

Expected: `4 passed`. If they still fail with `ModuleNotFoundError`, the install did
not take — stop and report rather than proceeding, because every later step's
verification depends on a working install.

- [ ] **Step 2: Write the failing guard test**

Create `tests/unit/test_hermetic_git_env.py`:

```python
"""The test suite must not inherit the developer's global git configuration.

Tests that build a throwaway repo and commit into it would otherwise fail on any
machine configured to sign commits (`commit.gpgsign=true` with an ssh signer), because
no signing agent is reachable from a non-interactive subprocess. CI has no signing
configured and therefore never sees it, which makes the breakage latent rather than
harmless. The session fixture in ``tests/conftest.py`` pins the git environment; these
tests prove it is actually pinned.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.unit
def test_git_config_env_vars_point_at_session_files() -> None:
    """Both git config layers are redirected away from the developer's real files."""
    for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"):
        value = os.environ.get(key)
        assert value, f"{key} is not set; the suite is inheriting real git config"
        assert Path(value).is_file(), f"{key} points at {value!r}, which is not a file"


@pytest.mark.unit
def test_signing_is_disabled_for_subprocess_git(tmp_path: Path) -> None:
    """A fresh repo reports signing OFF without any per-test configuration."""
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    out = subprocess.run(
        ["git", "config", "--get", "commit.gpgsign"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert out.stdout.strip() == "false"


@pytest.mark.unit
def test_commit_succeeds_without_per_test_git_config(tmp_path: Path) -> None:
    """The behaviour the 13 failing tests depend on: commit works with no local setup."""
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "file.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True
    )
    done = subprocess.run(
        ["git", "commit", "-q", "-m", "test: initial"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, f"commit failed: {done.stderr}"
```

- [ ] **Step 3: Run the guard test to verify it fails**

```bash
python -m pytest tests/unit/test_hermetic_git_env.py -q --no-cov -p no:cacheprovider
```

Expected: FAIL. `test_git_config_env_vars_point_at_session_files` fails with
`GIT_CONFIG_GLOBAL is not set; the suite is inheriting real git config`, and
`test_signing_is_disabled_for_subprocess_git` fails — either on the assert (if the
machine has no `commit.gpgsign`, `git config --get` exits 1 and `check=True` raises
`CalledProcessError`) or on the comparison (if it is set to `true`). The third test
passes or fails depending on the developer's config; both outcomes are fine at this
step.

- [ ] **Step 4: Write the fixture**

Create `tests/conftest.py`:

```python
"""Session-wide test environment guards.

Kept deliberately free of ``seshat`` imports: several tests assert that importing the
package does not pull heavy or lazy modules, and a conftest import would run before
them and invalidate the assertion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

_HERMETIC_GITCONFIG = """\
[user]
\tname = Seshat Test
\temail = test@example.invalid
[commit]
\tgpgsign = false
[tag]
\tgpgsign = false
[init]
\tdefaultBranch = main
[protocol "file"]
\tallow = always
"""


@pytest.fixture(scope="session", autouse=True)
def hermetic_git_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Path]:
    """Point git at throwaway config files for the whole test session.

    Tests that build a temp repo and commit into it must not inherit the developer's
    global config: a machine with ``commit.gpgsign=true`` and an ssh signer cannot sign
    from a non-interactive subprocess, so ``git commit`` exits 128 and the test fails
    for reasons unrelated to the code under test. CI configures no signing and so never
    reproduces it.

    Redirects both layers -- ``GIT_CONFIG_GLOBAL`` to a known-good config and
    ``GIT_CONFIG_SYSTEM`` to an empty file -- and restores the previous values on
    teardown. The developer's real config files are never read or written.
    """
    root = tmp_path_factory.mktemp("gitconfig")
    global_config = root / "gitconfig"
    global_config.write_text(_HERMETIC_GITCONFIG, encoding="utf-8")
    system_config = root / "system-gitconfig"
    system_config.write_text("", encoding="utf-8")

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
        patch.setenv("GIT_CONFIG_SYSTEM", str(system_config))
        yield global_config
```

- [ ] **Step 5: Run the guard test to verify it passes**

```bash
python -m pytest tests/unit/test_hermetic_git_env.py -q --no-cov -p no:cacheprovider
```

Expected: `3 passed`.

- [ ] **Step 6: Run the 13 previously-failing tests**

```bash
python -m pytest tests/unit/dbt/test_project.py tests/unit/dbt/test_scaffold_conformed_orchestration.py tests/unit/test_portfolio_watch_invariants.py tests/unit/test_portfolio_watch_summary.py tests/unit/test_workspace_init.py -q --no-cov -p no:cacheprovider
```

Expected: `59 passed, 1 skipped`. That count is the measured figure from running these
five files with a neutralized global config, so it is the target. If any fail, the
fixture is not reaching those subprocesses — do not patch the individual tests; fix the
fixture.

- [ ] **Step 7: Confirm the integration test the spec flagged as a candidate**

```bash
python -m pytest tests/integration/test_watch_cli.py -q --no-cov -p no:cacheprovider
```

Expected: PASS. This test commits at L77-78 without disabling signing, so it is the
same defect; `-m unit` merely deselects it. Record the result — it is the evidence that
the fix generalizes past the unit suite.

- [ ] **Step 8: Run the full unit suite**

```bash
python -m pytest -m unit -q --tb=short -p no:cacheprovider
```

Expected: `0 failed`. Baseline before this change was **17 failed, 4288 passed, 28
skipped, 388 deselected** — 13 signing plus the 4 stale-install failures cleared in
Step 1. Coverage is on by default via `addopts`, so this takes roughly 11-12 minutes;
do not add `--no-cov` here, because the committed configuration is what CI runs. Paste
the real summary line as evidence; do not assert success without it.

- [ ] **Step 9: Document it so nobody re-adds per-test signing config**

In `CONTRIBUTING.md`, in the "Before you commit" section after the command block, add:

```markdown
The test suite is hermetic with respect to git: a session fixture in `tests/conftest.py`
redirects `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` at throwaway files, so tests that
build a temp repo and commit into it do not need their own `commit.gpgsign=false` and
will not fail on a machine that signs commits.
```

- [ ] **Step 10: Lint and format**

```bash
ruff format --check src tests
ruff check src tests
```

Expected: both clean. If `ruff format --check` reports the new files, run
`ruff format tests/conftest.py tests/unit/test_hermetic_git_env.py` and re-check.

- [ ] **Step 11: Run the static governance gate**

```bash
python -m seshat.cli check
python -m seshat.cli semantic-check --repo .
```

Expected: no ERROR-severity findings. If a rule id fires, use the `retail-govern` skill
to map the id to its fix rather than guessing what the id means.

- [ ] **Step 12: Commit**

```bash
git add tests/conftest.py tests/unit/test_hermetic_git_env.py CONTRIBUTING.md
git commit -m "test: make the suite hermetic against global git config"
```

If commit signing fails with `1Password: No SSH private key found`, that is the known
environment wall — report it and ask before bypassing. Do not use `--no-verify`.

---

## Non-goals for this task

- **Not** modifying `tests/unit/_gitfix.py`. It stays as the explicit helper for tests
  that want a repo at `tmp_path/repo`.
- **Not** modifying the five failing test files. The fixture makes their existing code
  correct; editing them as well would be churn with no defect behind it.
- **Not** removing the now-redundant inline `-c commit.gpgsign=false` flags from
  `test_dagster_evidence.py`, the three `test_pbip_adoption_*.py` files,
  `test_fresh_workspace.py`, or `tests/fixtures/portfolio_watch/builders.py`. They are
  harmless and belt-and-braces; deleting them is a separate cleanup with its own risk.
- **Not** fixing the four lazy-import guard tests in code. Step 1 handles them as an
  environment action, which is the correct remedy.

## Self-review

**Spec coverage.** The spec's T1 section requires: the 13 Group-B failures pass (Step
6); the `tests/integration/test_watch_cli.py` candidate is confirmed rather than assumed
(Step 7); Group A is acknowledged as environmental and not code-fixed (Step 1 plus
Non-goals); and signing policy lives in one place rather than per call site (the fixture).
The spec's stated mechanism — adopting `_gitfix.make_git_repo` — is deliberately not
implemented, with the reason recorded under *Deviation from the spec*; the spec should be
amended to match before this lands, so the two documents do not disagree.

**Placeholder scan.** No TBDs. Every code step carries complete code; every run step
carries the exact command and the expected output, including the numeric targets
(`4 passed`, `3 passed`, `59 passed, 1 skipped`, `0 failed`).

**Type consistency.** The fixture is named `hermetic_git_config` in `conftest.py` and is
never referenced by name in the guard test (it is `autouse`), so there is no
name-mismatch surface. Return type is `Iterator[Path]` for a yielding fixture;
`tmp_path_factory` is annotated `pytest.TempPathFactory`, matching pytest 8.

## Why the other four tracks are not in this plan

The writing-plans skill requires one plan per independent subsystem, and three of the
remaining four are blocked on an input rather than on effort:

| Track | Blocked on |
|---|---|
| **T2** — CVD simulation evidence | Not blocked, and **already has a plan**: `specs/118-cvd-simulation-evidence/plan.md` and `tasks.md` exist. Refresh its stale `src/retail/*` → `src/seshat/*` anchors (`theme_gen.py:569` → `:789`, `:470` → `~:676`) and execute that, rather than writing a second plan for the same feature. |
| **T3** — rule-id fix table | The authoring-cost decision. `registry.py` has no fix field, so this means authoring fix guidance for 32 rules and migrating 47 more. Whether that is one PR or a split changes the whole task breakdown, and it may reorder T3 behind T4. |
| **T4** — fixture provenance | Which field the bundle treats as authoritative — 3 of 9 fixtures already carry `source_revision`, and `export_agent_bundles.py` writes both that and `manifest_digest`. Bind to one; picking needs a read of the manifest's own contract. |
| **T5** — spec-status claims | An owner ruling on the closed status vocabulary. Ten free-text variants exist today and no doc defines what `Ratified` vs `Implemented` vs `BUILT` mean. The manifest entries cannot be written until the vocabulary is fixed. |
