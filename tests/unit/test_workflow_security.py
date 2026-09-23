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
        # The whole seshat package, not just dbt/ and dagster_adapter/: the project
        # imports seshat.cli.commands.dbt at module scope (and more seshat modules
        # lazily), so a rename anywhere under src/seshat can break it.
        assert "src/seshat/**" in paths
        assert "pyproject.toml" in paths

    job = workflow["jobs"]["definitions-load-smoke"]
    assert isinstance(job.get("timeout-minutes"), int)
    assert job["timeout-minutes"] > 0


def _seshat_imports_of_the_orchestration_project() -> set[str]:
    import ast

    modules: set[str] = set()
    src = ROOT / "orchestration/dagster/src"
    for path in sorted(src.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            modules.update(n for n in names if n.split(".")[0] == "seshat")
    return modules


def test_dagster_smoke_paths_cover_every_seshat_module_the_project_imports() -> None:
    """Tripwire on the capability, not the filter's shape: every seshat module the
    orchestration src imports must sit under a dagster-smoke trigger path."""
    import fnmatch

    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/dagster-smoke.yml").read_text(encoding="utf-8")
    )
    triggers = workflow.get("on", workflow.get(True))
    imported = _seshat_imports_of_the_orchestration_project()
    assert imported, "expected the orchestration project to import seshat modules"
    for event in ("push", "pull_request"):
        patterns = triggers[event]["paths"]
        for module in sorted(imported):
            path = "src/" + module.replace(".", "/") + ".py"
            assert any(fnmatch.fnmatch(path, pattern) for pattern in patterns), (
                event,
                module,
            )


def _workflows() -> dict[str, dict]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
    }


def test_every_checkout_drops_the_persisted_token() -> None:
    """PR code and third-party build tooling run after checkout in every job; the
    job token must not sit in .git/config for them to lift."""
    for name, workflow in _workflows().items():
        for job_name, job in workflow.get("jobs", {}).items():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    settings = step.get("with") or {}
                    assert settings.get("persist-credentials") is False, (
                        name,
                        job_name,
                    )


def test_release_prep_token_reaches_only_the_push_and_pr_steps() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/prepare-coordinated-release.yml").read_text(
            encoding="utf-8"
        )
    )
    steps = workflow["jobs"]["prepare-release-pr"]["steps"]
    token_steps = [
        str(step.get("name"))
        for step in steps
        if "github.token" in str(step.get("env", {}))
        or "secrets.GITHUB_TOKEN" in str(step.get("env", {}))
    ]
    assert token_steps == [
        "Commit generated bundles and push the release branch",
        "Open a draft release pull request",
    ]
    push = next(s for s in steps if s.get("name") == token_steps[0])["run"]
    assert "git push" in push and "GIT_CONFIG_VALUE_0" in push
    assert "::add-mask::" in push


def test_publication_guards_are_identical_in_every_publish_job() -> None:
    """The fork/non-tag guard is copied into each publish job; a hardening applied
    to one copy only would leave the others publishing under the weaker guard."""
    workflow = _workflows()["release.yml"]
    guards = {}
    for job_name, job in workflow["jobs"].items():
        if not job_name.startswith("publish-"):
            continue
        matches = [
            s
            for s in job["steps"]
            if s.get("name") == "Reject forks and non-tag publication"
        ]
        assert len(matches) == 1, job_name
        guards[job_name] = (matches[0].get("env"), matches[0].get("run"))
    assert len(guards) >= 3, sorted(guards)
    assert len(set(map(repr, guards.values()))) == 1, sorted(guards)


def test_dep_integrity_exports_no_unused_token() -> None:
    text = (ROOT / ".github/workflows/dep-integrity.yml").read_text(encoding="utf-8")
    assert "GH_TOKEN" not in text
    assert "secrets.GITHUB_TOKEN" not in text
