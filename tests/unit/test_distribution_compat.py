"""Spec 119 compatibility tests for the renamed import module."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_db_connection_var(key: str) -> bool:
    """A live-DB connection env var (e.g. ANALYTICS_DB_*, *_DSN, DATABASE_URL)
    that must be scrubbed so a green subprocess exit honestly proves no DB use."""
    return (
        key.startswith("ANALYTICS_DB") or key.endswith("_DSN") or key == "DATABASE_URL"
    )


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    # Scrub any live-DB connection vars so a green exit is honest evidence that
    # the capability inventory needs no database (the shell may export
    # ANALYTICS_DB_* for `retail validate`'s live leg).
    for key in [k for k in env if _is_db_connection_var(k)]:
        del env[key]
    return env


def _run_module(module: str, workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, "check", "--repo", str(workspace)],
        text=True,
        capture_output=True,
        env=_environment(),
        check=False,
    )


def test_retail_import_shim_resolves() -> None:
    import retail
    import seshat

    assert retail is not None
    assert seshat is not None


def test_legacy_module_cli_matches_seshat(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    legacy = _run_module("retail.cli", tmp_path)
    primary = _run_module("seshat.cli", tmp_path)

    assert legacy.returncode == primary.returncode
    assert legacy.stdout == primary.stdout
    assert legacy.stderr == primary.stderr


# ---------------------------------------------------------------------------
# Capability inventory: the documented `python -m` entry point (spec 118/119).
# The skill and docs advertise `python -m seshat.capability_inventory`; the
# `retail` shim is a bare `from seshat import *` re-export that does NOT expose
# `retail.capability_inventory` as an importable submodule, so the OLD documented
# command failed with ModuleNotFoundError. These tests guard BOTH the working
# canonical command AND that the docs keep pointing at it (the drift that broke).
# ---------------------------------------------------------------------------


def _run_capability_inventory() -> subprocess.CompletedProcess[str]:
    """Invoke the module exactly as the skill/docs advertise. Runs from the repo
    root because the builder resolves ``docs/capabilities/capabilities.yaml``
    relative to CWD (``build_inventory(".")``)."""
    return subprocess.run(
        [sys.executable, "-m", "seshat.capability_inventory", "--format", "json"],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=_environment(),
        check=False,
    )


def test_capability_inventory_json_runs_and_has_records() -> None:
    """`python -m seshat.capability_inventory --format json` exits 0, emits valid
    JSON with capability records, and needs no database (DB env is scrubbed)."""
    result = _run_capability_inventory()

    assert result.returncode == 0, result.stderr
    records = json.loads(result.stdout)
    assert isinstance(records, list)
    assert records, "capability inventory produced no records"
    assert all("id" in record for record in records), records


def test_capability_docs_advertise_the_working_command() -> None:
    """The skill and capability README must advertise the command that WORKS
    (`python -m seshat.capability_inventory`) and must NOT advertise the broken
    legacy `python -m retail.capability_inventory` -- the shim has no such
    submodule, so the old string is a documented-but-dead command."""
    doc_paths = (
        REPO_ROOT / ".claude" / "skills" / "capabilities" / "SKILL.md",
        REPO_ROOT / "docs" / "capabilities" / "README.md",
    )
    for path in doc_paths:
        text = path.read_text(encoding="utf-8")
        assert "python -m seshat.capability_inventory" in text, path
        assert "python -m retail.capability_inventory" not in text, path


def test_no_new_capabilities_cli_verb() -> None:
    """The fix stays inside the ratified Option-B boundary: no `capabilities`
    verb was introduced into the CLI parser or its dispatch table."""
    from seshat.cli import _DISPATCH
    from seshat.cli.parser import _build_parser

    assert "capabilities" not in _DISPATCH
    assert "capabilities" not in _build_parser().format_help()
