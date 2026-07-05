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


def test_forbidden_definition_key_fails() -> None:
    findings = list(check_pbir_report_authoring(_ctx("r2_forbidden.Report")))
    # r2_forbidden has `measureDefinition` (a DEFINITION) -> must fire, and the
    # locator must point at that specific key (pin it, not just any finding).
    defn = [f for f in findings if f.locator.endswith("/measureDefinition")]
    assert len(defn) == 1
    assert defn[0].rule_id == "R2"
    assert "DEFINES business logic" in defn[0].message


def test_data_bound_reference_passes() -> None:
    # A legitimate report REFERENCES a measure via the query-grammar wrapper keys
    # `Measure`/`Expression` (a filter bound to a measure). These are references,
    # NOT definitions -- R2 must NOT fire (else the gate breaks on the first real
    # report). This is the false-positive regression guard.
    findings = list(check_pbir_report_authoring(_ctx("r2_databound.Report")))
    assert findings == [], f"R2 false-positived on a data-bound reference: {findings}"


def test_missing_schema_fails() -> None:
    findings = list(check_pbir_report_authoring(_ctx("r2_noschema.Report")))
    assert len(findings) == 1
    assert findings[0].rule_id == "R2"
    assert "$schema" in findings[0].message


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
