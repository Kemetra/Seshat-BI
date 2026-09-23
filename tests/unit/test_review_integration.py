from pathlib import Path

import pytest

from seshat.cli.parser import _build_parser
from seshat.core import Finding, Severity
from seshat.review_integration import build_review_result, markdown_summary

pytestmark = pytest.mark.unit


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
        # `git diff --name-only -z`: NUL-separated, so non-ASCII paths stay intact.
        stdout = "mappings/orders/readiness-status.yaml\0warehouse/gold/orders.sql\0"

    monkeypatch.setattr(
        "seshat.review_integration.run_subprocess", lambda *a, **k: Result()
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
        "seshat.review_integration.run_subprocess", lambda *a, **k: Result()
    )
    with pytest.raises(ValueError, match="could not be inspected"):
        build_review_result([], repo_root=tmp_path, commit_range="bad")


def test_only_check_receives_review_formats() -> None:
    parser = _build_parser()
    assert parser.parse_args(["check", "--format", "review"]).output_format == "review"
    with pytest.raises(SystemExit):
        parser.parse_args(["status", "--format", "review"])


@pytest.mark.parametrize("value", ["-n1", "--stat", "a..b\n"])
def test_option_shaped_commit_range_never_reaches_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    def must_not_run(*args, **kwargs):
        raise AssertionError(f"git ran with an unvalidated range: {args}")

    monkeypatch.setattr("seshat.review_integration.run_subprocess", must_not_run)
    with pytest.raises(ValueError, match="unsafe git commit range"):
        build_review_result([], repo_root=tmp_path, commit_range=value)


def test_review_format_refuses_option_shaped_range_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import json

    from seshat import cli

    monkeypatch.chdir(tmp_path)
    code = cli.main(
        ["check", "--repo", str(tmp_path), "--format", "review", "--commit-range=-n1"]
    )
    doc = json.loads(capsys.readouterr().out)
    assert code == 2
    assert doc["outcome"] == "input_defect"
    assert "unsafe git commit range" in doc["error"]
