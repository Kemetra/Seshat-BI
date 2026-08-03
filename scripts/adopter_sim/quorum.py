"""Aggregate repeated runs into verdicts.

A single run of a nondeterministic agent cannot establish a finding. Three runs
with a 2-of-3 quorum can. Flaky does not mean ignore -- it is reported with its
observed frequency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scripts.adopter_sim.model import Journey

STATUSES = ("confirmed", "flaky", "insufficient_data", "advisory")
_QUORUM = 2
_MIN_EVALUABLE = 2


@dataclass(frozen=True)
class QuorumVerdict:
    step: int
    kind: str
    detail: str
    status: str
    seen: int
    evaluable: int
    dataset: str = ""


def tally(
    journey: Journey,
    runs: Sequence[Mapping[str, object]],
    *,
    single_run: bool,
    dataset: str = "",
) -> tuple[QuorumVerdict, ...]:
    """Fold one dataset cohort's runs into a verdict per (step, kind).

    Callers MUST pass a single dataset's runs. Pooling clean and messy would let
    a 1-of-3 flake on each dataset add up to a false `confirmed`, and would hide
    which dataset exposed the regression -- destroying the control the two
    datasets exist to provide.

    Each run is a mapping with:
      findings: sequence of (step, kind, detail) triples, or (kind, detail)
                pairs for a single-step journey
      evaluable: the step numbers that produced a usable observation
    """
    counts: dict[tuple[int, str], list[str]] = {}
    evaluable_runs: dict[int, int] = {step.number: 0 for step in journey.steps}

    for run in runs:
        for number in run.get("evaluable") or ():
            if number in evaluable_runs:
                evaluable_runs[number] += 1
        for entry in run.get("findings") or ():
            step, kind, detail = _unpack(entry, journey)
            counts.setdefault((step, kind), []).append(detail)

    verdicts: list[QuorumVerdict] = []
    for (step, kind), details in sorted(counts.items()):
        seen = len(details)
        evaluable = evaluable_runs.get(step, 0)
        verdicts.append(
            QuorumVerdict(
                step=step,
                kind=kind,
                detail=details[0],
                status=_status(seen, evaluable, single_run=single_run),
                seen=seen,
                evaluable=evaluable,
                dataset=dataset,
            )
        )
    return tuple(verdicts)


def _unpack(entry: object, journey: Journey) -> tuple[int, str, str]:
    if isinstance(entry, (tuple, list)) and len(entry) == 3:
        return int(entry[0]), str(entry[1]), str(entry[2])
    if isinstance(entry, (tuple, list)) and len(entry) == 2:
        # Single-step journeys omit the step number.
        return journey.steps[0].number, str(entry[0]), str(entry[1])
    raise ValueError(f"unrecognised finding entry: {entry!r}")


def _status(seen: int, evaluable: int, *, single_run: bool) -> str:
    if single_run:
        return "advisory"
    if evaluable < _MIN_EVALUABLE:
        return "insufficient_data"
    if seen >= _QUORUM:
        return "confirmed"
    return "flaky"
