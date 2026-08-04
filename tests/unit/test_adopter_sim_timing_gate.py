"""The timing gate: report-only until a reference is accepted, then enforcing.

Issue #567. The gate must never fail the run that first records a reference --
there is nothing accepted to compare against yet -- and must fail a later run
whose calibration-normalised ratio leaves the tolerance band.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.baseline import (
    load_timings_reference,
    timings_baseline_path,
    write_timings_reference,
)
from scripts.adopter_sim.runner import _report_timings

pytestmark = pytest.mark.unit


def _cohorts(ratio: float, raw: float = 200.0) -> dict[str, list[dict[str, object]]]:
    return {"clean": [{"raws": {1: raw}, "ratios": {1: ratio}}]}


def _seed(root: Path, ratio: float) -> Path:
    path = timings_baseline_path(root, "j")
    write_timings_reference(path, {"clean": {1: ratio}}, raws={"clean": {1: 200.0}})
    return path


def test_first_run_records_a_reference_and_does_not_fail(tmp_path: Path) -> None:
    assert _report_timings("j", _cohorts(2.0), repo_root=tmp_path) is False
    assert load_timings_reference(timings_baseline_path(tmp_path, "j")) == {
        "clean": {1: 2.0}
    }


def test_a_slower_run_fails_the_gate(tmp_path: Path) -> None:
    _seed(tmp_path, 2.0)
    assert _report_timings("j", _cohorts(6.0), repo_root=tmp_path) is True


def test_a_run_inside_the_band_passes_the_gate(tmp_path: Path) -> None:
    _seed(tmp_path, 2.0)
    assert _report_timings("j", _cohorts(2.1), repo_root=tmp_path) is False


def test_an_accepted_reference_is_not_overwritten_by_a_later_run(
    tmp_path: Path,
) -> None:
    """Otherwise each run compares against the previous one, and a slow drift of
    24% per run never trips the 25% band."""
    path = _seed(tmp_path, 2.0)
    _report_timings("j", _cohorts(2.1), repo_root=tmp_path)
    assert load_timings_reference(path) == {"clean": {1: 2.0}}


def test_accepting_refreshes_the_reference(tmp_path: Path) -> None:
    """`--update-baseline` is the one explicit way to move an accepted reference."""
    path = _seed(tmp_path, 2.0)
    _report_timings("j", _cohorts(6.0), repo_root=tmp_path, accept=True)
    assert load_timings_reference(path) == {"clean": {1: 6.0}}


def test_accepting_does_not_fail_the_run_it_accepts(tmp_path: Path) -> None:
    _seed(tmp_path, 2.0)
    assert _report_timings("j", _cohorts(6.0), repo_root=tmp_path, accept=True) is False


def test_a_step_absent_from_the_reference_cannot_fail_the_run(tmp_path: Path) -> None:
    _seed(tmp_path, 2.0)
    cohorts = {"clean": [{"raws": {9: 999.0}, "ratios": {9: 99.0}}]}
    assert _report_timings("j", cohorts, repo_root=tmp_path) is False


def test_a_run_with_no_timings_reports_nothing(tmp_path: Path) -> None:
    assert _report_timings("j", {}, repo_root=tmp_path) is False
    assert not timings_baseline_path(tmp_path, "j").exists()


def test_not_measured_ratios_do_not_fail_the_gate(tmp_path: Path) -> None:
    """A run whose calibration failed contributes no ratio, and an absent
    measurement must never read as a regression."""
    _seed(tmp_path, 2.0)
    cohorts = {"clean": [{"raws": {1: 200.0}, "ratios": {1: None}}]}
    assert _report_timings("j", cohorts, repo_root=tmp_path) is False
