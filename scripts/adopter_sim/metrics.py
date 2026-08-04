"""Timing normalisation.

Raw wall-clock is machine-dependent and therefore useless in a shared record, so
every CLI timing is expressed as a ratio to a calibration step measured in the
same run.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# A metric this far from baseline fails the run; anything closer is noise.
TOLERANCE = 0.25


@dataclass(frozen=True)
class Timing:
    step: int
    raw_ms: float
    ratio: float | None


@dataclass(frozen=True)
class MetricReport:
    cli_ratios: tuple[Timing, ...]
    turns: int | None
    tool_calls: int | None
    tokens: int | None
    total_ms: float
    calibration_ms: float | None


def normalise(
    raw_ms: Mapping[int, float], calibration_ms: float | None
) -> tuple[Timing, ...]:
    """Express each raw timing as a ratio to calibration, keeping the raw value.

    A missing or zero calibration yields ratio=None -- the metric is reported
    `not_measured` rather than fabricated.
    """
    usable = bool(calibration_ms)
    return tuple(
        Timing(
            step=step,
            raw_ms=value,
            ratio=(value / calibration_ms) if usable else None,  # type: ignore[operator]
        )
        for step, value in sorted(raw_ms.items())
    )


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median of an empty sequence")
    return float(statistics.median(values))


def compare(current: float, baseline: float, *, tolerance: float) -> str:
    """'slower' | 'faster' | 'within_band', relative to the tolerance band."""
    if baseline <= 0:
        return "within_band"
    delta = (current - baseline) / baseline
    if delta > tolerance:
        return "slower"
    if delta < -tolerance:
        return "faster"
    return "within_band"


@dataclass(frozen=True)
class GateRow:
    dataset: str
    step: int
    current: float
    reference: float
    verdict: str


def gate(
    current: Mapping[str, Mapping[int, float]],
    reference: Mapping[str, Mapping[int, float]],
    *,
    tolerance: float,
) -> tuple[GateRow, ...]:
    """Judge this run's median ratios against the accepted reference.

    Only (dataset, step) pairs the reference already carries are judged. A newly
    added step or dataset has nothing accepted to measure against, and inventing
    a verdict for it would fail the very run that introduced it.
    """
    rows: list[GateRow] = []
    for dataset in sorted(current):
        accepted = reference.get(dataset) or {}
        for step, ratio in sorted(current[dataset].items()):
            if step not in accepted:
                continue
            rows.append(
                GateRow(
                    dataset=dataset,
                    step=step,
                    current=ratio,
                    reference=accepted[step],
                    verdict=compare(ratio, accepted[step], tolerance=tolerance),
                )
            )
    return tuple(rows)


def out_of_band(rows: Sequence[GateRow]) -> bool:
    """True when any gated metric left the band, in EITHER direction.

    An unexplained speed-up is also a regression signal: the usual cause is a
    step that stopped doing its work, not a genuine optimisation.
    """
    return any(row.verdict != "within_band" for row in rows)
