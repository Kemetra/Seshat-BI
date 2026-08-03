"""Shared builders for the adopter-sim tests.

Follows the repo's existing shared-helper convention (`_gitfix.py`,
`_agent_verify_fixtures.py`): one place for the value objects several test
modules need, so each module states only what it is actually asserting.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.adopter_sim.exitcodes import RunOutcome
from scripts.adopter_sim.model import Journey, JourneyStep
from scripts.adopter_sim.quorum import QuorumVerdict


def make_step(
    number: int,
    behavior: str | None,
    depends_on: tuple[int, ...] | list[int] = (),
    *,
    prompt: str | None = "do it",
    command: tuple[str, ...] | None = None,
) -> JourneyStep:
    return JourneyStep(
        number=number,
        title=f"step {number}",
        prompt=prompt,
        command=command,
        expected_behavior=behavior,
        depends_on=tuple(depends_on),
    )


def make_journey(steps, name: str = "t") -> Journey:
    return Journey(name=name, steps=tuple(steps))


def make_verdict(
    step: int,
    kind: str,
    status: str = "confirmed",
    *,
    detail: str = "d",
    seen: int = 2,
    evaluable: int = 3,
) -> QuorumVerdict:
    return QuorumVerdict(
        step=step,
        kind=kind,
        detail=detail,
        status=status,
        seen=seen,
        evaluable=evaluable,
    )


def make_outcome(**overrides) -> RunOutcome:
    """A RunOutcome with every flag clear unless overridden."""
    return RunOutcome(**overrides)


def write_findings_baseline(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"version": 1, "findings": entries}), encoding="utf-8")
    return path


def run_record(
    findings: list[tuple[int, str, str]] | list[tuple[str, str]],
    evaluable: list[int],
) -> dict[str, object]:
    """One element of the `runs` sequence `quorum.tally` consumes."""
    return {"findings": findings, "evaluable": evaluable}
