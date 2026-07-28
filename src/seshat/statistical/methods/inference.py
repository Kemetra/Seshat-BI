"""Deterministic uncertainty, multiplicity, and effect-size primitives."""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from ..contracts import AnalysisWithheld, Blocker
from ..evidence import decimal_text

_MAX_RESAMPLES = 99_999


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    low: str
    high: str
    level: str
    method: str = "BCa bootstrap"


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _arrays(samples: Sequence[object]):
    import numpy as np

    try:
        arrays = tuple(np.asarray(sample, dtype=np.float64) for sample in samples)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_NON_NUMERIC_INPUT",
            "Bootstrap input contains a non-numeric observation.",
            "Provide values matching the approved numeric roles.",
        ) from exc
    if not arrays or any(array.ndim != 1 or len(array) < 1 for array in arrays):
        raise _withheld(
            "STAT_BOOTSTRAP_TOO_SMALL",
            "BCa bootstrap requires non-empty one-dimensional samples.",
            "Provide at least three eligible observations per resampled sample.",
        )
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise _withheld(
            "STAT_NON_FINITE_INPUT",
            "Bootstrap input contains a non-finite observation.",
            "Resolve NaN or infinite values under the approved missing-data policy.",
        )
    return arrays


def bootstrap_interval(
    samples: Sequence[object],
    statistic: Callable[..., object],
    level: str,
    seed: int,
    paired: bool = False,
    *,
    n_resamples: int = 9_999,
) -> BootstrapInterval:
    """Return a deterministic finite BCa interval under a fixed resource ceiling."""

    import numpy as np
    from scipy import stats

    arrays = _arrays(samples)
    if any(len(array) < 3 for array in arrays):
        raise _withheld(
            "STAT_BOOTSTRAP_TOO_SMALL",
            "BCa bootstrap requires at least three observations per sample.",
            "Provide more eligible observations.",
        )
    if paired and len({len(array) for array in arrays}) != 1:
        raise _withheld(
            "STAT_PAIRING_INVALID",
            "Paired bootstrap samples have different lengths.",
            "Provide one aligned observation for every approved pair.",
        )
    if (
        not isinstance(n_resamples, int)
        or isinstance(n_resamples, bool)
        or not 1 <= n_resamples <= _MAX_RESAMPLES
    ):
        raise _withheld(
            "STAT_RESAMPLE_LIMIT",
            f"Bootstrap resamples must be between 1 and {_MAX_RESAMPLES}.",
            "Use a resample count within the governed resource ceiling.",
        )
    try:
        confidence = float(level)
    except (TypeError, ValueError) as exc:
        raise _withheld(
            "STAT_CONFIDENCE_LEVEL_INVALID",
            "The confidence level is not numeric.",
            "Use a governed confidence level strictly between zero and one.",
        ) from exc
    if not math.isfinite(confidence) or not 0 < confidence < 1:
        raise _withheld(
            "STAT_CONFIDENCE_LEVEL_INVALID",
            "The confidence level must be strictly between zero and one.",
            "Use a governed confidence level strictly between zero and one.",
        )
    try:
        observed = float(statistic(*arrays))
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_BOOTSTRAP_DEGENERATE",
            "The requested bootstrap statistic is not a finite scalar.",
            "Choose a statistic defined for the governed sample.",
        ) from exc
    if not math.isfinite(observed):
        raise _withheld(
            "STAT_BOOTSTRAP_DEGENERATE",
            "The requested bootstrap statistic is not finite.",
            "Choose a statistic defined for the governed sample.",
        )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        warnings.simplefilter("ignore", stats.DegenerateDataWarning)
        result = stats.bootstrap(
            arrays,
            statistic,
            method="BCa",
            confidence_level=confidence,
            n_resamples=n_resamples,
            paired=paired,
            rng=np.random.default_rng(seed),
        ).confidence_interval
    low = float(result.low)
    high = float(result.high)
    if not math.isfinite(low) or not math.isfinite(high):
        raise _withheld(
            "STAT_BOOTSTRAP_DEGENERATE",
            "The BCa bootstrap distribution is degenerate.",
            "Provide a variable sample with enough information for an interval.",
        )
    return BootstrapInterval(decimal_text(low), decimal_text(high), level)


def adjust_pvalues(values: Iterable[float], method: str) -> tuple[float, ...]:
    """Apply a stable Holm or Benjamini-Hochberg correction."""

    try:
        raw = tuple(float(value) for value in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_INVALID_PVALUE",
            "P-values must be a non-empty finite vector within [0, 1].",
            "Repair the upstream test result before multiplicity correction.",
        ) from exc
    if not raw or any(not math.isfinite(value) or not 0 <= value <= 1 for value in raw):
        raise _withheld(
            "STAT_INVALID_PVALUE",
            "P-values must be a non-empty finite vector within [0, 1].",
            "Repair the upstream test result before multiplicity correction.",
        )
    if method == "none":
        return raw
    if method not in {"holm", "benjamini-hochberg"}:
        raise _withheld(
            "STAT_MULTIPLICITY_METHOD",
            "The multiplicity correction is outside the governed catalog.",
            "Use none, holm, or benjamini-hochberg.",
        )

    count = len(raw)
    order = sorted(range(count), key=lambda index: (raw[index], index))
    sorted_values = [raw[index] for index in order]
    adjusted_sorted: list[float]
    if method == "holm":
        adjusted_sorted = []
        running = 0.0
        for rank, value in enumerate(sorted_values):
            running = max(running, (count - rank) * value)
            adjusted_sorted.append(min(1.0, running))
    else:
        adjusted_sorted = [0.0] * count
        running = 1.0
        for rank in range(count - 1, -1, -1):
            candidate = sorted_values[rank] * count / (rank + 1)
            running = min(running, candidate)
            adjusted_sorted[rank] = min(1.0, max(0.0, running))
    restored = [0.0] * count
    for sorted_index, original_index in enumerate(order):
        restored[original_index] = adjusted_sorted[sorted_index]
    return tuple(restored)


