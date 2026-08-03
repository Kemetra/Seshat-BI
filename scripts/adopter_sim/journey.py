"""Load and validate a journey manifest. Fails closed on anything ambiguous."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.adopter_sim.model import (
    EXPECTED_BEHAVIORS,
    AdopterSimError,
    Journey,
    JourneyStep,
)


def _document(path: Path) -> dict:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AdopterSimError(f"cannot read journey {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AdopterSimError(f"journey {path} is not a mapping")
    return raw


def _name(raw: dict, path: Path) -> str:
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise AdopterSimError(f"journey {path} has no name")
    return name


def _raw_steps(raw: dict, path: Path) -> list:
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise AdopterSimError(f"journey {path} has no steps")
    return raw_steps


def load_journey(path: Path) -> Journey:
    raw = _document(path)
    name = _name(raw, path)
    steps = tuple(_step(entry, path) for entry in _raw_steps(raw, path))
    _validate_dependencies(steps, path)
    return Journey(name=name, steps=steps)


def _identity(entry: dict, path: Path) -> tuple[int, str]:
    number = entry.get("number")
    title = entry.get("title")
    if not isinstance(number, int) or not isinstance(title, str):
        raise AdopterSimError(f"journey {path} step needs int number and str title")
    return number, title


def _action(entry: dict, number: int) -> tuple[str | None, tuple[str, ...] | None]:
    """Exactly one of prompt (agent-driven) or command (CLI)."""
    prompt = entry.get("prompt")
    command = entry.get("command")
    if prompt is None and command is None:
        raise AdopterSimError(f"step {number} needs a prompt or command")
    if prompt is not None and command is not None:
        raise AdopterSimError(f"step {number} has both a prompt and a command")
    return prompt, tuple(command) if command is not None else None


def _behavior(entry: dict, number: int) -> str | None:
    behavior = entry.get("expected_behavior")
    if behavior is not None and behavior not in EXPECTED_BEHAVIORS:
        raise AdopterSimError(
            f"step {number} expected_behavior {behavior!r} is outside the "
            f"categorical set {sorted(EXPECTED_BEHAVIORS)}"
        )
    return behavior


def _depends_on(entry: dict, number: int) -> tuple[int, ...]:
    depends_on = entry.get("depends_on", [])
    if not isinstance(depends_on, list) or not all(
        isinstance(item, int) for item in depends_on
    ):
        raise AdopterSimError(f"step {number} depends_on must be a list of ints")
    return tuple(depends_on)


def _str_list(entry: dict, key: str, number: int) -> tuple[str, ...]:
    values = entry.get(key, [])
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise AdopterSimError(f"step {number} {key} must be a list of strings")
    return tuple(values)


def _postconditions(entry: dict, number: int) -> dict[str, tuple[str, ...]]:
    conditions = {
        key: _str_list(entry, key, number)
        for key in ("expect_artifacts", "forbid_artifacts", "must_mention")
    }
    patterns = _str_list(entry, "forbid_patterns", number)
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise AdopterSimError(
                f"step {number} forbid_patterns entry {pattern!r} is not a valid "
                f"regex: {exc}"
            ) from exc
    conditions["forbid_patterns"] = patterns
    return conditions


def _step(entry: object, path: Path) -> JourneyStep:
    if not isinstance(entry, dict):
        raise AdopterSimError(f"journey {path} has a non-mapping step")
    number, title = _identity(entry, path)
    prompt, command = _action(entry, number)
    return JourneyStep(
        number=number,
        title=title,
        prompt=prompt,
        command=command,
        expected_behavior=_behavior(entry, number),
        depends_on=_depends_on(entry, number),
        **_postconditions(entry, number),
    )


def _validate_dependencies(steps: tuple[JourneyStep, ...], path: Path) -> None:
    numbers = [step.number for step in steps]
    if len(set(numbers)) != len(numbers):
        raise AdopterSimError(f"journey {path} repeats a step number")
    known: set[int] = set()
    for step in steps:
        for parent in step.depends_on:
            if parent == step.number:
                raise AdopterSimError(f"step {step.number} depends_on itself (a cycle)")
            if parent not in known:
                raise AdopterSimError(
                    f"step {step.number} depends_on {parent}, which is not an "
                    "earlier step (forward reference, unknown step, or a cycle)"
                )
        known.add(step.number)
    _reject_cycles(steps)


def _reject_cycles(steps: tuple[JourneyStep, ...]) -> None:
    edges = {step.number: set(step.depends_on) for step in steps}
    resolved: set[int] = set()
    while True:
        ready = {n for n, parents in edges.items() if parents <= resolved} - resolved
        if not ready:
            break
        resolved |= ready
    unresolved = set(edges) - resolved
    if unresolved:
        raise AdopterSimError(
            f"journey has a depends_on cycle among steps {sorted(unresolved)}"
        )
