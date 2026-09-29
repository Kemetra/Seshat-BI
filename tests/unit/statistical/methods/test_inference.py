"""Direct-oracle and degeneracy tests for inference primitives."""

from __future__ import annotations

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from seshat.statistical.contracts import AnalysisWithheld  # noqa: E402
from seshat.statistical.methods.inference import (  # noqa: E402
    BootstrapRequest,
    adjust_pvalues,
    bootstrap_interval,
    eta_squared_h,
    hedges_g,
    omega_squared,
    paired_standardized_change,
    rank_biserial,
)

pytestmark = pytest.mark.statistics


def test_bootstrap_interval_is_seeded_and_matches_scipy() -> None:
    sample = np.array([2.0, 4.0, 5.0, 8.0, 9.0])
    expected = stats.bootstrap(
        (sample,),
        np.mean,
        method="BCa",
        confidence_level=0.95,
        n_resamples=9_999,
        rng=np.random.default_rng(1729),
    ).confidence_interval

    request = BootstrapRequest("0.95", 1729)
    actual = bootstrap_interval((sample,), np.mean, request)
    repeated = bootstrap_interval((sample,), np.mean, request)

    assert float(actual.low) == pytest.approx(expected.low)
    assert float(actual.high) == pytest.approx(expected.high)
    assert actual == repeated
    assert actual.method == "BCa bootstrap"


def test_paired_bootstrap_preserves_alignment() -> None:
    first = np.array([1.0, 2.0, 4.0, 8.0])
    second = first + np.array([1.0, 1.0, 2.0, 2.0])

    def statistic(left, right):
        return np.mean(right - left)

    interval = bootstrap_interval(
        (first, second), statistic, BootstrapRequest("0.95", 1729, paired=True)
    )

    assert float(interval.low) <= 1.5 <= float(interval.high)


def test_holm_and_benjamini_hochberg_match_hand_calculation() -> None:
    values = (0.01, 0.04, 0.03)
    assert adjust_pvalues(values, "none") == values
    assert adjust_pvalues(values, "holm") == pytest.approx((0.03, 0.06, 0.06))
    assert adjust_pvalues(values, "benjamini-hochberg") == pytest.approx(
        (0.03, 0.04, 0.04)
    )


def test_effect_sizes_match_exact_small_sample_formulas() -> None:
    first = np.array([1.0, 2.0, 3.0])
    second = np.array([3.0, 4.0, 5.0])
    pooled = np.sqrt(
        (
            (len(first) - 1) * np.var(first, ddof=1)
            + (len(second) - 1) * np.var(second, ddof=1)
        )
        / (len(first) + len(second) - 2)
    )
    correction = 1 - 3 / (4 * (len(first) + len(second) - 2) - 1)
    assert hedges_g(first, second) == pytest.approx(
        correction * (np.mean(first) - np.mean(second)) / pooled
    )

    before = np.array([1.0, 2.0, 3.0, 4.0])
    after = np.array([2.0, 4.0, 4.0, 7.0])
    differences = after - before
    assert paired_standardized_change(before, after) == pytest.approx(
        np.mean(differences) / np.std(differences, ddof=1)
    )
    assert rank_biserial(first, second) == pytest.approx(-8 / 9)
    assert rank_biserial(before, after, paired=True) == pytest.approx(1.0)


def _ss_omega_squared(groups: list[list[float]]) -> float:
    """Independent reference: omega^2 = (SS_b - df_b * MS_w) / (SS_t + MS_w)."""
    arrays = [np.asarray(group) for group in groups]
    pooled = np.concatenate(arrays)
    grand = pooled.mean()
    ss_between = sum(len(a) * (a.mean() - grand) ** 2 for a in arrays)
    ss_within = sum(((a - a.mean()) ** 2).sum() for a in arrays)
    ms_within = ss_within / (len(pooled) - len(arrays))
    ss_total = ((pooled - grand) ** 2).sum()
    return (ss_between - (len(arrays) - 1) * ms_within) / (ss_total + ms_within)


def test_omega_squared_matches_the_sum_of_squares_reference() -> None:
    """#735: textbook omega^2 from the classical F, checked against SS terms.

    Hand-computed for these groups: SS_b=105.5, SS_w=28.5, SS_t=134, MS_w=19/6,
    so omega^2 = (105.5 - 2*19/6) / (134 + 19/6) = 0.72296 (the prior formula
    (F - df_b)/(F + df_w) gave 0.5713).
    """
    groups = [[1.0, 2.0, 3.0, 4.0], [3.0, 5.0, 7.0, 8.0], [8.0, 9.0, 10.0, 12.0]]
    classical_f = float(stats.f_oneway(*groups).statistic)
    observed = omega_squared(classical_f, group_count=3, total_count=12)
    assert observed == pytest.approx(_ss_omega_squared(groups))
    assert observed == pytest.approx(0.722965, abs=1e-6)


def test_eta_squared_h_is_the_named_kruskal_wallis_effect() -> None:
    """(H - k + 1)/(n - k) is eta^2_H (Cohen); epsilon^2 would be H/(n-1)=0.571."""
    assert eta_squared_h(8.0, group_count=3, total_count=15) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("call", "code"),
    (
        (
            lambda: bootstrap_interval(
                (np.array([1.0, 1.0, 1.0]),), np.mean, BootstrapRequest("0.95", 1)
            ),
            "STAT_BOOTSTRAP_DEGENERATE",
        ),
        (
            lambda: bootstrap_interval(
                (np.array([1.0, 2.0]),), np.mean, BootstrapRequest("0.95", 1)
            ),
            "STAT_BOOTSTRAP_TOO_SMALL",
        ),
        (
            lambda: bootstrap_interval(
                (np.array([1.0, 2.0, 3.0]),),
                np.mean,
                BootstrapRequest("0.95", 1, n_resamples=100_000),
            ),
            "STAT_RESAMPLE_LIMIT",
        ),
        (lambda: hedges_g(np.ones(3), np.ones(3)), "STAT_EFFECT_SIZE_UNDEFINED"),
        (
            lambda: paired_standardized_change(np.arange(3), np.arange(3) + 1),
            "STAT_EFFECT_SIZE_UNDEFINED",
        ),
    ),
)
def test_degenerate_inference_is_withheld(call, code: str) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        call()
    assert exc_info.value.blockers[0].code == code


@pytest.mark.parametrize(
    "values",
    ((), (-0.1,), (1.1,), (float("nan"),), (0.1, float("inf"))),
)
def test_pvalue_adjustment_refuses_empty_or_invalid_vectors(values) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        adjust_pvalues(values, "holm")
    assert exc_info.value.blockers[0].code == "STAT_INVALID_PVALUE"
