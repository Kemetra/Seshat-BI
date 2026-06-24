"""TDD tests for G6 -- no real host/value in committed PBIP parameters.

Power BI Desktop re-writes the real DB host/database into the tracked
expressions.tmdl on every "Edit Parameters -> save". C2 catches a DigitalOcean
endpoint specifically; G6 fails closed on ANY non-placeholder value in a PBIP
M parameter (IsParameterQuery=true), so the recurring leak is blocked at the gate
regardless of host. A committed parameter value MUST be the <placeholder> form.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.g6 import check_pbip_param_no_real_value

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbip_params"

pytestmark = pytest.mark.unit


def _ctx(model_dir: str) -> RuleContext:
    return RuleContext(
        repo_root=FIXTURES,
        tracked_files=(f"{model_dir}/definition/expressions.tmdl",),
    )


def test_placeholder_values_pass() -> None:
    # "<your-db-host>" / "<your-database>" are placeholders -> no finding.
    assert list(check_pbip_param_no_real_value(_ctx("clean.SemanticModel"))) == []


def test_real_host_and_db_fail() -> None:
    findings = list(check_pbip_param_no_real_value(_ctx("leak.SemanticModel")))
    # both Server (real host) and Database (real name) are non-placeholder -> 2 findings
    assert len(findings) == 2
    assert all(f.rule_id == "G6" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    # locator is path:lineno (consistent with C2); the param name is in the message
    messages = " ".join(f.message for f in findings)
    assert "Server" in messages
    assert "Database" in messages
    locators = " ".join(f.locator for f in findings)
    assert "expressions.tmdl:1" in locators
    assert "expressions.tmdl:6" in locators


def test_real_host_message_names_the_param_and_placeholder() -> None:
    findings = list(check_pbip_param_no_real_value(_ctx("leak.SemanticModel")))
    msg = findings[0].message
    assert "Server" in msg
    # the message should steer the fix: use the placeholder / set values at refresh
    assert "placeholder" in msg.lower() or "parameter" in msg.lower()


def test_test_fixtures_are_exempt() -> None:
    # A leaked value UNDER tests/ must NOT fire (fixtures intentionally carry it).
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=("tests/fixtures/x.SemanticModel/definition/expressions.tmdl",),
    )
    assert list(check_pbip_param_no_real_value(ctx)) == []


def test_only_scans_parameter_expressions() -> None:
    # A normal (non-IsParameterQuery) shared expression with a literal must NOT
    # fire -- G6 targets connection PARAMETERS, not every M expression.
    d = FIXTURES / "nonparam.SemanticModel" / "definition"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "expressions.tmdl"
    f.write_text(
        'expression FxRate = "1.0" meta [IsParameterQuery=false, Type="Text"]\n',
        encoding="utf-8",
    )
    try:
        findings = list(check_pbip_param_no_real_value(_ctx("nonparam.SemanticModel")))
        assert findings == []
    finally:
        f.unlink()
        d.rmdir()
        d.parent.rmdir()
