"""The test suite must not inherit the developer's global git configuration.

Tests that build a throwaway repo and commit into it would otherwise fail on any
machine configured to sign commits (``commit.gpgsign=true`` with an ssh signer), because
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
def test_global_git_config_points_at_a_session_file() -> None:
    """The global layer is redirected away from the developer's real config."""
    value = os.environ.get("GIT_CONFIG_GLOBAL")
    assert value, "GIT_CONFIG_GLOBAL is not set; the suite inherits real git config"
    assert Path(value).is_file(), f"GIT_CONFIG_GLOBAL points at {value!r}, not a file"


@pytest.mark.unit
def test_system_git_config_is_not_redirected() -> None:
    """The system layer must be left intact.

    On Windows it carries ``core.autocrlf = true`` from the Git-for-Windows installer.
    Blanking it changes line-ending normalization on ``git add``, which changes the
    committed blob SHAs and makes every revision-citation test report a stale contract.
    Signing is neutralized through the global layer instead, which takes precedence.
    """
    assert "GIT_CONFIG_SYSTEM" not in os.environ


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
    """What the 13 failing tests need: a commit with no per-test git config."""
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "file.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    done = subprocess.run(
        ["git", "commit", "-q", "-m", "test: initial"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, f"commit failed: {done.stderr}"
