"""Tests for E7 -- ``retail doctor`` read-only drift digest.

Doctor aggregates existing read-only checks + a load-bearing-doc probe into a
findings digest. It reads and reports, never fixes; emits no numeric score; is
advisory (exit 0) by default and only fails under --strict. It adds no @register
rule.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seshat.core import RuleContext
from seshat.doctor import collect_findings, format_digest, run_doctor

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap(repo: Path) -> None:
    """Make `repo` kit-bootstrapped so the KIT_SELF checks actually run (#377).

    Since Spec A, doctor SKIPS the aggregated kit-self checks in a repo that is not
    kit-bootstrapped (to agree with `check` and not over-report on a foreign repo).
    So a test that wants to see GENUINE drift must bootstrap first.
    """
    (repo / ".seshat").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "kit-source.yaml", repo / ".seshat" / "kit-source.yaml"
    )
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "compass.yaml", repo / ".seshat" / "compass.yaml"
    )


def _ctx_missing_everything(tmp_path: Path) -> RuleContext:
    # A BOOTSTRAPPED repo that is nonetheless missing its manifests -> genuine
    # drift the checks fire on (fail-loud), giving a non-empty digest.
    _bootstrap(tmp_path)
    return RuleContext(repo_root=tmp_path, tracked_files=())


def test_collect_findings_on_bootstrapped_repo_with_drift_reports_it(
    tmp_path: Path,
) -> None:
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    assert findings, "a bootstrapped repo missing its manifests should surface drift"
    # the load-bearing probe must flag the missing glossary
    assert any("glossary.md" in f.message for f in findings)


def test_format_digest_lists_findings_and_no_score(tmp_path: Path) -> None:
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    text = format_digest(findings)
    assert "finding(s)" in text
    # no numeric score / percentage in the digest (hard rule #9)
    assert "%" not in text
    assert "score" not in text.lower()


def test_format_digest_clean_message() -> None:
    assert "no drift found" in format_digest([])


def test_run_doctor_advisory_exits_zero_even_with_findings(tmp_path: Path) -> None:
    # default (advisory): exit 0 despite findings -> never a second gate.
    assert run_doctor(tmp_path, strict=False) == 0


def test_run_doctor_strict_exits_nonzero_on_findings(tmp_path: Path) -> None:
    # Bootstrap so the kit-self checks run and surface genuine drift (missing
    # manifests) -- strict must then exit non-zero. A non-bootstrapped repo is
    # covered separately in test_doctor_kit_self_skip.py (strict stays 0).
    _bootstrap(tmp_path)
    assert run_doctor(tmp_path, strict=True) == 1


def test_run_doctor_on_real_repo_is_clean_and_advisory() -> None:
    # Against the real committed tree, the aggregated checks should be clean and
    # doctor exits 0. (If this ever fails, the repo genuinely has drift -- which is
    # exactly what doctor is meant to surface.)
    repo_root = Path(__file__).resolve().parents[2]
    assert run_doctor(repo_root, strict=True) == 0


def test_doctor_adds_no_register_rule() -> None:
    # E7 is a CLI helper, not a rule: DOCTOR must not appear in the rule registry.
    import importlib

    import seshat.rules  # noqa: F401
    from seshat import registry

    importlib.reload(seshat.rules)
    ids = {r.id for r in registry.all_rules()}
    assert "DOCTOR" not in ids
