"""Governed Pearson and Spearman association evidence."""

from __future__ import annotations

from ..contracts import (
    AnalysisWithheld,
    Diagnostic,
    Estimate,
    Interval,
    MethodContext,
    MethodResult,
    TestStatistic,
    require,
    withheld,
)
from ..evidence import decimal_text
from .common import finite_array
from .inference import BootstrapRequest, adjust_pvalues, bootstrap_interval


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _role_indexes(context: MethodContext) -> tuple[int, ...]:
    indexes: list[int] = []
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
    return tuple(indexes)


def _complete_pairs(context: MethodContext, roles: tuple[int, ...]):
    left_index, right_index = roles
    pairs = [
        (row[left_index], row[right_index])
        for row in context.data.rows
        if not _missing(row[left_index]) and not _missing(row[right_index])
    ]
    excluded = len(context.data.rows) - len(pairs)
    require(
        not excluded or context.spec.missing_policy != "fail",
        "STAT_MISSING_DATA",
        "Association input contains incomplete pairs.",
        "Resolve missing values or approve pairwise/complete-case exclusion.",
    )
    return pairs, excluded


def _pairs(context: MethodContext):
    pairs, excluded = _complete_pairs(context, _role_indexes(context))
    first = finite_array([pair[0] for pair in pairs], "response")
    second = finite_array([pair[1] for pair in pairs], "predictor")
    minimum = max(3, context.spec.minimum_data.get("observations", 3))
    require(
        len(first) >= minimum,
        "STAT_MINIMUM_DATA",
        "Too few complete pairs remain for association evidence.",
        "Provide more complete approved pairs.",
    )
    return first, second, excluded


def _association_interval(first, second, statistic, request: BootstrapRequest):
    """Report the BCa interval, or one warning when the resamples cannot define it."""

    try:
        bootstrapped = bootstrap_interval((first, second), statistic, request)
    except AnalysisWithheld as exc:
        if exc.blockers[0].code != "STAT_BOOTSTRAP_DEGENERATE":
            raise
        withheld_interval = Diagnostic(
            "STAT_INTERVAL_WITHHELD",
            "warning",
            None,
            "The association estimate is valid, but the BCa interval "
            "was undefined for the observed resamples.",
        )
        return (), (withheld_interval,)
    interval = Interval(
        "correlation",
        bootstrapped.low,
        bootstrapped.high,
        bootstrapped.level,
        bootstrapped.method,
    )
    return (interval,), ()


def run_correlate(context: MethodContext) -> MethodResult:
    """Compute only the declared association coefficient."""

    import numpy as np
    from scipy import stats

    first, second, excluded = _pairs(context)
    require(
        np.ptp(first) != 0 and np.ptp(second) != 0,
        "STAT_CONSTANT_INPUT",
        "Association is undefined for a constant input.",
        "Provide variable observations for both governed roles.",
    )
    parameters = context.spec.method.parameters
    coefficient = str(parameters["coefficient"])
    function = stats.pearsonr if coefficient == "pearson" else stats.spearmanr
    result = function(first, second)
    observed = float(result.statistic)
    p_value = float(result.pvalue)
    adjusted = adjust_pvalues((p_value,), str(parameters["correction"]))[0]

    def statistic(left, right):
        return float(function(left, right).statistic)

    request = BootstrapRequest(
        str(parameters["confidence_level"]), context.spec.random_seed, paired=True
    )
    intervals, diagnostics = _association_interval(first, second, statistic, request)
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
