"""Governed single- and two-proportion evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

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

_UNGROUPED = "__all__"


@dataclass(frozen=True, slots=True)
class _Rule:
    """The declared comparison and interval rules of one proportion analysis."""

    interval: str
    alternative: str
    comparison: str
    correction: str
    level: str
    minimum_denominator: int
    privacy_floor: int


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _invalid_count(message: str) -> AnalysisWithheld:
    return _withheld(
        "STAT_INVALID_COUNT", message, "Provide non-negative integer counts."
    )


def _column_index(context: MethodContext, role: str, column: str) -> int:
    try:
        return context.data.columns.index(column)
    except ValueError as exc:
        raise _withheld(
            "STAT_PROVIDER_INVALID_DATA",
            f"The acquired data omits the governed {role} column.",
            "Repair the provider projection and rerun the analysis.",
        ) from exc


def _indexes(context: MethodContext) -> tuple[int, int, int | None]:
    numerator = _column_index(
        context, "numerator", context.spec.roles["numerator"].column
    )
    denominator = _column_index(
        context, "denominator", context.spec.roles["denominator"].column
    )
    group = context.spec.roles.get("group")
    if group is None:
        return numerator, denominator, None
    return numerator, denominator, _column_index(context, "group", group.column)


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_count(number: float) -> bool:
    return math.isfinite(number) and number >= 0 and number.is_integer()


def _count(value: object, role: str) -> int:
    require(
        not isinstance(value, bool),
        "STAT_INVALID_COUNT",
        f"The {role} role contains a boolean rather than a count.",
        "Provide non-negative integer counts.",
    )
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        raise _invalid_count(f"The {role} role contains a non-numeric count.") from exc
    require(
        _is_count(number),
        "STAT_INVALID_COUNT",
        f"The {role} role must contain finite non-negative integer counts.",
        "Provide non-negative integer counts.",
    )
    return int(number)


def _pair(numerator: object, denominator: object) -> tuple[int, int]:
    successes = _count(numerator, "numerator")
    trials = _count(denominator, "denominator")
    require(
        successes <= trials,
        "STAT_INVALID_PROPORTION",
        "A numerator count exceeds its denominator.",
        "Repair the approved numerator and denominator counts.",
    )
    return successes, trials


def _counts(context: MethodContext):
    """Accumulate successes and trials per eligible group label."""

    numerator_index, denominator_index, group_index = _indexes(context)
    grouped: dict[str, list[int]] = {}
    missing = 0
    for row in context.data.rows:
        cells = (
            row[numerator_index],
            row[denominator_index],
            row[group_index] if group_index is not None else _UNGROUPED,
        )
        if any(_missing(cell) for cell in cells):
            missing += 1
            continue
        successes, trials = _pair(cells[0], cells[1])
        bucket = grouped.setdefault(str(cells[2]), [0, 0])
        bucket[0] += successes
        bucket[1] += trials
    require(
        not missing or context.spec.missing_policy != "fail",
        "STAT_MISSING_DATA",
        "Proportion input contains missing numerator, denominator, or group values.",
        "Resolve missing values or approve a non-failing missing-data policy.",
    )
    return grouped, missing


def _validate_denominator(successes: int, trials: int, rule: _Rule) -> None:
    require(
        trials != 0,
        "STAT_ZERO_DENOMINATOR",
        "A governed proportion denominator is zero.",
        "Provide a positive eligible denominator.",
    )
    floor = max(rule.minimum_denominator, rule.privacy_floor)
    require(
        trials >= floor,
        "STAT_MINIMUM_DENOMINATOR",
        f"A governed proportion denominator is below the approved floor {floor}.",
        "Provide a larger eligible denominator or revise the approved floor.",
    )
    require(
        successes <= trials,
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


def _chi_square_result(table, rule: _Rule) -> tuple[float, float]:
    import numpy as np
    from scipy import stats

    require(
        rule.alternative == "two-sided",
        "STAT_ALTERNATIVE_INVALID",
        "Chi-square comparison requires the two-sided alternative.",
        "Use two-sided or explicitly select Fisher exact.",
    )
    result = stats.chi2_contingency(table, correction=False)
    require(
        not np.any(result.expected_freq < 5),
        "STAT_EXPECTED_CELL_COUNT",
        "Chi-square expected cell counts violate the declared minimum of five.",
        "Use an explicitly approved Fisher exact analysis or more data.",
    )
    return float(result.statistic), float(result.pvalue)


def _fisher_result(table, rule: _Rule) -> tuple[float, float]:
    from scipy import stats

    result = stats.fisher_exact(table, alternative=rule.alternative)
    return float(result.statistic), float(result.pvalue)


def _comparison_result(table, rule: _Rule) -> tuple[float, float]:
    if rule.comparison == "chi_square":
        return _chi_square_result(table, rule)
    if rule.comparison == "fisher_exact":
        return _fisher_result(table, rule)
    raise _withheld(
        "STAT_COMPARISON_REQUIRED",
        "Two grouped proportions require an explicit comparison method.",
        "Declare chi_square or fisher_exact.",
    )


def _corrected_table(table, rule: _Rule):
    """Apply the approved zero-cell correction, or refuse an undefined ratio."""

    import numpy as np

    adjusted = table.copy()
    if not np.any(adjusted == 0):
        return adjusted
    require(
        rule.correction == "haldane-anscombe",
        "STAT_ZERO_CELL",
        "A zero cell makes ratio intervals undefined without explicit correction.",
        "Approve haldane-anscombe correction or provide non-zero cells.",
    )
    return adjusted + 0.5


def _ratio_evidence(
    first: tuple[int, int], second: tuple[int, int], adjusted, level: str
):
    """Report the risk difference, risk ratio, and odds ratio with intervals."""

    from scipy import stats

    a, n1 = first
    c, n2 = second
    aa, bb = adjusted[0]
    cc, dd = adjusted[1]
    nn1, nn2 = aa + bb, cc + dd
    raw_p1, raw_p2 = a / n1, c / n2
    difference = raw_p1 - raw_p2
    ratio = (aa / nn1) / (cc / nn2)
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
    effects = (
        Estimate("risk_difference", decimal_text(difference), None),
        Estimate("risk_ratio", decimal_text(ratio), None),
        Estimate("odds_ratio", decimal_text(odds_ratio), None),
    )
    return effects, intervals


def _comparison(first: tuple[int, int], second: tuple[int, int], rule: _Rule):
    import numpy as np

    a, n1 = first
    c, n2 = second
    table = np.asarray([[a, n1 - a], [c, n2 - c]], dtype=np.float64)
    statistic, p_value = _comparison_result(table, rule)
    effects, intervals = _ratio_evidence(
        first, second, _corrected_table(table, rule), rule.level
    )
    test = TestStatistic(
        rule.comparison,
        decimal_text(statistic) if math.isfinite(statistic) else None,
        decimal_text(p_value),
        decimal_text(p_value),
        rule.alternative,
        rule.comparison,
    )
    return test, effects, intervals


def _rule(context: MethodContext) -> _Rule:
    parameters = context.spec.method.parameters
    return _Rule(
        interval=str(parameters["interval"]),
        alternative=str(parameters["alternative"]),
        comparison=str(parameters.get("comparison", "none")),
        correction=str(parameters.get("zero_cell_correction", "none")),
        level=str(parameters["confidence_level"]),
        minimum_denominator=int(parameters.get("minimum_denominator", 1)),
        privacy_floor=int(context.spec.pii["minimum_group_count"]),
    )


def _group_estimates(grouped: Mapping[str, list[int]], labels: tuple[str, ...]):
    return tuple(
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


def _single_proportion(
    grouped: Mapping[str, list[int]], rule: _Rule, diagnostics
) -> MethodResult:
    successes, trials = grouped[_UNGROUPED]
    return MethodResult(
        estimates=(
            Estimate("successes", str(successes), None),
            Estimate("trials", str(trials), None),
            Estimate("proportion", decimal_text(successes / trials), None),
        ),
        intervals=(_interval(successes, trials, rule.interval, rule.level),),
        diagnostics=diagnostics,
    )


def run_proportion(context: MethodContext) -> MethodResult:
    """Compute only the explicitly governed proportion analysis."""

    rule = _rule(context)
    grouped, missing = _counts(context)
    require(
        grouped,
        "STAT_MINIMUM_DATA",
        "No complete proportion observations remain.",
        "Provide complete approved numerator and denominator counts.",
    )
    for successes, trials in grouped.values():
        _validate_denominator(successes, trials, rule)

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
    if labels == (_UNGROUPED,):
        return _single_proportion(grouped, rule, diagnostics)
    require(
        len(labels) == 2,
        "STAT_GROUP_COUNT_INVALID",
        "Proportion comparison requires exactly two eligible groups.",
        "Provide exactly two groups above the approved denominator floor.",
    )
    test, effects, intervals = _comparison(
        tuple(grouped[labels[0]]), tuple(grouped[labels[1]]), rule
    )
    return MethodResult(
        estimates=_group_estimates(grouped, labels),
        effect_sizes=effects,
        intervals=intervals,
        tests=(test,),
        diagnostics=diagnostics,
        interpretation_cautions=(
            "Proportion comparisons are derived evidence, not proof of causation.",
        ),
    )
