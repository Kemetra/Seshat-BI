"""Load and validate a journey manifest. Fails closed on anything ambiguous."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.adopter_sim.model import (
    EXPECTED_BEHAVIORS,
    AdopterSimError,
    Journey,
    JourneyStep,
)


def load_journey(path: Path) -> Journey:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AdopterSimError(f"cannot read journey {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AdopterSimError(f"journey {path} is not a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise AdopterSimError(f"journey {path} has no name")
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise AdopterSimError(f"journey {path} has no steps")

    steps = tuple(_step(entry, path) for entry in raw_steps)
    _validate_dependencies(steps, path)
    return Journey(name=name, steps=steps)


def _step(entry: object, path: Path) -> JourneyStep:
    if not isinstance(entry, dict):
        raise AdopterSimError(f"journey {path} has a non-mapping step")
    number = entry.get("number")
    title = entry.get("title")
    if not isinstance(number, int) or not isinstance(title, str):
        raise AdopterSimError(f"journey {path} step needs int number and str title")
    prompt = entry.get("prompt")
    command = entry.get("command")
    if prompt is None and command is None:
        raise AdopterSimError(f"step {number} needs a prompt or command")
    if prompt is not None and command is not None:
        raise AdopterSimError(f"step {number} has both a prompt and a command")
    behavior = entry.get("expected_behavior")
    if behavior is not None and behavior not in EXPECTED_BEHAVIORS:
        raise AdopterSimError(
            f"step {number} expected_behavior {behavior!r} is outside the "
            f"categorical set {sorted(EXPECTED_BEHAVIORS)}"
        )
    depends_on = entry.get("depends_on", [])
    if not isinstance(depends_on, list) or not all(
        isinstance(item, int) for item in depends_on
    ):
        raise AdopterSimError(f"step {number} depends_on must be a list of ints")
    return JourneyStep(
        number=number,
        title=title,
        prompt=prompt,
        command=tuple(command) if command is not None else None,
        expected_behavior=behavior,
        depends_on=tuple(depends_on),
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
