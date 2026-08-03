from __future__ import annotations

import pytest

from scripts.adopter_sim.metrics import TOLERANCE, compare, median, normalise

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
