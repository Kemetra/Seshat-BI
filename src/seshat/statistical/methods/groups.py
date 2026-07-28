"""Explicit governed group comparisons without automatic test selection."""

from __future__ import annotations

import math
from dataclasses import dataclass

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
from .common import finite_array, numeric_role, safe_groups
from .inference import (
    BootstrapRequest,
    adjust_pvalues,
    bootstrap_interval,
    epsilon_squared,
    hedges_g,
    omega_squared,
    paired_standardized_change,
    rank_biserial,
)

_PAIRED = frozenset({"paired_t", "wilcoxon"})
_OMNIBUS = frozenset({"welch_anova", "kruskal_wallis"})
_MEAN_DIFFERENCE = frozenset({"welch_t", "paired_t"})


@dataclass(frozen=True, slots=True)
class _Plan:
    """The declared comparison rules, read once from the approved parameters."""

    test: str
    alternative: str
    level: str
    correction: str


@dataclass(frozen=True, slots=True)
class _Prepared:
    """Privacy-safe group values with the rows they came from."""

    values: dict[str, object]
    rows: dict[str, tuple[int, ...]]
    suppressed: int


@dataclass(frozen=True, slots=True)
class _Outcome:
    """One test's finite statistic and its paired effect size."""

    statistic: float
    p_value: float
    effect_name: str
    effect: float


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _refused(message: str) -> AnalysisWithheld:
    return _withheld(
        "STAT_METHOD_REFUSED", message, "Choose a test defined by the analysis schema."
    )


def _pairing_invalid(message: str, recovery: str) -> AnalysisWithheld:
    return _withheld("STAT_PAIRING_INVALID", message, recovery)


def _finite(value: object, label: str) -> float:
    message = f"The {label} is not a finite statistical result."
    recovery = "Provide samples for which the declared test is defined."
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld("STAT_TEST_UNDEFINED", message, recovery) from exc
    require(math.isfinite(number), "STAT_TEST_UNDEFINED", message, recovery)
    return number


def _prepared_groups(context: MethodContext) -> _Prepared:
    sample = numeric_role(context, "response")
    grouped = safe_groups(context)
    by_row = dict(zip(sample.row_indices, sample.values.tolist(), strict=True))
    floor = int(context.spec.pii["minimum_group_count"])
    values: dict[str, object] = {}
    rows: dict[str, tuple[int, ...]] = {}
    suppressed = grouped.suppressed_count
    for group in grouped.groups:
        retained_rows = tuple(index for index in group.row_indices if index in by_row)
        if len(retained_rows) < floor:
            suppressed += 1
            continue
        values[group.label] = finite_array(
            (by_row[index] for index in retained_rows), "response"
        )
        rows[group.label] = retained_rows
    return _Prepared(values, rows, suppressed)


def _ordered_labels(context: MethodContext, available: set[str]) -> tuple[str, ...]:
    declared = context.spec.method.parameters.get("group_order")
    labels = (
        tuple(str(item) for item in declared) if declared else tuple(sorted(available))
    )
    unique = len(labels) == len(set(labels))
    require(
        unique and set(labels) == available,
        "STAT_GROUP_ORDER_INVALID",
        "Declared group order does not match the privacy-safe groups.",
        "Declare every eligible group exactly once in group_order.",
    )
    return labels


def _identifier_index(context: MethodContext) -> int:
    binding = context.spec.roles.get("identifier")
    require(
        binding is not None,
        "STAT_PAIR_IDENTIFIER_MISSING",
        "Paired tests require a governed identifier role.",
        "Bind an approved unique pair identifier.",
    )
    try:
        return context.data.columns.index(binding.column)
    except ValueError as exc:
        raise _withheld(
            "STAT_PAIR_IDENTIFIER_MISSING",
            "The provider result omits the governed pair identifier.",
            "Project the approved identifier column from the provider.",
        ) from exc


def _identifier(raw: object) -> str:
    present = raw is not None and (not isinstance(raw, str) or raw.strip())
    if not present:
        raise _pairing_invalid(
            "A paired observation has a missing identifier.",
            "Provide one non-missing unique identifier for every pair.",
        )
    return str(raw)


def _identified_values(context: MethodContext, index: int, rows, group_values):
    """Map each pair identifier in one group to its response value."""

    mapping: dict[str, float] = {}
    for row_index, value in zip(rows, group_values, strict=True):
        identifier = _identifier(context.data.rows[row_index][index])
        if identifier in mapping:
            raise _pairing_invalid(
                "A paired group contains a duplicated identifier.",
                "Provide exactly one observation per identifier and group.",
            )
        mapping[identifier] = value
    return mapping


