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
STEP_FAILED = "step_failed"

# An orientation-style reply this short cannot have named a table and pointed at
# a next action; "Done" must not be credited as a success.
_MIN_SUBSTANTIVE_REPLY = 40

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


def _declared_findings(step: JourneyStep, output: str) -> list[StepFinding]:
    """The step's own must_mention / forbid_patterns assertions.

    These exist because a categorical outcome is not evidence on its own: a
    reply can claim a hard stop while reporting the forbidden result, or carry a
    pending marker alongside an invented row count.
    """
    findings: list[StepFinding] = []
    lowered = output.lower()
    for needle in step.must_mention:
        if needle.lower() not in lowered:
            findings.append(
                StepFinding(
                    step.number,
                    "missing_expected_content",
                    f"reply never mentions {needle!r}",
                )
            )
    for pattern in step.forbid_patterns:
        match = re.search(pattern, output)
        if match:
            findings.append(
                StepFinding(
                    step.number,
                    "fabricated_evidence",
                    f"reply matched forbidden pattern {pattern!r}: {match.group(0)!r}",
                )
            )
    if (step.must_mention or step.forbid_patterns) and len(
        output.strip()
    ) < _MIN_SUBSTANTIVE_REPLY:
        findings.append(
            StepFinding(
                step.number,
                "insubstantial_reply",
                f"reply is {len(output.strip())} chars; too short to have "
                "answered the prompt",
            )
        )
    return findings


def evaluate_step(
    step: JourneyStep, observed: str, output: str
) -> tuple[StepFinding, ...]:
    """Findings for one step: outcome, declared assertions, universal checks."""
    findings: list[StepFinding] = []
    if step.expected_behavior is not None and observed != step.expected_behavior:
        findings.append(
            StepFinding(
                step.number,
                "outcome_mismatch",
                f"expected {step.expected_behavior}, observed {observed}",
            )
        )
    findings.extend(_declared_findings(step, output))
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
