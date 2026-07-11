"""Tests for E7 -- ``retail doctor`` read-only drift digest.

Doctor aggregates existing read-only checks + a load-bearing-doc probe into a
findings digest. It reads and reports, never fixes; emits no numeric score; is
advisory (exit 0) by default and only fails under --strict. It adds no @register
rule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext
from seshat.doctor import collect_findings, format_digest, run_doctor

pytestmark = pytest.mark.unit


def _ctx_missing_everything(tmp_path: Path) -> RuleContext:
    # A bare tmp dir: no tracked files at all -> the load-bearing probe + the
    # manifest-dependent checks all fire (fail-loud), giving a non-empty digest.
    return RuleContext(repo_root=tmp_path, tracked_files=())


def test_collect_findings_on_empty_repo_reports_drift(tmp_path: Path) -> None:
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    assert findings, "an empty repo should surface load-bearing-doc + manifest findings"
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
