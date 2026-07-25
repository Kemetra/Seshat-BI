"""Behavioral contract tests for knowledge-layer route validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_knowledge_routes.py"
SCENARIOS = ROOT / "tests" / "fixtures" / "knowledge-route-scenarios.yaml"


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


def test_missing_routed_resource_returns_finding(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `knowledge/profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    scenarios = tmp_path / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            {
                "layer": "example-knowledge",
                "task_contains": "Profile data",
                "expect_resources": ["knowledge/profile.md"],
                "terminal_contains": "profile verdict",
            }
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert [(item["code"], item["resource"]) for item in json.loads(result.stdout)] == [
        ("missing_resource", "knowledge/profile.md")
    ]


def test_complete_route_returns_no_findings(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    (layer / "knowledge").mkdir(parents=True)
    (layer / "knowledge" / "profile.md").write_text(
        "# Profile\n",
        encoding="utf-8",
    )
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `knowledge/profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    scenarios = tmp_path / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            {
                "layer": "example-knowledge",
                "task_contains": "Profile data",
                "expect_resources": ["knowledge/profile.md"],
                "terminal_contains": "profile verdict",
            }
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 0
    assert json.loads(result.stdout) == []


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


def test_missing_and_ambiguous_routes_are_distinct(tmp_path: Path) -> None:
    layer = tmp_path / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile daily data | `profile.md` | profile verdict |\n"
        "| Profile monthly data | `profile.md` | profile verdict |\n",
        encoding="utf-8",
    )
    (layer / "profile.md").write_text("# Profile\n", encoding="utf-8")
    scenarios = tmp_path / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            {
                "layer": "example-knowledge",
                "task_contains": "Unknown task",
                "expect_resources": ["profile.md"],
                "terminal_contains": "profile verdict",
            },
            {
                "layer": "example-knowledge",
                "task_contains": "Profile",
                "expect_resources": ["profile.md"],
                "terminal_contains": "profile verdict",
            },
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert _finding_codes(result) == ["missing_route", "ambiguous_route"]


def test_unlisted_and_escaping_resources_are_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    layer = repo / "skills" / "example-knowledge"
    layer.mkdir(parents=True)
    (layer / "INDEX.md").write_text(
        "| Task | Open | End on |\n"
        "|---|---|---|\n"
        "| Profile data | `profile.md` | profile verdict |\n"
        "| Inspect outside | `../../../outside.md` | profile verdict |\n",
        encoding="utf-8",
    )
    (layer / "profile.md").write_text("# Profile\n", encoding="utf-8")
    (layer / "unlisted.md").write_text("# Unlisted\n", encoding="utf-8")
    (tmp_path / "outside.md").write_text("# Outside\n", encoding="utf-8")
    scenarios = repo / "scenarios.yaml"
    _write_scenarios(
        scenarios,
        [
            {
                "layer": "example-knowledge",
                "task_contains": "Profile data",
                "expect_resources": ["unlisted.md"],
                "terminal_contains": "profile verdict",
            },
            {
                "layer": "example-knowledge",
                "task_contains": "Inspect outside",
                "expect_resources": ["../../../outside.md"],
                "terminal_contains": "profile verdict",
            },
        ],
    )

    result = _run_validator(repo, scenarios)

    assert result.returncode == 1
    assert _finding_codes(result) == [
        "missing_resource_reference",
        "unsafe_resource",
    ]


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
            {
                "layer": "example-knowledge",
                "task_contains": "Profile data",
                "expect_resources": ["profile.md"],
                "terminal_contains": "validation checklist",
            }
        ],
    )

    result = _run_validator(tmp_path, scenarios)

    assert result.returncode == 1
    assert _finding_codes(result) == ["terminal_mismatch"]


def test_repository_routes_satisfy_reviewed_scenarios() -> None:
    result = _run_validator(ROOT, SCENARIOS)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == []
