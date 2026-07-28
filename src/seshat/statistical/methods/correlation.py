"""Governed Pearson and Spearman association evidence."""

from __future__ import annotations

from ..contracts import (
    AnalysisWithheld,
    Blocker,
    Diagnostic,
    Estimate,
    Interval,
    MethodContext,
    MethodResult,
    TestStatistic,
)
from ..evidence import decimal_text
from .common import finite_array
from .inference import adjust_pvalues, bootstrap_interval


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _pairs(context: MethodContext):
    indexes = []
    for role in ("response", "predictor"):
        binding = context.spec.roles[role]
        try:
            indexes.append(context.data.columns.index(binding.column))
        except ValueError as exc:
            raise _withheld(
                "STAT_PROVIDER_INVALID_DATA",
                f"The acquired data omits the governed {role} column.",
                "Repair the provider projection and rerun the analysis.",
            ) from exc
    left: list[object] = []
    right: list[object] = []
    excluded = 0
    for row in context.data.rows:
        first, second = row[indexes[0]], row[indexes[1]]
        if _missing(first) or _missing(second):
            excluded += 1
            continue
        left.append(first)
        right.append(second)
    if excluded and context.spec.missing_policy == "fail":
        raise _withheld(
            "STAT_MISSING_DATA",
            "Association input contains incomplete pairs.",
            "Resolve missing values or approve pairwise/complete-case exclusion.",
        )
    first = finite_array(left, "response")
    second = finite_array(right, "predictor")
    minimum = context.spec.minimum_data.get("observations", 3)
    if len(first) < max(3, minimum):
        raise _withheld(
            "STAT_MINIMUM_DATA",
            "Too few complete pairs remain for association evidence.",
            "Provide more complete approved pairs.",
        )
    return first, second, excluded


def run_correlate(context: MethodContext) -> MethodResult:
    """Compute only the declared association coefficient."""

    import numpy as np
    from scipy import stats

    first, second, excluded = _pairs(context)
    if np.ptp(first) == 0 or np.ptp(second) == 0:
        raise _withheld(
            "STAT_CONSTANT_INPUT",
            "Association is undefined for a constant input.",
            "Provide variable observations for both governed roles.",
        )
    parameters = context.spec.method.parameters
    coefficient = str(parameters["coefficient"])
    level = str(parameters["confidence_level"])
    correction = str(parameters["correction"])
    function = stats.pearsonr if coefficient == "pearson" else stats.spearmanr
    result = function(first, second)
    observed = float(result.statistic)
    p_value = float(result.pvalue)
    adjusted = adjust_pvalues((p_value,), correction)[0]

    def statistic(left, right):
        return float(function(left, right).statistic)

    try:
        bootstrapped = bootstrap_interval(
            (first, second),
            statistic,
            level,
            context.spec.random_seed,
            paired=True,
        )
    except AnalysisWithheld as exc:
        if exc.blockers[0].code != "STAT_BOOTSTRAP_DEGENERATE":
            raise
        intervals = ()
        interval_diagnostic = (
            Diagnostic(
                "STAT_INTERVAL_WITHHELD",
                "warning",
                None,
                "The association estimate is valid, but the BCa interval "
                "was undefined for the observed resamples.",
            ),
        )
    else:
        intervals = (
            Interval(
                "correlation",
                bootstrapped.low,
                bootstrapped.high,
                bootstrapped.level,
                bootstrapped.method,
            ),
        )
        interval_diagnostic = ()
    diagnostics = interval_diagnostic
    if excluded:
        diagnostics += (
            Diagnostic(
                "STAT_MISSING_PAIRS_EXCLUDED",
                "warning",
                str(excluded),
                "Incomplete pairs were excluded under the declared "
                "missing-data policy.",
            ),
        )
    return MethodResult(
        estimates=(
            Estimate("correlation", decimal_text(observed), None),
            Estimate("paired_count", str(len(first)), None),
            Estimate("excluded_pair_count", str(excluded), None),
        ),
        intervals=intervals,
        tests=(
            TestStatistic(
                coefficient,
                decimal_text(observed),
                decimal_text(p_value),
                decimal_text(adjusted),
                "two-sided",
                coefficient,
            ),
        ),
        diagnostics=diagnostics,
        interpretation_cautions=(
            "Association does not establish causation, a driver, or an effect.",
        ),
    )
