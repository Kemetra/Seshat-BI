"""Per-journey invocation history, machine-local.

A flaky finding that persists across three consecutive invocations escalates to
`recurring-flaky`, and that verdict cannot be reached from a single invocation --
it needs memory of the previous ones.

That memory is machine-local for the same reason timings are: it describes what
this machine's runs happened to do, not portable truth. Committing it would make
another laptop's history read as this one's. It therefore lives beside the
timings reference under `.seshat/adopter-sim/` rather than being tracked.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

# Three CONSECUTIVE flaky invocations escalate (adopter-sim design, repeat policy).
RECURRENCE_WINDOW = 3

# One invocation: the flaky (step, kind) keys it produced, per dataset cohort.
Invocation = dict[str, frozenset[tuple[int, str]]]


def invocation_history_path(repo_root: Path, journey: str) -> Path:
    return repo_root / ".seshat" / "adopter-sim" / f"{journey}.history.json"


def load_invocation_history(path: Path) -> tuple[Invocation, ...]:
    """Oldest invocation first. An absent or unreadable file reads as no history.

    History is machine-local convenience state, not evidence, so a corrupt file
    costs at most a delayed escalation -- never an aborted run.
    """
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    entries = payload.get("invocations") or ()
    return tuple(_invocation(entry) for entry in entries)


def _invocation(entry: object) -> Invocation:
    if not isinstance(entry, Mapping):
        return {}
    return {
        str(dataset): frozenset(
            (int(key[0]), str(key[1]))
            for key in keys or ()
            if isinstance(key, (list, tuple)) and len(key) == 2
        )
        for dataset, keys in entry.items()
    }


def append_invocation(
    path: Path,
    flaky: Mapping[str, Iterable[tuple[int, str]]],
    *,
    window: int = RECURRENCE_WINDOW,
) -> None:
    """Append this invocation's flaky keys, keeping only the last `window`.

    Capping at the window is what keeps the file small: nothing older can affect
    a verdict, so nothing older is worth storing.
    """
    history = [_serialise(entry) for entry in load_invocation_history(path)]
    history.append(_serialise(flaky))
    payload = {"version": 1, "invocations": history[-window:]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return None


def _serialise(
    flaky: Mapping[str, Iterable[tuple[int, str]]],
) -> dict[str, list[list[object]]]:
    return {
        dataset: sorted([step, kind] for step, kind in keys)
        for dataset, keys in sorted(flaky.items())
    }


# A recurring-flaky finding is STILL flaking, so it keeps its own streak alive.
# Dropping it here would break the streak that produced it and make the verdict
# oscillate escalated / not-escalated on every other run.
_FLAKY_STATUSES = ("flaky", "recurring-flaky")


def flaky_keys(verdicts: Iterable[object]) -> dict[str, list[tuple[int, str]]]:
    """This invocation's flaky (step, kind) keys, per dataset cohort.

    Confirmed findings are already actionable and advisory / insufficient_data
    ones were never reproduced, so none of them belong in a recurrence streak.
    """
    keys: dict[str, list[tuple[int, str]]] = {}
    for verdict in verdicts:
        status = getattr(verdict, "status", "")
        if status not in _FLAKY_STATUSES:
            continue
        dataset = getattr(verdict, "dataset", "")
        entry = (int(getattr(verdict, "step")), str(getattr(verdict, "kind")))
        keys.setdefault(dataset, []).append(entry)
    return {dataset: sorted(entries) for dataset, entries in sorted(keys.items())}


def dataset_history(
    history: Sequence[Invocation], dataset: str
) -> tuple[frozenset[tuple[int, str]], ...]:
    """One entry per invocation, oldest first, for ONE dataset cohort.

    A dataset absent from an invocation contributes an EMPTY set rather than
    being skipped, so a run in which that cohort produced no flake breaks the
    streak. Cohorts are judged independently, exactly as in `quorum.tally`.
    """
    return tuple(entry.get(dataset, frozenset()) for entry in history)
