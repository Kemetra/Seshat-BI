from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.pbir import check_pbir_relative_reference

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"


def _ctx(report_dir: str) -> RuleContext:
    return RuleContext(
        repo_root=FIXTURES,
        tracked_files=(f"{report_dir}/definition.pbir",),
    )


@pytest.mark.unit
def test_relative_path_passes() -> None:
    findings = list(check_pbir_relative_reference(_ctx("relative.Report")))
    assert findings == []


@pytest.mark.unit
def test_absolute_path_fails() -> None:
    findings = list(check_pbir_relative_reference(_ctx("absolute.Report")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R1"
    assert f.severity is Severity.ERROR
    assert f.locator == "absolute.Report/definition.pbir#/datasetReference/byPath/path"
    assert "absolute" in f.message.lower()


@pytest.mark.unit
def test_byconnection_fails() -> None:
    findings = list(check_pbir_relative_reference(_ctx("byconn.Report")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R1"
    assert f.severity is Severity.ERROR
    assert f.locator == "byconn.Report/definition.pbir#/datasetReference/byConnection"
    assert "byconnection" in f.message.lower()


@pytest.mark.unit
def test_no_pbir_files_is_silent() -> None:
    ctx = RuleContext(repo_root=FIXTURES, tracked_files=("warehouse/x.sql",))
    assert list(check_pbir_relative_reference(ctx)) == []


@pytest.mark.unit
def test_tests_prefixed_pbir_is_exempted() -> None:
    # A .pbir under tests/ is an intentional bad fixture (absolute path here),
    # so R1 must NOT fire on it (centralized tests/ exemption, M6 follow-up).
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=("tests/fixtures/pbir/absolute.Report/definition.pbir",),
    )
    assert list(check_pbir_relative_reference(ctx)) == []


@pytest.mark.unit
def test_non_tests_absolute_pbir_still_fires() -> None:
    # The same absolute-path content under a NON-tests/ path is a real violation:
    # R1 must still flag it. (We point repo_root at FIXTURES and use a tracked
    # path whose basename resolves to the existing absolute.Report fixture.)
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=("absolute.Report/definition.pbir",),
    )
    findings = list(check_pbir_relative_reference(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "R1"
    assert findings[0].severity is Severity.ERROR