def _paired_values(
    context: MethodContext,
    labels: tuple[str, str],
    values: dict[str, object],
    rows: dict[str, tuple[int, ...]],
):
    """Align two groups on their approved pair identifiers, in identifier order."""

    index = _identifier_index(context)
    aligned = [
        _identified_values(context, index, rows[label], values[label].tolist())
        for label in labels
    ]
    require(
        set(aligned[0]) == set(aligned[1]),
        "STAT_PAIRING_INVALID",
        "Paired groups contain unmatched identifiers.",
        "Provide one aligned observation in both groups for every identifier.",
    )
    identifiers = sorted(aligned[0])
    require(
        len(identifiers) >= context.spec.minimum_data.get("observations", 1),
        "STAT_MINIMUM_DATA",
        "The aligned pair count is below the governed observation minimum.",
        "Provide more complete approved pairs.",
    )
    return (
        finite_array((aligned[0][item] for item in identifiers), "response"),
        finite_array((aligned[1][item] for item in identifiers), "response"),
    )


def _test_statistic(
    name: str, outcome: _Outcome, plan: _Plan, adjusted: float | None = None
) -> TestStatistic:
    p_value = outcome.p_value
    return TestStatistic(
        name=name,
        statistic=decimal_text(outcome.statistic),
        p_value=decimal_text(p_value),
        adjusted_p_value=decimal_text(p_value if adjusted is None else adjusted),
        alternative=plan.alternative,
        method=plan.test,
    )


def _welch_t(left, right, alternative: str) -> _Outcome:
    from scipy import stats

    result = stats.ttest_ind(left, right, equal_var=False, alternative=alternative)
    return _outcome(result, "hedges_g", hedges_g(left, right))


def _paired_t(left, right, alternative: str) -> _Outcome:
    from scipy import stats

    result = stats.ttest_rel(left, right, alternative=alternative)
    effect = paired_standardized_change(right, left)
    return _outcome(result, "paired_standardized_change", effect)


def _mann_whitney(left, right, alternative: str) -> _Outcome:
    from scipy import stats

    result = stats.mannwhitneyu(left, right, alternative=alternative)
    return _outcome(result, "rank_biserial", rank_biserial(left, right))


def _wilcoxon(left, right, alternative: str) -> _Outcome:
    from scipy import stats

    result = stats.wilcoxon(left, right, alternative=alternative)
    effect = rank_biserial(right, left, paired=True)
    return _outcome(result, "rank_biserial", effect)


def _outcome(result, effect_name: str, effect: float) -> _Outcome:
    return _Outcome(
        _finite(result.statistic, "test statistic"),
        _finite(result.pvalue, "p-value"),
        effect_name,
        effect,
    )


_TWO_GROUP_TESTS = {
    "welch_t": _welch_t,
    "paired_t": _paired_t,
    "mann_whitney": _mann_whitney,
    "wilcoxon": _wilcoxon,
}


def _two_group_test(test: str, left, right, alternative: str) -> _Outcome:
    runner = _TWO_GROUP_TESTS.get(test)
    if runner is None:
        raise _refused("The declared two-group test is outside the governed catalog.")
    return runner(left, right, alternative)


def _post_hoc_outcome(groups: dict[str, object], pair: tuple[str, str], plan: _Plan):
    left_label, right_label = pair
    require(
        left_label in groups and right_label in groups,
        "STAT_POST_HOC_INVALID",
        "A declared post-hoc pair is not privacy-safe and available.",
        "Declare pairs only from eligible groups above the privacy floor.",
    )
    outcome = _two_group_test(
        plan.test, groups[left_label], groups[right_label], plan.alternative
    )
    return f"{plan.test}[{left_label},{right_label}]", outcome


def _post_hoc(context: MethodContext, groups: dict[str, object], plan: _Plan):
    """Run only the explicitly declared post-hoc pairs, corrected as a family."""

    declared = context.spec.method.parameters.get("post_hoc_pairs", ())
    pairs = tuple(tuple(str(label) for label in pair) for pair in declared)
    if not pairs:
        return (), ()
    require(
        plan.correction != "none",
        "STAT_MULTIPLICITY_REQUIRED",
        "Multiple post-hoc comparisons require a declared correction.",
        "Use holm or benjamini-hochberg for the complete comparison family.",
    )
    compatible = "welch_t" if plan.test == "welch_anova" else "mann_whitney"
    pair_plan = _Plan(compatible, plan.alternative, plan.level, plan.correction)
    measured = [_post_hoc_outcome(groups, pair, pair_plan) for pair in pairs]
    adjusted = adjust_pvalues(
        (outcome.p_value for _, outcome in measured), plan.correction
    )
    tests = tuple(
        _test_statistic(name, outcome, pair_plan, corrected)
        for (name, outcome), corrected in zip(measured, adjusted, strict=True)
    )
    effects = tuple(
        Estimate(f"{outcome.effect_name}[{name}]", decimal_text(outcome.effect), None)
        for name, outcome in measured
    )
    return tests, effects


