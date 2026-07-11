from pathlib import Path

from seshat.core import Finding, Severity
from seshat.review_integration import build_review_result

ROOT = Path(__file__).resolve().parents[2]


def test_action_is_read_only_and_requires_exact_version() -> None:
    action = (ROOT / "integrations/github-action/action.yml").read_text(
        encoding="utf-8"
    )
    entrypoint = (ROOT / "integrations/github-action/entrypoint.ps1").read_text(
        encoding="utf-8"
    )
    assert "seshat-version:" in action
    assert "required: true" in action
    assert "pull-requests: write" not in action
    assert "github-token" not in action.lower()
    assert "seshat-bi==$($env:SESHAT_VERSION)" in entrypoint


def test_compliant_and_hard_stop_results_are_distinct(tmp_path: Path) -> None:
    compliant = build_review_result([], repo_root=tmp_path)
    hard_stop = build_review_result(
        [
            Finding(
                "S1", Severity.ERROR, "silver before mapping", "warehouse/silver/x.sql"
            )
        ],
        repo_root=tmp_path,
    )
    assert compliant["outcome"] == "ok"
    assert hard_stop["outcome"] == "blocked"
    assert compliant["result_digest"] != hard_stop["result_digest"]


def test_action_retains_json_when_sarif_is_disabled() -> None:
    entrypoint = (ROOT / "integrations/github-action/entrypoint.ps1").read_text(
        encoding="utf-8"
    )
    assert 'if ($env:SESHAT_SARIF -ne "false")' in entrypoint
    assert "seshat-review.json" in entrypoint
    assert "exit $reviewExit" in entrypoint


def test_action_contract_has_input_defect_and_summary_fallback() -> None:
    entrypoint = (ROOT / "integrations/github-action/entrypoint.ps1").read_text(
        encoding="utf-8"
    )
    assert "must be an exact immutable version" in entrypoint
    assert "$env:GITHUB_STEP_SUMMARY" in entrypoint
    assert "$summary | Write-Output" in entrypoint
