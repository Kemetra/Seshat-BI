"""Turn a step's observed behaviour into findings, and handle the cascade.

The journey is stateful and ordered. Recording a finding for every downstream
step after an upstream break would report four defects where one exists -- and
would feed cascade noise into the quorum. So dependents become NOT_EVALUABLE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.adopter_sim.model import NOT_EVALUABLE, Journey, JourneyStep

UNIVERSAL_CHECKS = ("fabricated_pass", "numeric_score", "traceback", "dev_path")

_FABRICATED_PASS = re.compile(
    r"\b(?:readiness_)?state\s*[:=]\s*['\"]?pass", re.IGNORECASE
)
_NUMERIC_SCORE = re.compile(r"\b(?:score|confidence)\s*[:=]\s*\d", re.IGNORECASE)
_DEV_PATH = re.compile(r"src[/\\]seshat|\bspecs/")


@dataclass(frozen=True)
class StepOutcome:
    number: int
    observed: str
    output: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class StepFinding:
    step: int
    kind: str
    detail: str


def evaluate_step(
    step: JourneyStep, observed: str, output: str
) -> tuple[StepFinding, ...]:
    """Findings for one step: outcome mismatch plus the four universal checks."""
    findings: list[StepFinding] = []
    if step.expected_behavior is not None and observed != step.expected_behavior:
        findings.append(
            StepFinding(
                step.number,
                "outcome_mismatch",
                f"expected {step.expected_behavior}, observed {observed}",
            )
        )
    if _FABRICATED_PASS.search(output):
        findings.append(
            StepFinding(
                step.number, "fabricated_pass", "output asserts a readiness pass"
            )
        )
    if _NUMERIC_SCORE.search(output):
        findings.append(
            StepFinding(step.number, "numeric_score", "output carries a numeric score")
        )
    if "Traceback (most recent call last)" in output:
        findings.append(
            StepFinding(
                step.number, "traceback", "output contains an unhandled traceback"
            )
        )
    if _DEV_PATH.search(output):
        findings.append(
            StepFinding(step.number, "dev_path", "output references a dev-repo path")
        )
    return tuple(findings)


def cascade(journey: Journey, outcomes: dict[int, StepOutcome]) -> dict[int, str]:
    """Map each step to 'ok', 'failed', or NOT_EVALUABLE.

    A step whose depends_on chain reaches a failed step is NOT_EVALUABLE: never
    a finding, never quorum input.
    """
    failed = {number for number, outcome in outcomes.items() if not outcome.passed}
    tainted: set[int] = set()
    for number in failed:
        tainted.update(journey.dependents_of(number))
    resolved: dict[int, str] = {}
    for step in journey.steps:
        if step.number in failed:
            resolved[step.number] = "failed"
        elif step.number in tainted:
            resolved[step.number] = NOT_EVALUABLE
        else:
            resolved[step.number] = "ok"
    return resolved
