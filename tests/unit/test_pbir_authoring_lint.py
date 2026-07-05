"""Unit tests for R2 (PBIR report.json authoring-lint)."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.pbir import check_pbir_report_authoring

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"


def _ctx(report: str) -> RuleContext:
    return RuleContext(
        repo_root=FIXTURES,
        tracked_files=(f"{report}/definition/report.json",),
    )


def test_clean_report_passes() -> None:
    assert list(check_pbir_report_authoring(_ctx("r2_clean.Report"))) == []


def test_missing_basetheme_reference_fails() -> None:
    findings = list(check_pbir_report_authoring(_ctx("r2_missingref.Report")))
    assert len(findings) == 1
    assert findings[0].rule_id == "R2"
    assert findings[0].severity is Severity.ERROR
    assert "does not exist" in findings[0].message


def test_forbidden_business_key_fails() -> None:
    findings = list(check_pbir_report_authoring(_ctx("r2_forbidden.Report")))
    assert any(f.rule_id == "R2" for f in findings)
    assert any("forbidden business-logic key" in f.message for f in findings)


def test_invalid_json_fails() -> None:
    findings = list(check_pbir_report_authoring(_ctx("r2_badjson.Report")))
    assert len(findings) == 1
    assert findings[0].rule_id == "R2"
    assert "valid JSON" in findings[0].message


def test_no_report_json_is_silent() -> None:
    ctx = RuleContext(repo_root=FIXTURES, tracked_files=("warehouse/x.sql",))
    assert list(check_pbir_report_authoring(ctx)) == []


def test_tests_prefixed_report_is_exempted() -> None:
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=(
            "tests/fixtures/pbir/r2_forbidden.Report/definition/report.json",
        ),
    )
    assert list(check_pbir_report_authoring(ctx)) == []
