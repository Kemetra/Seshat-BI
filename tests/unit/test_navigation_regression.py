"""F1 -- navigation regression harness.

The COMPASS fast-routing table (`COMPASS.md` "## Fast routing") is the agent's
first-hop dispatch: a task type -> the Route file(s) to open. Nothing mechanically
guaranteed those Route targets still resolve on disk and stay consistent with the
`docs/routing/routes.yaml` registry (A1 guards the registry; nothing guarded the
COMPASS prose table that mirrors it). A rename that updated the registry but not
COMPASS (or vice-versa) would silently break first-hop navigation.

This harness closes that gap. It:
  1. extracts every backtick-quoted target path from the COMPASS fast-routing table,
  2. asserts each committed expectation (tests/fixtures/nav-scenarios.yaml) is named
     by the matching COMPASS row AND resolves as a tracked file,
  3. asserts every skill SKILL.md/INDEX.md COMPASS names also appears in the route
     registry's targets, so COMPASS and routes.yaml cannot drift apart.

Test-only: no `@register` rule, no rule-count change, no score. Read-only over
committed files. Fails closed on a rename/miss.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPASS = _REPO_ROOT / "COMPASS.md"
_ROUTES = _REPO_ROOT / "docs" / "routing" / "routes.yaml"
_SCENARIOS = _REPO_ROOT / "tests" / "fixtures" / "nav-scenarios.yaml"

# A backtick-quoted repo-relative path ending in a file extension we care about.
_TARGET_RE = re.compile(r"`([^`]+\.(?:md|yaml|json))`")


def _tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def _fast_routing_rows() -> list[tuple[str, list[str]]]:
    """Return (task_type_cell, [target paths]) for each fast-routing table row."""
    text = _COMPASS.read_text(encoding="utf-8")
    m = re.search(r"^##+\s*Fast routing\s*$", text, re.M)
    assert m, "COMPASS.md has no '## Fast routing' section"
    rest = text[m.end() :]
    rows: list[tuple[str, list[str]]] = []
    for line in rest.splitlines():
        s = line.strip()
        if s.startswith("##"):
            break  # next section ends the table
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        task = cells[0]
        if task.lower().startswith("task type") or set(task) <= {"-", ":"}:
            continue  # header / separator
        route_cell = cells[1]
        targets = _TARGET_RE.findall(route_cell)
        rows.append((task, targets))
    return rows


def _load_scenarios() -> list[dict]:
    data = yaml.safe_load(_SCENARIOS.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and isinstance(data.get("scenarios"), list)
    return data["scenarios"]


def _route_registry_targets() -> set[str]:
    data = yaml.safe_load(_ROUTES.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for route in data.get("routes", []):
        for t in route.get("targets", []) or []:
            targets.add(t)
    return targets


@pytest.mark.parametrize(
    "scenario", _load_scenarios(), ids=lambda s: s["task_contains"]
)
def test_compass_row_targets_resolve(scenario: dict) -> None:
    rows = _fast_routing_rows()
    needle = scenario["task_contains"]
    matches = [(task, targets) for task, targets in rows if needle in task]
    assert matches, f"no COMPASS fast-routing row contains {needle!r}"
    _, targets = matches[0]
    tracked = _tracked_files()
    for expected in scenario["expect_targets"]:
        assert expected in targets, (
            f"COMPASS row {needle!r} no longer names {expected!r} (names: {targets})"
        )
        assert expected in tracked, (
            f"COMPASS target {expected!r} for row {needle!r} is not a tracked file "
            f"-- navigation is broken"
        )


def test_compass_skill_targets_are_in_route_registry() -> None:
    """Every skill SKILL.md/INDEX.md COMPASS names must be in routes.yaml too."""
    rows = _fast_routing_rows()
    registry_targets = _route_registry_targets()
    missing: list[str] = []
    for _task, targets in rows:
        for t in targets:
            if t.startswith("skills/") and t.endswith(("SKILL.md", "INDEX.md")):
                if t not in registry_targets:
                    missing.append(t)
    assert not missing, (
        f"COMPASS names skill targets absent from docs/routing/routes.yaml: "
        f"{sorted(set(missing))} -- COMPASS and the route registry have drifted"
    )
