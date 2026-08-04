"""Aggregate repeated runs into verdicts.

A single run of a nondeterministic agent cannot establish a finding. Three runs
with a 2-of-3 quorum can. Flaky does not mean ignore -- it is reported with its
observed frequency.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace

from scripts.adopter_sim.model import Journey

STATUSES = (
    "confirmed",
    "flaky",
    "recurring-flaky",
    "insufficient_data",
    "advisory",
)
_QUORUM = 2
_MIN_EVALUABLE = 2
# Three CONSECUTIVE flaky invocations escalate; this one plus _RECURRENCE - 1 prior.
_RECURRENCE = 3


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

    This folds ONE invocation. Escalating a finding that keeps flaking across
    invocations is `escalate`, which needs history this function does not see.
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


def escalate(
    verdicts: Sequence[QuorumVerdict],
    previous_flaky: Sequence[Collection[tuple[int, str]]],
) -> tuple[QuorumVerdict, ...]:
    """Escalate flaky verdicts that complete a consecutive flaky streak.

    Separate from `tally` because it works on a different time scale: `tally`
    folds the runs of ONE invocation, this compares against the invocations
    before it. `previous_flaky` carries THIS cohort's flaky keys, oldest first --
    callers pass one dataset's history for the same reason they pass one
    dataset's runs.

    Only `flaky` escalates. A `confirmed` finding is already actionable and must
    not be relabelled, and an `advisory` single-run verdict was never reproduced.
    """
    needed = _RECURRENCE - 1
    recent = tuple(previous_flaky)[-needed:]
    if len(recent) < needed:
        return tuple(verdicts)
    return tuple(
        replace(verdict, status="recurring-flaky")
        if verdict.status == "flaky"
        and all((verdict.step, verdict.kind) in entry for entry in recent)
        else verdict
        for verdict in verdicts
    )


def _status(seen: int, evaluable: int, *, single_run: bool) -> str:
    if single_run:
        return "advisory"
    if evaluable < _MIN_EVALUABLE:
        return "insufficient_data"
    if seen >= _QUORUM:
        return "confirmed"
    return "flaky"