def _finite_vector(values: object, name: str):
    import numpy as np

    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            f"{name} requires numeric observations.",
            "Provide enough variable finite observations for the effect size.",
        ) from exc
    if array.ndim != 1 or len(array) < 2 or not np.all(np.isfinite(array)):
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            f"{name} requires at least two finite observations.",
            "Provide enough variable finite observations for the effect size.",
        )
    return array


def hedges_g(first: object, second: object) -> float:
    """Bias-corrected standardized independent-group mean difference."""

    import numpy as np

    left = _finite_vector(first, "Hedges g")
    right = _finite_vector(second, "Hedges g")
    degrees = len(left) + len(right) - 2
    pooled_variance = (
        (len(left) - 1) * np.var(left, ddof=1)
        + (len(right) - 1) * np.var(right, ddof=1)
    ) / degrees
    if not math.isfinite(float(pooled_variance)) or pooled_variance <= 0:
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            "Hedges g is undefined because pooled variance is zero.",
            "Use an effect size defined for the observed group variability.",
        )
    correction = 1 - 3 / (4 * degrees - 1)
    return float(
        correction * (np.mean(left) - np.mean(right)) / np.sqrt(pooled_variance)
    )


def paired_standardized_change(before: object, after: object) -> float:
    """Standardized mean paired difference using the difference-score deviation."""

    import numpy as np

    left = _finite_vector(before, "Paired standardized change")
    right = _finite_vector(after, "Paired standardized change")
    if len(left) != len(right):
        raise _withheld(
            "STAT_PAIRING_INVALID",
            "Paired effect-size samples have different lengths.",
            "Provide one aligned observation for every approved pair.",
        )
    differences = right - left
    deviation = float(np.std(differences, ddof=1))
    if not math.isfinite(deviation) or deviation == 0:
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            (
                "Paired standardized change is undefined because "
                "difference variance is zero."
            ),
            "Use an effect size defined for the observed paired differences.",
        )
    return float(np.mean(differences) / deviation)


def rank_biserial(first: object, second: object, *, paired: bool = False) -> float:
    """Rank-biserial correlation for independent or aligned paired samples."""

    import numpy as np
    from scipy import stats

    left = _finite_vector(first, "Rank-biserial correlation")
    right = _finite_vector(second, "Rank-biserial correlation")
    if paired:
        if len(left) != len(right):
            raise _withheld(
                "STAT_PAIRING_INVALID",
                "Paired rank samples have different lengths.",
                "Provide one aligned observation for every approved pair.",
            )
        differences = right - left
        nonzero = differences[differences != 0]
        if len(nonzero) == 0:
            raise _withheld(
                "STAT_EFFECT_SIZE_UNDEFINED",
                "Paired rank-biserial correlation has no non-zero differences.",
                "Use an effect size defined for the observed paired differences.",
            )
        ranks = stats.rankdata(np.abs(nonzero))
        positive = float(np.sum(ranks[nonzero > 0]))
        negative = float(np.sum(ranks[nonzero < 0]))
        return (positive - negative) / (positive + negative)
    statistic = float(
        stats.mannwhitneyu(left, right, alternative="two-sided").statistic
    )
    return 2 * statistic / (len(left) * len(right)) - 1


def omega_squared(f_statistic: float, *, group_count: int, total_count: int) -> float:
    """Omega-squared estimate from a one-way F statistic."""

    between = group_count - 1
    within = total_count - group_count
    statistic = float(f_statistic)
    denominator = statistic + within
    if not math.isfinite(statistic) or between < 1 or within < 1 or denominator <= 0:
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            "Omega squared is undefined for the supplied group degrees of freedom.",
            "Provide at least two groups with residual degrees of freedom.",
        )
    return min(1.0, max(0.0, (statistic - between) / denominator))


def epsilon_squared(h_statistic: float, *, group_count: int, total_count: int) -> float:
    """Epsilon-squared estimate from a Kruskal-Wallis H statistic."""

    denominator = total_count - group_count
    statistic = float(h_statistic)
    if not math.isfinite(statistic) or group_count < 2 or denominator <= 0:
        raise _withheld(
            "STAT_EFFECT_SIZE_UNDEFINED",
            "Epsilon squared is undefined for the supplied group sizes.",
            "Provide at least two groups with residual observations.",
        )
    value = (statistic - group_count + 1) / denominator
    return min(1.0, max(0.0, value))
