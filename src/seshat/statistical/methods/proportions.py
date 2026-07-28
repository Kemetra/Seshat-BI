"""Governed single- and two-proportion evidence."""

from __future__ import annotations

import math

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


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _indexes(context: MethodContext) -> tuple[int, int, int | None]:
    indexes = []
    for role in ("numerator", "denominator"):
        binding = context.spec.roles[role]
        try:
            indexes.append(context.data.columns.index(binding.column))
        except ValueError as exc:
            raise _withheld(
                "STAT_PROVIDER_INVALID_DATA",
                f"The acquired data omits the governed {role} column.",
                "Repair the provider projection and rerun the analysis.",
            ) from exc
    group = context.spec.roles.get("group")
    if group is None:
        return indexes[0], indexes[1], None
    try:
        group_index = context.data.columns.index(group.column)
    except ValueError as exc:
        raise _withheld(
            "STAT_PROVIDER_INVALID_DATA",
            "The acquired data omits the governed group column.",
            "Repair the provider projection and rerun the analysis.",
        ) from exc
    return indexes[0], indexes[1], group_index


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _count(value: object, role: str) -> int:
    if isinstance(value, bool):
        raise _withheld(
            "STAT_INVALID_COUNT",
            f"The {role} role contains a boolean rather than a count.",
            "Provide non-negative integer counts.",
        )
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_INVALID_COUNT",
            f"The {role} role contains a non-numeric count.",
            "Provide non-negative integer counts.",
        ) from exc
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        raise _withheld(
            "STAT_INVALID_COUNT",
            f"The {role} role must contain finite non-negative integer counts.",
            "Provide non-negative integer counts.",
        )
    return int(number)


def _counts(context: MethodContext):
    numerator_index, denominator_index, group_index = _indexes(context)
    grouped: dict[str, list[int]] = {}
    missing = 0
    for row in context.data.rows:
        numerator = row[numerator_index]
        denominator = row[denominator_index]
        group = row[group_index] if group_index is not None else "__all__"
        if _missing(numerator) or _missing(denominator) or _missing(group):
            missing += 1
            continue
        successes = _count(numerator, "numerator")
        trials = _count(denominator, "denominator")
        if successes > trials:
            raise _withheld(
                "STAT_INVALID_PROPORTION",
                "A numerator count exceeds its denominator.",
                "Repair the approved numerator and denominator counts.",
            )
        bucket = grouped.setdefault(str(group), [0, 0])
        bucket[0] += successes
        bucket[1] += trials
    if missing and context.spec.missing_policy == "fail":
        raise _withheld(
            "STAT_MISSING_DATA",
            (
                "Proportion input contains missing numerator, denominator, "
                "or group values."
            ),
            "Resolve missing values or approve a non-failing missing-data policy.",
        )
    return grouped, missing


def _validate_denominator(
    successes: int, trials: int, minimum: int, privacy_floor: int
) -> None:
    if trials == 0:
        raise _withheld(
            "STAT_ZERO_DENOMINATOR",
            "A governed proportion denominator is zero.",
            "Provide a positive eligible denominator.",
        )
    floor = max(minimum, privacy_floor)
    if trials < floor:
        raise _withheld(
            "STAT_MINIMUM_DENOMINATOR",
            f"A governed proportion denominator is below the approved floor {floor}.",
            "Provide a larger eligible denominator or revise the approved floor.",
        )
    if successes > trials:
        raise _withheld(
            "STAT_INVALID_PROPORTION",
            "A numerator count exceeds its denominator.",
            "Repair the approved numerator and denominator counts.",
        )


def _interval(successes: int, trials: int, method: str, level: str) -> Interval:
    from scipy import stats

    scipy_method = "exact" if method == "exact_binomial" else "wilson"
    result = stats.binomtest(successes, trials).proportion_ci(
        confidence_level=float(level), method=scipy_method
    )
    return Interval(
        "proportion",
        decimal_text(float(result.low)),
        decimal_text(float(result.high)),
        level,
        f"{scipy_method} binomial",
    )


