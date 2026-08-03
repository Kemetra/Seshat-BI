from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_VALID = """\
version: 1
name: synthetic
steps:
  - number: 1
    title: "Install check"
    command: ["seshat", "--version"]
    depends_on: []
  - number: 2
    title: "Orient"
    prompt: "Where do I start?"
    depends_on: [1]
  - number: 3
    title: "Scaffold"
    command: ["seshat", "scaffold-source", "orders"]
    expected_behavior: proceed
    depends_on: [1]
  - number: 4
    title: "Profile"
    prompt: "Profile the table."
    expected_behavior: block_for_evidence
    depends_on: [3]
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "journey.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_journey_loads(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.name == "synthetic"
    assert len(journey.steps) == 4
    assert journey.step(4).expected_behavior == "block_for_evidence"


def test_prompt_steps_are_agent_driven(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.step(2).agent_driven is True
    assert journey.step(1).agent_driven is False


def test_dependents_are_transitive(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.dependents_of(1) == (2, 3, 4)
    assert journey.dependents_of(3) == (4,)


def test_unknown_expected_behavior_fails_closed(tmp_path: Path) -> None:
    text = _VALID.replace("expected_behavior: proceed", "expected_behavior: maybe")
    with pytest.raises(AdopterSimError, match="expected_behavior"):
        load_journey(_write(tmp_path, text))


def test_forward_reference_fails_closed(tmp_path: Path) -> None:
    text = _VALID.replace(
        "depends_on: [1]\n  - number: 3", "depends_on: [9]\n  - number: 3"
    )
    with pytest.raises(AdopterSimError, match="depends_on"):
        load_journey(_write(tmp_path, text))


def test_dependency_cycle_fails_closed(tmp_path: Path) -> None:
    text = """\
version: 1
name: cyclic
steps:
  - number: 1
    title: "A"
    prompt: "a"
    depends_on: [2]
  - number: 2
    title: "B"
    prompt: "b"
    depends_on: [1]
"""
    with pytest.raises(AdopterSimError, match="depends_on"):
        load_journey(_write(tmp_path, text))


def test_step_needs_prompt_or_command(tmp_path: Path) -> None:
    text = """\
version: 1
name: empty
steps:
  - number: 1
    title: "Nothing"
    depends_on: []
"""
    with pytest.raises(AdopterSimError, match="prompt or command"):
        load_journey(_write(tmp_path, text))


def test_shipped_first_hour_journey_loads() -> None:
    journey = load_journey(_REPO / "benchmark/journeys/first-hour.yaml")
    assert journey.name == "first-hour"
    assert len(journey.steps) == 7
    # Steps 1-2 carry no declared outcome (spec: category error); 3-7 do.
    assert journey.step(1).expected_behavior is None
    assert journey.step(2).expected_behavior is None
    assert all(journey.step(n).expected_behavior for n in (3, 4, 5, 6, 7))
