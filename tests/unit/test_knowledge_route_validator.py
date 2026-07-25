"""Behavioral contract tests for knowledge-layer route validation."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_knowledge_routes.py"
SCENARIOS = ROOT / "tests" / "fixtures" / "knowledge-route-scenarios.yaml"


@dataclass(frozen=True)
class _RouteCase:
    repo_name: str
    index: str
    files: tuple[str, ...]
    scenarios: tuple[dict[str, object], ...]
    expected_returncode: int
    expected_findings: tuple[tuple[str, str], ...]


def _run_validator(repo: Path, scenarios: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--scenarios",
            str(scenarios),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_scenarios(path: Path, scenarios: list[dict[str, object]]) -> None:
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "scenarios": scenarios},
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _finding_codes(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [item["code"] for item in json.loads(result.stdout)]


def _scenario(
    task: str,
    resources: list[str],
    terminal: str = "profile verdict",
) -> dict[str, object]:
    return {
        "layer": "example-knowledge",
        "task_contains": task,
        "expect_resources": resources,
        "terminal_contains": terminal,
    }


def _run_route_case(
    tmp_path: Path,
    case: _RouteCase,
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / case.repo_name if case.repo_name else tmp_path
    layer = repo / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(case.index, encoding="utf-8")
    for relative_path in case.files:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Fixture\n", encoding="utf-8")
    scenario_path = repo / "scenarios.yaml"
    _write_scenarios(scenario_path, list(case.scenarios))
    return _run_validator(repo, scenario_path)


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            _RouteCase(
                repo_name="",
                index=(
                    "| Task | Open | End on |\n"
                    "|---|---|---|\n"
                    "| Profile data | `knowledge/profile.md` | profile verdict |\n"
                ),
                files=(),
                scenarios=(_scenario("Profile data", ["knowledge/profile.md"]),),
                expected_returncode=1,
                expected_findings=(("missing_resource", "knowledge/profile.md"),),
            ),
            id="missing-resource",
        ),
        pytest.param(
            _RouteCase(
                repo_name="",
                index=(
                    "| Task | Open | End on |\n"
                    "|---|---|---|\n"
                    "| Profile data | `knowledge/profile.md` | profile verdict |\n"
                ),
                files=("skills/example-knowledge/knowledge/profile.md",),
                scenarios=(_scenario("Profile data", ["knowledge/profile.md"]),),
                expected_returncode=0,
                expected_findings=(),
            ),
            id="complete-route",
        ),
        pytest.param(
            _RouteCase(
                repo_name="",
                index=(
                    "| Task | Open | End on |\n"
                    "|---|---|---|\n"
                    "| Profile daily data | `profile.md` | profile verdict |\n"
                    "| Profile monthly data | `profile.md` | profile verdict |\n"
                ),
                files=("skills/example-knowledge/profile.md",),
                scenarios=(
                    _scenario("Unknown task", ["profile.md"]),
                    _scenario("Profile", ["profile.md"]),
                ),
                expected_returncode=1,
                expected_findings=(
                    ("missing_route", ""),
                    ("ambiguous_route", ""),
                ),
            ),
            id="missing-and-ambiguous-routes",
        ),
        pytest.param(
            _RouteCase(
                repo_name="repo",
                index=(
                    "| Task | Open | End on |\n"
                    "|---|---|---|\n"
                    "| Profile data | `profile.md` | profile verdict |\n"
                    "| Inspect outside | `../../../outside.md` | profile verdict |\n"
                ),
                files=(
                    "repo/skills/example-knowledge/profile.md",
                    "repo/skills/example-knowledge/unlisted.md",
                    "outside.md",
                ),
                scenarios=(
                    _scenario("Profile data", ["unlisted.md"]),
                    _scenario("Inspect outside", ["../../../outside.md"]),
                ),
                expected_returncode=1,
                expected_findings=(
                    ("missing_resource_reference", "unlisted.md"),
                    ("unsafe_resource", "../../../outside.md"),
                ),
            ),
            id="unlisted-and-escaping-resources",
        ),
    ],
)
def test_route_validation_cases(
    tmp_path: Path,
    case: _RouteCase,
) -> None:
    result = _run_route_case(tmp_path, case)

    assert result.returncode == case.expected_returncode
    assert [
        (item["code"], item["resource"]) for item in json.loads(result.stdout)
    ] == list(case.expected_findings)


def test_missing_index_is_reported_categorically(tmp_path: Path) -> None:
    scenarios = tmp_path / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            {
                "layer": "missing-knowledge",
                "task_contains": "Profile data",
                "expect_resources": ["knowledge/profile.md"],
                "terminal_contains": "profile verdict",
            }
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert _finding_codes(result) == ["missing_index"]


def test_terminal_mismatch_is_reported(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    (layer / "profile.md").write_text("# Profile\n", encoding="utf-8")
    scenarios = tmp_path / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            _scenario(
                "Profile data",
                ["profile.md"],
                terminal="validation checklist",
            )
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert _finding_codes(result) == ["terminal_mismatch"]


def test_repository_routes_satisfy_reviewed_scenarios() -> None:
    result = _run_validator(ROOT, SCENARIOS)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == []
