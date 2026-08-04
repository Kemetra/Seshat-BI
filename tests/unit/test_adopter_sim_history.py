"""The two machine-local stores: the timings reference and invocation history.

Both are git-ignored per-journey state under `.seshat/adopter-sim/`. Neither may
fabricate a reading when its file is absent -- an absent store means "nothing
accepted yet", which must read as empty rather than as a passing comparison.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.adopter_sim.baseline import (
    load_timings_reference,
    timings_baseline_path,
    write_timings_reference,
)
from scripts.adopter_sim.history import (
    RECURRENCE_WINDOW,
    append_invocation,
    dataset_history,
    flaky_keys,
    invocation_history_path,
    load_invocation_history,
)
from scripts.adopter_sim.runner import _record_history
from tests.unit._adopter_sim_helpers import make_verdict


def _verdict(step: int, kind: str, status: str, *, dataset: str):
    """A verdict carrying a dataset, without growing the shared helper."""
    return replace(make_verdict(step, kind, status), dataset=dataset)


pytestmark = pytest.mark.unit


def test_absent_timings_reference_reads_as_empty(tmp_path: Path) -> None:
    assert load_timings_reference(tmp_path / "nothing.json") == {}


def test_timings_reference_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "first-hour.timings.json"
    write_timings_reference(
        path, {"clean": {1: 2.0, 3: 4.5}}, raws={"clean": {1: 200.0, 3: 450.0}}
    )
    assert load_timings_reference(path) == {"clean": {1: 2.0, 3: 4.5}}


def test_timings_reference_keeps_raw_ms_for_the_reader(tmp_path: Path) -> None:
    """Raw ms is machine-local context; it is recorded but never gated on."""
    path = tmp_path / "t.json"
    write_timings_reference(path, {"clean": {1: 2.0}}, raws={"clean": {1: 200.0}})
    assert "200" in path.read_text(encoding="utf-8")


def test_unreadable_timings_reference_reads_as_empty(tmp_path: Path) -> None:
    """A corrupt machine-local file must not abort the run -- it is not truth,
    and re-recording it costs one run."""
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_timings_reference(path) == {}


def test_timings_reference_lives_beside_the_history(tmp_path: Path) -> None:
    assert (
        invocation_history_path(tmp_path, "first-hour").parent
        == timings_baseline_path(tmp_path, "first-hour").parent
    )


def test_history_path_is_machine_local(tmp_path: Path) -> None:
    path = invocation_history_path(tmp_path, "first-hour")
    assert path == tmp_path / ".seshat" / "adopter-sim" / "first-hour.history.json"


def test_absent_history_reads_as_empty(tmp_path: Path) -> None:
    assert load_invocation_history(tmp_path / "nothing.json") == ()


def test_history_appends_oldest_first(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    append_invocation(path, {"clean": [(5, "outcome_mismatch")]})
    append_invocation(path, {"clean": [(6, "traceback")]})
    assert dataset_history(load_invocation_history(path), "clean") == (
        frozenset({(5, "outcome_mismatch")}),
        frozenset({(6, "traceback")}),
    )


def test_history_is_capped_to_the_recurrence_window(tmp_path: Path) -> None:
    """Only the window matters, so the file cannot grow without bound."""
    path = tmp_path / "h.json"
    for step in range(1, RECURRENCE_WINDOW + 4):
        append_invocation(path, {"clean": [(step, "outcome_mismatch")]})
    assert len(load_invocation_history(path)) == RECURRENCE_WINDOW


def test_history_keeps_datasets_apart(tmp_path: Path) -> None:
    """Cohort independence is load-bearing: a messy-only flake must never count
    toward a clean recurrence."""
    path = tmp_path / "h.json"
    append_invocation(path, {"clean": [(5, "a")], "messy": [(7, "b")]})
    history = load_invocation_history(path)
    assert dataset_history(history, "clean") == (frozenset({(5, "a")}),)
    assert dataset_history(history, "messy") == (frozenset({(7, "b")}),)


def test_dataset_absent_from_an_invocation_reads_as_no_flakes(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    append_invocation(path, {"clean": [(5, "a")]})
    assert dataset_history(load_invocation_history(path), "messy") == (frozenset(),)


def test_unreadable_history_reads_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_invocation_history(path) == ()


def test_flaky_keys_collects_flaky_verdicts_per_dataset() -> None:
    verdicts = [
        _verdict(5, "outcome_mismatch", "flaky", dataset="clean"),
        _verdict(7, "traceback", "flaky", dataset="messy"),
    ]
    assert flaky_keys(verdicts) == {
        "clean": [(5, "outcome_mismatch")],
        "messy": [(7, "traceback")],
    }


def test_flaky_keys_counts_recurring_flaky_as_still_flaking() -> None:
    """Once escalated the finding is STILL flaking. Dropping it here would break
    its own streak and make the verdict oscillate escalated/not on every run."""
    verdicts = [_verdict(5, "a", "recurring-flaky", dataset="clean")]
    assert flaky_keys(verdicts) == {"clean": [(5, "a")]}


def test_recording_persists_this_invocation(tmp_path: Path) -> None:
    verdicts = [_verdict(5, "a", "flaky", dataset="clean")]
    _record_history("j", verdicts, single_run=False, repo_root=tmp_path)
    history = load_invocation_history(invocation_history_path(tmp_path, "j"))
    assert dataset_history(history, "clean") == (frozenset({(5, "a")}),)


def test_a_single_run_invocation_records_no_history(tmp_path: Path) -> None:
    """`--runs 1` reproduces nothing, so it can neither start nor continue a
    streak -- and writing an empty entry would silently BREAK an existing one."""
    _record_history(
        "j",
        [_verdict(5, "a", "advisory", dataset="clean")],
        single_run=True,
        repo_root=tmp_path,
    )
    assert not invocation_history_path(tmp_path, "j").exists()


def test_flaky_keys_ignores_confirmed_and_advisory() -> None:
    verdicts = [
        _verdict(1, "a", "confirmed", dataset="clean"),
        _verdict(2, "b", "advisory", dataset="clean"),
        _verdict(3, "c", "insufficient_data", dataset="clean"),
    ]
    assert flaky_keys(verdicts) == {}
