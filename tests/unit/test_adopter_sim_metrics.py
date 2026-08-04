from __future__ import annotations

import pytest

from scripts.adopter_sim.metrics import (
    TOLERANCE,
    compare,
    gate,
    median,
    normalise,
    out_of_band,
)

pytestmark = pytest.mark.unit


def test_ratios_are_machine_independent() -> None:
    fast = normalise({1: 200.0, 2: 400.0}, calibration_ms=100.0)
    slow = normalise({1: 600.0, 2: 1200.0}, calibration_ms=300.0)
    assert [t.ratio for t in fast] == [t.ratio for t in slow] == [2.0, 4.0]


def test_raw_ms_is_preserved_alongside_the_ratio() -> None:
    timings = normalise({1: 250.0}, calibration_ms=100.0)
    assert timings[0].raw_ms == 250.0
    assert timings[0].ratio == 2.5


def test_ratio_is_none_when_calibration_failed() -> None:
    timings = normalise({1: 250.0}, calibration_ms=None)
    assert timings[0].ratio is None
    assert timings[0].raw_ms == 250.0


def test_zero_calibration_is_treated_as_failed() -> None:
    timings = normalise({1: 250.0}, calibration_ms=0.0)
    assert timings[0].ratio is None


def test_timings_are_ordered_by_step() -> None:
    timings = normalise({7: 10.0, 1: 20.0, 3: 30.0}, calibration_ms=10.0)
    assert [t.step for t in timings] == [1, 3, 7]


def test_median_of_three() -> None:
    assert median([5.0, 1.0, 3.0]) == 3.0


def test_median_of_even_count() -> None:
    assert median([1.0, 3.0]) == 2.0


def test_median_of_empty_raises() -> None:
    with pytest.raises(ValueError):
        median([])


def test_compare_within_band() -> None:
    assert compare(1.1, 1.0, tolerance=TOLERANCE) == "within_band"


def test_compare_slower() -> None:
    assert compare(1.6, 1.0, tolerance=TOLERANCE) == "slower"


def test_compare_faster() -> None:
    assert compare(0.5, 1.0, tolerance=TOLERANCE) == "faster"


def test_compare_against_absent_baseline_is_within_band() -> None:
    assert compare(1.0, 0.0, tolerance=TOLERANCE) == "within_band"


def test_gate_reports_within_band_for_an_unchanged_ratio() -> None:
    rows = gate({"clean": {1: 2.05}}, {"clean": {1: 2.0}}, tolerance=TOLERANCE)
    assert [(r.dataset, r.step, r.verdict) for r in rows] == [
        ("clean", 1, "within_band")
    ]
    assert not out_of_band(rows)


def test_gate_flags_a_slower_step_out_of_band() -> None:
    rows = gate({"clean": {1: 3.0}}, {"clean": {1: 2.0}}, tolerance=TOLERANCE)
    assert rows[0].verdict == "slower"
    assert out_of_band(rows)


def test_gate_flags_a_faster_step_out_of_band() -> None:
    """The design gates 'slower / faster / within band' -- an unexplained
    speed-up means the step stopped doing its work, so it is not a free pass."""
    rows = gate({"clean": {1: 1.0}}, {"clean": {1: 2.0}}, tolerance=TOLERANCE)
    assert rows[0].verdict == "faster"
    assert out_of_band(rows)


def test_gate_skips_steps_the_reference_does_not_carry() -> None:
    """A newly added step has no accepted reference, so it cannot be judged."""
    rows = gate({"clean": {1: 2.0, 9: 99.0}}, {"clean": {1: 2.0}}, tolerance=TOLERANCE)
    assert [r.step for r in rows] == [1]


def test_gate_skips_datasets_the_reference_does_not_carry() -> None:
    rows = gate({"messy": {1: 9.0}}, {"clean": {1: 2.0}}, tolerance=TOLERANCE)
    assert rows == ()
    assert not out_of_band(rows)


def test_gate_without_a_reference_yields_no_rows() -> None:
    """First run: nothing accepted yet, so nothing may fail the run."""
    assert gate({"clean": {1: 2.0}}, {}, tolerance=TOLERANCE) == ()


def test_gate_keeps_datasets_independent() -> None:
    rows = gate(
        {"clean": {1: 2.0}, "messy": {1: 4.0}},
        {"clean": {1: 2.0}, "messy": {1: 2.0}},
        tolerance=TOLERANCE,
    )
    assert [(r.dataset, r.verdict) for r in rows] == [
        ("clean", "within_band"),
        ("messy", "slower"),
    ]
