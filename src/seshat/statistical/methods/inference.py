"""Deterministic uncertainty, multiplicity, and effect-size primitives."""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from ..contracts import AnalysisWithheld, require, withheld
from ..evidence import decimal_text

_MAX_RESAMPLES = 99_999

_MULTIPLICITY_METHODS = frozenset({"holm", "benjamini-hochberg"})


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    low: str
    high: str
    level: str
    method: str = "BCa bootstrap"


@dataclass(frozen=True, slots=True)
class BootstrapRequest:
    """The governed knobs of one bootstrap interval, declared together."""

    level: str
    seed: int
    paired: bool = False
    n_resamples: int = 9_999


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _degenerate(message: str) -> AnalysisWithheld:
    return _withheld(
        "STAT_BOOTSTRAP_DEGENERATE",
        message,
        "Choose a statistic defined for the governed sample.",
    )


def _undefined_effect(message: str) -> AnalysisWithheld:
    return _withheld(
        "STAT_EFFECT_SIZE_UNDEFINED",
        message,
        "Provide enough variable finite observations for the effect size.",
    )


def _usable_sample(array) -> bool:
    return array.ndim == 1 and len(array) >= 1


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
    require(
        arrays and all(_usable_sample(array) for array in arrays),
        "STAT_BOOTSTRAP_TOO_SMALL",
        "BCa bootstrap requires non-empty one-dimensional samples.",
        "Provide at least three eligible observations per resampled sample.",
    )
    require(
        all(bool(np.all(np.isfinite(array))) for array in arrays),
        "STAT_NON_FINITE_INPUT",
        "Bootstrap input contains a non-finite observation.",
        "Resolve NaN or infinite values under the approved missing-data policy.",
    )
    return arrays


def _valid_resample_count(count: object) -> bool:
    if isinstance(count, bool) or not isinstance(count, int):
        return False
    return 1 <= count <= _MAX_RESAMPLES


def _assert_bootstrappable(arrays, request: BootstrapRequest) -> None:
    """Hold the sample-size, pairing, and resource rules of a BCa interval."""

    require(
        all(len(array) >= 3 for array in arrays),
        "STAT_BOOTSTRAP_TOO_SMALL",
        "BCa bootstrap requires at least three observations per sample.",
        "Provide more eligible observations.",
    )
    require(
        not request.paired or len({len(array) for array in arrays}) == 1,
        "STAT_PAIRING_INVALID",
        "Paired bootstrap samples have different lengths.",
        "Provide one aligned observation for every approved pair.",
    )
    require(
        _valid_resample_count(request.n_resamples),
        "STAT_RESAMPLE_LIMIT",
        f"Bootstrap resamples must be between 1 and {_MAX_RESAMPLES}.",
        "Use a resample count within the governed resource ceiling.",
    )


def _confidence(level: str) -> float:
    recovery = "Use a governed confidence level strictly between zero and one."
    try:
        confidence = float(level)
    except (TypeError, ValueError) as exc:
        raise _withheld(
            "STAT_CONFIDENCE_LEVEL_INVALID",
            "The confidence level is not numeric.",
            recovery,
        ) from exc
    require(
        math.isfinite(confidence) and 0 < confidence < 1,
        "STAT_CONFIDENCE_LEVEL_INVALID",
        "The confidence level must be strictly between zero and one.",
        recovery,
    )
    return confidence


def _observed_statistic(statistic: Callable[..., object], arrays) -> float:
    try:
        observed = float(statistic(*arrays))
    except (TypeError, ValueError, OverflowError) as exc:
        raise _degenerate(
            "The requested bootstrap statistic is not a finite scalar."
        ) from exc
    if not math.isfinite(observed):
        raise _degenerate("The requested bootstrap statistic is not finite.")
    return observed


def _bca_interval(
    arrays,
    statistic: Callable[..., object],
    request: BootstrapRequest,
    confidence: float,
):
    import numpy as np
    from scipy import stats

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        warnings.simplefilter("ignore", stats.DegenerateDataWarning)
        return stats.bootstrap(
            arrays,
            statistic,
            method="BCa",
            confidence_level=confidence,
            n_resamples=request.n_resamples,
            paired=request.paired,
            rng=np.random.default_rng(request.seed),
        ).confidence_interval


def bootstrap_interval(
    samples: Sequence[object],
    statistic: Callable[..., object],
    request: BootstrapRequest,
) -> BootstrapInterval:
    """Return a deterministic finite BCa interval under a fixed resource ceiling."""

    arrays = _arrays(samples)
    _assert_bootstrappable(arrays, request)
    confidence = _confidence(request.level)
    _observed_statistic(statistic, arrays)
    result = _bca_interval(arrays, statistic, request, confidence)
    low = float(result.low)
    high = float(result.high)
    if not math.isfinite(low) or not math.isfinite(high):
        raise _withheld(
            "STAT_BOOTSTRAP_DEGENERATE",
            "The BCa bootstrap distribution is degenerate.",
            "Provide a variable sample with enough information for an interval.",
        )
    return BootstrapInterval(decimal_text(low), decimal_text(high), request.level)


def _is_probability(value: float) -> bool:
    return math.isfinite(value) and 0 <= value <= 1


