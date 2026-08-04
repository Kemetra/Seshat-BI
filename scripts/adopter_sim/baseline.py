"""Two baselines, split by portability.

Findings are tracked -- portable and worth a git diff. Timings are
machine-local: committing them would turn a different laptop, or CI, into a
permanent false regression. This follows the .seshat/watch/ precedent (spec 131).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError
from scripts.adopter_sim.quorum import QuorumVerdict

# Only a confirmed verdict is baseline-worthy. Flaky, insufficient_data, and
# advisory verdicts are reported but never recorded as accepted state.
_BASELINE_STATUS = "confirmed"


@dataclass(frozen=True)
class DiffRow:
    step: int
    kind: str
    state: str
    dataset: str = ""


def findings_baseline_path(repo_root: Path, journey: str) -> Path:
    return (
        repo_root / "benchmark" / "journeys" / "baseline" / f"{journey}.findings.json"
    )


def timings_baseline_path(repo_root: Path, journey: str) -> Path:
    return repo_root / ".seshat" / "adopter-sim" / f"{journey}.timings.json"


def load_timings_reference(path: Path) -> dict[str, dict[int, float]]:
    """The accepted per-dataset median ratios, or {} when nothing is accepted.

    Unlike the findings baseline this file is machine-local and therefore not
    truth: an absent OR unreadable one reads as empty, so a corrupt cache
    re-records itself on the next run instead of aborting it.
    """
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        str(dataset): {int(step): float(value) for step, value in (steps or {}).items()}
        for dataset, steps in (payload.get("ratios") or {}).items()
    }


def write_timings_reference(
    path: Path,
    ratios: Mapping[str, Mapping[int, float]],
    *,
    raws: Mapping[str, Mapping[int, float]],
) -> None:
    """Record the accepted reference.

    Raw milliseconds are kept as context for a human reading the file; only the
    calibration-normalised ratios are ever compared against.
    """
    payload = {
        "version": 1,
        "ratios": _by_step(ratios),
        "raw_ms": _by_step(raws),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return None


def _by_step(
    values: Mapping[str, Mapping[int, float]],
) -> dict[str, dict[str, float]]:
    """JSON object keys are strings; keep them sorted so diffs stay readable."""
    return {
        dataset: {str(step): value for step, value in sorted(steps.items())}
        for dataset, steps in sorted(values.items())
    }


def load_findings_baseline(path: Path) -> tuple[dict[str, str], ...]:
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdopterSimError(f"cannot read baseline {path}: {exc}") from exc
    entries = payload.get("findings") or []
    return tuple(
        {
            "step": int(entry["step"]),
            "kind": str(entry["kind"]),
            # Entries predating per-dataset cohorts carry no dataset.
            "dataset": str(entry.get("dataset") or ""),
        }
        for entry in entries
    )


def diff_findings(
    verdicts: Sequence[QuorumVerdict], baseline: Sequence[dict[str, str]]
) -> tuple[DiffRow, ...]:
    """New / resolved / unchanged, keyed per DATASET as well as step and kind."""
    current = {
        (v.dataset, v.step, v.kind) for v in verdicts if v.status == _BASELINE_STATUS
    }
    known = {
        (str(e.get("dataset") or ""), int(e["step"]), str(e["kind"])) for e in baseline
    }
    states = (
        ("new", current - known),
        ("resolved", known - current),
        ("unchanged", current & known),
    )
    return tuple(
        DiffRow(step, kind, state, dataset)
        for state, keys in states
        for dataset, step, kind in sorted(keys)
    )


def _assert_acceptable(
    *, partial: bool, single_run: bool, aborted: bool, invoked_by: str
) -> None:
    """Refusal conditions, so a hand-wave cannot become accepted state."""
    refusals = (
        (partial, "the run was partial"),
        (single_run, "--runs 1 findings are not reproduced"),
        (aborted, "the run aborted on an assertion or fixture self-test"),
        (not invoked_by.strip(), "no invoking human named"),
    )
    for triggered, reason in refusals:
        if triggered:
            raise AdopterSimError(f"refusing baseline update: {reason}")
    return None


def update_findings_baseline(
    path: Path,
    verdicts: Sequence[QuorumVerdict],
    *,
    run_id: str,
    kit_version: str,
    invoked_by: str,
    partial: bool,
    single_run: bool,
    aborted: bool,
) -> None:
    """Write the accepted findings plus provenance, or refuse.

    Refusal conditions exist so a hand-wave cannot become accepted state.
    """
    _assert_acceptable(
        partial=partial,
        single_run=single_run,
        aborted=aborted,
        invoked_by=invoked_by,
    )
    payload = {
        "version": 1,
        "provenance": {
            "run_id": run_id,
            "kit_version": kit_version,
            "invoked_by": invoked_by,
        },
        "findings": [
            {
                "dataset": v.dataset,
                "step": v.step,
                "kind": v.kind,
                "detail": v.detail,
            }
            for v in sorted(verdicts, key=lambda v: (v.dataset, v.step, v.kind))
            if v.status == _BASELINE_STATUS
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return None
