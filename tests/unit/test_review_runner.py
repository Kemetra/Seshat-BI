import json
from pathlib import Path

from seshat.core import Finding, RegisteredRule, RuleContext, Severity
from seshat.runner import run_review, run_sarif


def _rules() -> tuple[RegisteredRule, ...]:
    return (
        RegisteredRule(
            id="S1",
            title="premature silver",
            rule=lambda _ctx: [
                Finding(
                    "S1",
                    Severity.ERROR,
                    "mapping is not cleared",
                    "warehouse/silver/orders.sql:1",
                )
            ],
        ),
    )


def test_review_runner_preserves_blocking_exit_code(
    tmp_path: Path, capsys: object
) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    assert run_review(_rules(), ctx) == 1
    document = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert document["outcome"] == "blocked"
    assert document["exit_code"] == 1
    assert document["run_boundary"]["live_validation"] == "not_run"


def test_sarif_runner_preserves_blocking_exit_code(
    tmp_path: Path, capsys: object
) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    assert run_sarif(_rules(), ctx) == 1
    document = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert document["version"] == "2.1.0"
    assert document["runs"][0]["results"][0]["ruleId"] == "S1"