def _comparison(
    first: tuple[int, int],
    second: tuple[int, int],
    method: str,
    alternative: str,
    level: str,
    correction: str,
):
    import numpy as np
    from scipy import stats

    a, n1 = first
    c, n2 = second
    b, d = n1 - a, n2 - c
    table = np.asarray([[a, b], [c, d]], dtype=np.float64)
    if method == "chi_square":
        if alternative != "two-sided":
            raise _withheld(
                "STAT_ALTERNATIVE_INVALID",
                "Chi-square comparison requires the two-sided alternative.",
                "Use two-sided or explicitly select Fisher exact.",
            )
        result = stats.chi2_contingency(table, correction=False)
        if np.any(result.expected_freq < 5):
            raise _withheld(
                "STAT_EXPECTED_CELL_COUNT",
                "Chi-square expected cell counts violate the declared minimum of five.",
                "Use an explicitly approved Fisher exact analysis or more data.",
            )
        statistic = float(result.statistic)
        p_value = float(result.pvalue)
    elif method == "fisher_exact":
        result = stats.fisher_exact(table, alternative=alternative)
        statistic = float(result.statistic)
        p_value = float(result.pvalue)
    else:
        raise _withheld(
            "STAT_COMPARISON_REQUIRED",
            "Two grouped proportions require an explicit comparison method.",
            "Declare chi_square or fisher_exact.",
        )

    adjusted = table.copy()
    if np.any(adjusted == 0):
        if correction != "haldane-anscombe":
            raise _withheld(
                "STAT_ZERO_CELL",
                (
                    "A zero cell makes ratio intervals undefined without "
                    "explicit correction."
                ),
                "Approve haldane-anscombe correction or provide non-zero cells.",
            )
        adjusted += 0.5
    aa, bb = adjusted[0]
    cc, dd = adjusted[1]
    nn1, nn2 = aa + bb, cc + dd
    p1, p2 = aa / nn1, cc / nn2
    raw_p1, raw_p2 = a / n1, c / n2
    difference = raw_p1 - raw_p2
    ratio = p1 / p2
    odds_ratio = (aa * dd) / (bb * cc)
    z = float(stats.norm.ppf(1 - (1 - float(level)) / 2))
    difference_se = math.sqrt(raw_p1 * (1 - raw_p1) / n1 + raw_p2 * (1 - raw_p2) / n2)
    ratio_se = math.sqrt(1 / aa - 1 / nn1 + 1 / cc - 1 / nn2)
    odds_se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)

    def log_interval(name: str, estimate: float, standard_error: float) -> Interval:
        return Interval(
            name,
            decimal_text(math.exp(math.log(estimate) - z * standard_error)),
            decimal_text(math.exp(math.log(estimate) + z * standard_error)),
            level,
            "log normal",
        )

    intervals = (
        Interval(
            "risk_difference",
            decimal_text(difference - z * difference_se),
            decimal_text(difference + z * difference_se),
            level,
            "normal",
        ),
        log_interval("risk_ratio", ratio, ratio_se),
        log_interval("odds_ratio", odds_ratio, odds_se),
    )
    test = TestStatistic(
        method,
        decimal_text(statistic) if math.isfinite(statistic) else None,
        decimal_text(p_value),
        decimal_text(p_value),
        alternative,
        method,
    )
    effects = (
        Estimate("risk_difference", decimal_text(difference), None),
        Estimate("risk_ratio", decimal_text(ratio), None),
        Estimate("odds_ratio", decimal_text(odds_ratio), None),
    )
    return test, effects, intervals


def run_proportion(context: MethodContext) -> MethodResult:
    """Compute only the explicitly governed proportion analysis."""

    parameters = context.spec.method.parameters
    level = str(parameters["confidence_level"])
    interval_method = str(parameters["interval"])
    alternative = str(parameters["alternative"])
    comparison = str(parameters.get("comparison", "none"))
    correction = str(parameters.get("zero_cell_correction", "none"))
    minimum = int(parameters.get("minimum_denominator", 1))
    privacy_floor = int(context.spec.pii["minimum_group_count"])
    grouped, missing = _counts(context)
    if not grouped:
        raise _withheld(
            "STAT_MINIMUM_DATA",
            "No complete proportion observations remain.",
            "Provide complete approved numerator and denominator counts.",
        )
    for successes, trials in grouped.values():
        _validate_denominator(successes, trials, minimum, privacy_floor)

    diagnostics = ()
    if missing:
        diagnostics = (
            Diagnostic(
                "STAT_MISSING_ROWS_EXCLUDED",
                "warning",
                str(missing),
                "Rows with incomplete proportion status were excluded.",
            ),
        )
    labels = tuple(sorted(grouped))
    estimates = tuple(
        item
        for label in labels
        for item in (
            Estimate(f"group[{label}].successes", str(grouped[label][0]), None),
            Estimate(f"group[{label}].trials", str(grouped[label][1]), None),
            Estimate(
                f"group[{label}].proportion",
                decimal_text(grouped[label][0] / grouped[label][1]),
                None,
            ),
        )
    )
    if labels == ("__all__",):
        successes, trials = grouped["__all__"]
        return MethodResult(
            estimates=(
                Estimate("successes", str(successes), None),
                Estimate("trials", str(trials), None),
                Estimate("proportion", decimal_text(successes / trials), None),
            ),
            intervals=(_interval(successes, trials, interval_method, level),),
            diagnostics=diagnostics,
        )
    if len(labels) != 2:
        raise _withheld(
            "STAT_GROUP_COUNT_INVALID",
            "Proportion comparison requires exactly two eligible groups.",
            "Provide exactly two groups above the approved denominator floor.",
        )
    test, effects, intervals = _comparison(
        tuple(grouped[labels[0]]),
        tuple(grouped[labels[1]]),
        comparison,
        alternative,
        level,
        correction,
    )
    return MethodResult(
        estimates=estimates,
        effect_sizes=effects,
        intervals=intervals,
        tests=(test,),
        diagnostics=diagnostics,
        interpretation_cautions=(
            "Proportion comparisons are derived evidence, not proof of causation.",
        ),
    )
