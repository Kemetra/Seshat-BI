"""Supply-chain guardrails for the Dagster smoke workflow."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_every_workflow_job_has_a_bounded_runtime() -> None:
    """Network and browser operations must not consume the runner maximum."""

    for workflow_path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        for job_name, job in workflow.get("jobs", {}).items():
            assert isinstance(job.get("timeout-minutes"), int), (
                workflow_path.name,
                job_name,
            )
            assert job["timeout-minutes"] > 0, (workflow_path.name, job_name)


def test_dagster_smoke_pins_actions_and_minimizes_permissions() -> None:
    text = (ROOT / ".github/workflows/dagster-smoke.yml").read_text(encoding="utf-8")

    assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0" in text
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in text
    assert "permissions:" in text and "contents: read" in text
    assert "actions/checkout@v" not in text
    assert "actions/setup-python@v" not in text


def test_dagster_smoke_runs_when_its_root_dbt_runtime_changes() -> None:
    """The smoke imports seshat.dbt, so changes to that runtime must trigger it."""

    workflow_path = ROOT / ".github/workflows/dagster-smoke.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))

    for event in ("push", "pull_request"):
        paths = set(triggers[event]["paths"])
        assert "src/seshat/dbt/**" in paths
        assert "pyproject.toml" in paths

    job = workflow["jobs"]["definitions-load-smoke"]
    assert isinstance(job.get("timeout-minutes"), int)
    assert job["timeout-minutes"] > 0
