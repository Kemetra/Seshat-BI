from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# tests/unit/test_cseam.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEP_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dep-integrity.yml"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"


@pytest.mark.unit
def test_ci_workflow_parses_and_references_retail_check() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)  # raises if the YAML is invalid
    assert parsed is not None
    assert "retail check" in text


@pytest.mark.unit
def test_ci_keeps_required_check_present_while_gating_heavy_jobs() -> None:
    """Docs-only PRs must report CI success without running code-heavy jobs."""

    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert workflow["permissions"] == {"contents": "read"}
    assert jobs["changes"]["outputs"]["code_changed"]
    assert jobs["changes"]["outputs"]["contracts_required"]
    assert jobs["check"]["needs"] == "changes"

    heavy_jobs = {
        "statistics",
        "report-surfaces",
        "smoke",
        "smoke-unix",
        # The Windows unit leg (#698) is as heavy as `check` and must stay
        # docs-only-gated like every other code-heavy job.
        "unit-windows",
        "agent-distribution",
        "integration",
    }
    for job_name in heavy_jobs:
        job = jobs[job_name]
        assert job["needs"] == "changes", job_name
        assert "needs.changes.outputs.code_changed == 'true'" in job["if"], job_name

    integration_steps = jobs["integration"]["steps"]
    integration_command = "\n".join(
        str(step.get("run", "")) for step in integration_steps
    )
    assert 'pytest -m "integration and not live_db and not statistics"' in (
        integration_command
    )

    expensive_check_steps = {
        "Ruff format check",
        "Ruff lint",
        "Build the Studio frontend",
        "Unit tests",
        "Governed dbt adapter contract",
        "Public distribution contract tests",
    }
    for step in jobs["check"]["steps"]:
        if step.get("name") in expensive_check_steps:
            assert "needs.changes.outputs.code_changed == 'true'" in step.get(
                "if", ""
            ), step["name"]


@pytest.mark.unit
def test_ci_runs_every_unmarked_non_live_test_in_a_contract_surface() -> None:
    """A missing marker must select a safe default lane, never disappear from CI."""

    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["contract-surfaces"]

    assert job["needs"] == "changes"
    assert "needs.changes.outputs.contracts_required == 'true'" in job["if"]
    commands = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert (
        'pytest -m "not unit and not integration and not live_db and not statistics"'
        in commands
    )
    assert ".[dev,stats,stats-change,studio,mcp,report,files]" in commands
    assert "tests/unit/test_studio_*.py" in commands
    assert "tests/unit/test_report_*.py" in commands
    assert "tests/unit/test_cli_profile_file.py" in commands
    assert "tests/integration/test_governor_stdio_no_deadlock.py" in commands
    names = [str(step.get("name", "")) for step in job["steps"]]
    assert names.index("Build the Studio frontend") < names.index(
        "Unmarked credential-free contract tests"
    )

    report_commands = "\n".join(
        str(step.get("run", ""))
        for step in workflow["jobs"]["report-surfaces"]["steps"]
    )
    assert "tests/integration/test_demo_html_browser.py" in report_commands
    assert "tests/integration/test_explorer_browser.py" in report_commands
    assert "tests/integration/test_showcase_a11y_rtl.py" in report_commands


@pytest.mark.unit
def test_ci_uses_the_smallest_install_and_reuses_python_downloads() -> None:
    """Prose checks need the package core, while code checks need dev tooling."""

    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    check_steps = workflow["jobs"]["check"]["steps"]
    installs = {
        step.get("name"): step
        for step in check_steps
        if "Install" in step.get("name", "")
    }

    assert installs["Install package core"]["run"] == "pip install -e ."
    assert (
        "needs.changes.outputs.code_changed != 'true'"
        in installs["Install package core"]["if"]
    )
    assert (
        installs["Install development environment"]["run"] == 'pip install -e ".[dev]"'
    )
    assert (
        "needs.changes.outputs.code_changed == 'true'"
        in installs["Install development environment"]["if"]
    )

    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/setup-python@"):
                assert step.get("with", {}).get("cache") == "pip", job_name
                assert step["with"].get("cache-dependency-path") == "pyproject.toml", (
                    job_name
                )


@pytest.mark.unit
def test_ci_jobs_have_bounded_runtime_and_commenting_is_isolated() -> None:
    """A hung tool must time out, and PR write access must stay out of test jobs."""

    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    for job_name, job in jobs.items():
        assert isinstance(job.get("timeout-minutes"), int), job_name
        assert job["timeout-minutes"] > 0, job_name

    commenter = jobs["friendly-pr-summary"]
    assert commenter["permissions"] == {
        "contents": "read",
        "pull-requests": "write",
    }
    for job_name, job in jobs.items():
        if job_name != "friendly-pr-summary":
            assert job.get("permissions") != commenter["permissions"], job_name


@pytest.mark.unit
def test_docs_only_pr_skips_network_dependency_resolution() -> None:
    """A prose-only PR must not spend a runner resolving every optional extra."""

    workflow = yaml.safe_load(DEP_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert jobs["changes"]["outputs"]["code_changed"]
    assert jobs["co-resolution"]["needs"] == "changes"
    assert "needs.changes.outputs.code_changed == 'true'" in jobs["co-resolution"]["if"]


@pytest.mark.unit
def test_pre_commit_config_parses_and_references_retail_check() -> None:
    text = PRE_COMMIT.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)  # raises if the YAML is invalid
    assert parsed is not None
    assert "retail check" in text
    hooks = {
        hook["id"]: hook
        for repository in parsed["repos"]
        for hook in repository["hooks"]
    }
    commit_message = hooks["retail-commit-message"]
    assert commit_message["entry"] == "retail check --commit-msg-file"
    assert commit_message["stages"] == ["commit-msg"]
