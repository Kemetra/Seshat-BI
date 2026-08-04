"""Unit tests for the `version_compatibility` check (spec 129, FR-011).

Split out of the former monolithic ``test_agent_verify_checks.py`` to keep
each test module single-purpose (CodeScene Low Cohesion).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from seshat.agent_verify import checks
from tests.unit._agent_verify_fixtures import target_spec

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _patch_audit_versions(
    monkeypatch: pytest.MonkeyPatch, projections: list[dict]
) -> None:
    def _fake_audit_versions(repo_root):  # noqa: ANN001 - test double
        return {"projections": projections}

    monkeypatch.setattr(
        "seshat.release_versions.audit_distribution_versions", _fake_audit_versions
    )


def test_version_compatibility_pass_in_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": "0.2.0",
                "expected": "0.2.0",
                "status": "pass",
            }
        ],
    )
    result = checks.version_compatibility_check(spec, tmp_path)
    assert result.verdict == "PASS"
    assert "0.2.0" in result.evidence[0]


def test_version_compatibility_blocked_out_of_range_names_both_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": "0.1.0",
                "expected": "0.2.0",
                "status": "blocked",
                "blocking_reason": "claude_plugin version is '0.1.0'; expected '0.2.0'",
            }
        ],
    )
    result = checks.version_compatibility_check(spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert "0.1.0" in result.blocking_reasons[0]
    assert "0.2.0" in result.blocking_reasons[0]


def test_version_compatibility_blocked_when_declaration_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = target_spec(tmp_path)
    _patch_audit_versions(monkeypatch, [])  # no projection for this surface at all
    result = checks.version_compatibility_check(spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert "no version projection" in result.blocking_reasons[0]


def test_version_compatibility_never_passes_on_absent_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = target_spec(tmp_path)
    _patch_audit_versions(
        monkeypatch,
        [
            {
                "surface": "claude_plugin",
                "observed": None,
                "expected": "0.2.0",
                "status": "blocked",
            }
        ],
    )
    result = checks.version_compatibility_check(spec, tmp_path)
    assert result.verdict != "PASS"


def test_version_compatibility_works_from_installed_package_boundary(
    tmp_path: Path,
) -> None:
    """The check must not depend on the development-only ``scripts`` package."""

    program = """
import sys
from pathlib import Path

from seshat.agent_verify.checks import version_compatibility_check
from seshat.agent_verify.targets import resolve_target

result = version_compatibility_check(resolve_target("claude"), Path(sys.argv[1]))
print(result.verdict)
if result.blocking_reasons:
    print(result.blocking_reasons[0])
raise SystemExit(0 if result.verdict == "PASS" else 1)
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program, str(_REPO_ROOT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.splitlines() == ["PASS"]
