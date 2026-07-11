from pathlib import Path

import pytest

from seshat.cli.parser import _build_parser
from seshat.core import Finding, Severity
from seshat.review_integration import build_review_result, markdown_summary


def test_review_digest_ignores_finding_order(tmp_path: Path) -> None:
    findings = [
        Finding("S1", Severity.ERROR, "blocked", "warehouse/silver/x.sql"),
        Finding("I1", Severity.INFO, "inspected", "README.md"),
    ]
    a = build_review_result(findings, repo_root=tmp_path)
    b = build_review_result(reversed(findings), repo_root=tmp_path)
    assert a["result_digest"] == b["result_digest"]


def test_review_reports_blocker_stage_and_static_boundary(tmp_path: Path) -> None:
    result = build_review_result(
        [
            Finding(
                "S1", Severity.ERROR, "mapping is not cleared", "warehouse/silver/x.sql"
            )
        ],
        repo_root=tmp_path,
        next_actions=["clear Mapping Ready with a named human review"],
    )
    assert result["outcome"] == "blocked"
    assert result["affected_stages"] == ["silver_ready"]
    assert result["run_boundary"] == {
        "static_checks": "blocked",
        "live_validation": "not_run",
        "semantic_correctness_claimed": False,
    }


def test_review_markdown_is_compact_and_actionable(tmp_path: Path) -> None:
    result = build_review_result(
        [Finding("S1", Severity.ERROR, "blocked", "silver.sql")],
        repo_root=tmp_path,
        next_actions=["return to mapping"],
    )
    summary = markdown_summary(result)
    assert "Seshat BI review: BLOCKED" in summary
    assert "return to mapping" in summary
    assert "semantic correctness were not claimed" in summary


def test_review_changed_state_from_commit_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Result:
        returncode = 0
        stdout = "mappings/orders/readiness-status.yaml\nwarehouse/gold/orders.sql\n"

    monkeypatch.setattr(
        "seshat.review_integration.subprocess.run", lambda *a, **k: Result()
    )
    result = build_review_result([], repo_root=tmp_path, commit_range="base..head")
    assert result["changed_readiness_state"] == [
        "mappings/orders/readiness-status.yaml"
    ]
    assert "gold_ready" in result["affected_stages"]


def test_invalid_commit_range_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Result:
        returncode = 128
        stdout = ""

    monkeypatch.setattr(
        "seshat.review_integration.subprocess.run", lambda *a, **k: Result()
    )
    with pytest.raises(ValueError, match="could not be inspected"):
        build_review_result([], repo_root=tmp_path, commit_range="bad")


def test_only_check_receives_review_formats() -> None:
    parser = _build_parser()
    assert parser.parse_args(["check", "--format", "review"]).output_format == "review"
    with pytest.raises(SystemExit):
        parser.parse_args(["status", "--format", "review"])