def _mean_difference_interval(left, right, plan: _Plan, seed: int) -> Interval:
    paired = plan.test == "paired_t"

    def difference(first, second):
        import numpy as np

        if paired:
            return np.mean(first - second)
        return np.mean(first) - np.mean(second)

    interval = bootstrap_interval(
        (left, right), difference, BootstrapRequest(plan.level, seed, paired=paired)
    )
    return Interval(
        "mean_difference",
        interval.low,
        interval.high,
        interval.level,
        interval.method,
    )


def _two_group_evidence(
    context: MethodContext, prepared: _Prepared, labels: tuple[str, ...], plan: _Plan
):
    require(
        len(labels) == 2,
        "STAT_GROUP_COUNT_INVALID",
        "The declared two-group test requires exactly two eligible groups.",
        "Provide exactly two groups above the approved privacy floor.",
    )
    groups = prepared.values
    left, right = groups[labels[0]], groups[labels[1]]
    if plan.test in _PAIRED:
        left, right = _paired_values(
            context, (labels[0], labels[1]), groups, prepared.rows
        )
    outcome = _two_group_test(plan.test, left, right, plan.alternative)
    adjusted = adjust_pvalues((outcome.p_value,), plan.correction)[0]
    tests = (_test_statistic(plan.test, outcome, plan, adjusted),)
    effects = (Estimate(outcome.effect_name, decimal_text(outcome.effect), None),)
    intervals: tuple[Interval, ...] = ()
    if plan.test in _MEAN_DIFFERENCE:
        intervals = (
            _mean_difference_interval(left, right, plan, context.spec.random_seed),
        )
    return tests, effects, intervals


def _omnibus_outcome(samples: tuple[object, ...], plan: _Plan) -> _Outcome:
    from scipy import stats

    total = sum(len(sample) for sample in samples)
    if plan.test == "welch_anova":
        result = stats.f_oneway(*samples, equal_var=False)
        effect = omega_squared(
            _finite(result.statistic, "test statistic"),
            group_count=len(samples),
            total_count=total,
        )
        return _outcome(result, "omega_squared", effect)
    result = stats.kruskal(*samples)
    effect = epsilon_squared(
        _finite(result.statistic, "test statistic"),
        group_count=len(samples),
        total_count=total,
    )
    return _outcome(result, "epsilon_squared", effect)


def _omnibus_evidence(
    context: MethodContext, prepared: _Prepared, labels: tuple[str, ...], plan: _Plan
):
    require(
        len(labels) >= 3,
        "STAT_GROUP_COUNT_INVALID",
        "The declared omnibus test requires at least three eligible groups.",
        "Provide at least three groups above the approved privacy floor.",
    )
    require(
        plan.alternative == "two-sided",
        "STAT_ALTERNATIVE_INVALID",
        "Omnibus group tests require the two-sided alternative.",
        "Set method.parameters.alternative to two-sided.",
    )
    samples = tuple(prepared.values[label] for label in labels)
    outcome = _omnibus_outcome(samples, plan)
    tests = (_test_statistic(plan.test, outcome, plan),)
    effects = (Estimate(outcome.effect_name, decimal_text(outcome.effect), None),)
    post_tests, post_effects = _post_hoc(context, prepared.values, plan)
    return tests + post_tests, effects + post_effects, ()


def run_compare_groups(context: MethodContext) -> MethodResult:
    """Run exactly the declared group-comparison method."""

    parameters = context.spec.method.parameters
    plan = _Plan(
        test=str(parameters["test"]),
        alternative=str(parameters["alternative"]),
        level=str(parameters["confidence_level"]),
        correction=str(parameters["correction"]),
    )
    prepared = _prepared_groups(context)
    labels = _ordered_labels(context, set(prepared.values))

    diagnostics: tuple[Diagnostic, ...] = ()
    if prepared.suppressed:
        diagnostics = (
            Diagnostic(
                "STAT_GROUPS_SUPPRESSED",
                "warning",
                str(prepared.suppressed),
                "Groups below the approved minimum count were suppressed.",
            ),
        )
    estimates = tuple(
        Estimate(
            f"group[{label}].count",
            decimal_text(len(prepared.values[label])),
            None,
        )
        for label in labels
    )
    if plan.test in _TWO_GROUP_TESTS:
        tests, effects, intervals = _two_group_evidence(context, prepared, labels, plan)
    elif plan.test in _OMNIBUS:
        tests, effects, intervals = _omnibus_evidence(context, prepared, labels, plan)
    else:
        raise _refused("The declared group test is outside the governed catalog.")
    return MethodResult(
        estimates=estimates,
        effect_sizes=effects,
        intervals=intervals,
        tests=tests,
        diagnostics=diagnostics,
        interpretation_cautions=(
            "Group comparisons are derived evidence, not proof of causation.",
        ),
    )