def _pvalues(values: Iterable[float]) -> tuple[float, ...]:
    message = "P-values must be a non-empty finite vector within [0, 1]."
    recovery = "Repair the upstream test result before multiplicity correction."
    try:
        raw = tuple(float(value) for value in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld("STAT_INVALID_PVALUE", message, recovery) from exc
    require(
        raw and all(_is_probability(value) for value in raw),
        "STAT_INVALID_PVALUE",
        message,
        recovery,
    )
    return raw


def _holm(sorted_values: Sequence[float]) -> list[float]:
    """Step-down family-wise correction over ascending p-values."""

    count = len(sorted_values)
    adjusted: list[float] = []
    running = 0.0
    for rank, value in enumerate(sorted_values):
        running = max(running, (count - rank) * value)
        adjusted.append(min(1.0, running))
    return adjusted


def _benjamini_hochberg(sorted_values: Sequence[float]) -> list[float]:
    """Step-up false-discovery correction over ascending p-values."""

    count = len(sorted_values)
    adjusted = [0.0] * count
    running = 1.0
    for rank in range(count - 1, -1, -1):
        candidate = sorted_values[rank] * count / (rank + 1)
        running = min(running, candidate)
        adjusted[rank] = min(1.0, max(0.0, running))
    return adjusted


def adjust_pvalues(values: Iterable[float], method: str) -> tuple[float, ...]:
    """Apply a stable Holm or Benjamini-Hochberg correction."""

    raw = _pvalues(values)
    if method == "none":
        return raw
    require(
        method in _MULTIPLICITY_METHODS,
        "STAT_MULTIPLICITY_METHOD",
        "The multiplicity correction is outside the governed catalog.",
        "Use none, holm, or benjamini-hochberg.",
    )
    order = sorted(range(len(raw)), key=lambda index: (raw[index], index))
    correct = _holm if method == "holm" else _benjamini_hochberg
    adjusted_sorted = correct([raw[index] for index in order])
    restored = [0.0] * len(raw)
    for sorted_index, original_index in enumerate(order):
        restored[original_index] = adjusted_sorted[sorted_index]
    return tuple(restored)


def _finite_vector(values: object, name: str):
    import numpy as np

    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _undefined_effect(f"{name} requires numeric observations.") from exc
    usable = array.ndim == 1 and len(array) >= 2
    require(
        usable and bool(np.all(np.isfinite(array))),
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
    require(
        math.isfinite(float(pooled_variance)) and pooled_variance > 0,
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
    require(
        len(left) == len(right),
        "STAT_PAIRING_INVALID",
        "Paired effect-size samples have different lengths.",
        "Provide one aligned observation for every approved pair.",
    )
    differences = right - left
    deviation = float(np.std(differences, ddof=1))
    require(
        math.isfinite(deviation) and deviation != 0,
        "STAT_EFFECT_SIZE_UNDEFINED",
        (
            "Paired standardized change is undefined because "
            "difference variance is zero."
        ),
        "Use an effect size defined for the observed paired differences.",
    )
    return float(np.mean(differences) / deviation)


def _paired_rank_biserial(left, right) -> float:
    import numpy as np
    from scipy import stats

    require(
        len(left) == len(right),
        "STAT_PAIRING_INVALID",
        "Paired rank samples have different lengths.",
        "Provide one aligned observation for every approved pair.",
    )
    differences = right - left
    nonzero = differences[differences != 0]
    require(
        len(nonzero) > 0,
        "STAT_EFFECT_SIZE_UNDEFINED",
        "Paired rank-biserial correlation has no non-zero differences.",
        "Use an effect size defined for the observed paired differences.",
    )
    ranks = stats.rankdata(np.abs(nonzero))
    positive = float(np.sum(ranks[nonzero > 0]))
    negative = float(np.sum(ranks[nonzero < 0]))
    return (positive - negative) / (positive + negative)


def rank_biserial(first: object, second: object, *, paired: bool = False) -> float:
    """Rank-biserial correlation for independent or aligned paired samples."""

    from scipy import stats

    left = _finite_vector(first, "Rank-biserial correlation")
    right = _finite_vector(second, "Rank-biserial correlation")
    if paired:
        return _paired_rank_biserial(left, right)
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
    defined = math.isfinite(statistic) and min(between, within) >= 1
    require(
        defined and denominator > 0,
        "STAT_EFFECT_SIZE_UNDEFINED",
        "Omega squared is undefined for the supplied group degrees of freedom.",
        "Provide at least two groups with residual degrees of freedom.",
    )
    return min(1.0, max(0.0, (statistic - between) / denominator))


def epsilon_squared(h_statistic: float, *, group_count: int, total_count: int) -> float:
    """Epsilon-squared estimate from a Kruskal-Wallis H statistic."""

    denominator = total_count - group_count
    statistic = float(h_statistic)
    defined = math.isfinite(statistic) and group_count >= 2
    require(
        defined and denominator > 0,
        "STAT_EFFECT_SIZE_UNDEFINED",
        "Epsilon squared is undefined for the supplied group sizes.",
        "Provide at least two groups with residual observations.",
    )
    value = (statistic - group_count + 1) / denominator
    return min(1.0, max(0.0, value))
