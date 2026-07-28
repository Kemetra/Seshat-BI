"""Explicit governed group comparisons without automatic test selection."""

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
from .common import finite_array, numeric_role, safe_groups
from .inference import (
    adjust_pvalues,
    bootstrap_interval,
    epsilon_squared,
    hedges_g,
    omega_squared,
    paired_standardized_change,
    rank_biserial,
)

_TWO_GROUP = frozenset({"welch_t", "paired_t", "mann_whitney", "wilcoxon"})
_PAIRED = frozenset({"paired_t", "wilcoxon"})
_OMNIBUS = frozenset({"welch_anova", "kruskal_wallis"})


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _finite(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _withheld(
            "STAT_TEST_UNDEFINED",
            f"The {label} is not a finite statistical result.",
            "Provide samples for which the declared test is defined.",
        ) from exc
    if not math.isfinite(number):
        raise _withheld(
            "STAT_TEST_UNDEFINED",
            f"The {label} is not a finite statistical result.",
            "Provide samples for which the declared test is defined.",
        )
    return number


def _prepared_groups(context: MethodContext):
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
    return values, rows, suppressed


def _ordered_labels(context: MethodContext, available: set[str]) -> tuple[str, ...]:
    declared = context.spec.method.parameters.get("group_order")
    labels = (
        tuple(str(item) for item in declared) if declared else tuple(sorted(available))
    )
    if len(labels) != len(set(labels)) or set(labels) != available:
        raise _withheld(
            "STAT_GROUP_ORDER_INVALID",
            "Declared group order does not match the privacy-safe groups.",
            "Declare every eligible group exactly once in group_order.",
        )
    return labels


def _identifier_index(context: MethodContext) -> int:
    binding = context.spec.roles.get("identifier")
    if binding is None:
        raise _withheld(
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


def _paired_values(
    context: MethodContext,
    labels: tuple[str, str],
    values: dict[str, object],
    rows: dict[str, tuple[int, ...]],
):
    identifier_index = _identifier_index(context)
    aligned: list[dict[str, float]] = []
    for label in labels:
        mapping: dict[str, float] = {}
        group_values = values[label].tolist()
        for row_index, value in zip(rows[label], group_values, strict=True):
            raw_identifier = context.data.rows[row_index][identifier_index]
            if raw_identifier is None or (
                isinstance(raw_identifier, str) and not raw_identifier.strip()
            ):
                raise _withheld(
                    "STAT_PAIRING_INVALID",
                    "A paired observation has a missing identifier.",
                    "Provide one non-missing unique identifier for every pair.",
                )
            identifier = str(raw_identifier)
            if identifier in mapping:
                raise _withheld(
                    "STAT_PAIRING_INVALID",
                    "A paired group contains a duplicated identifier.",
                    "Provide exactly one observation per identifier and group.",
                )
            mapping[identifier] = value
        aligned.append(mapping)
    if set(aligned[0]) != set(aligned[1]):
        raise _withheld(
            "STAT_PAIRING_INVALID",
            "Paired groups contain unmatched identifiers.",
            "Provide one aligned observation in both groups for every identifier.",
        )
    identifiers = sorted(aligned[0])
    minimum = context.spec.minimum_data.get("observations", 1)
    if len(identifiers) < minimum:
        raise _withheld(
            "STAT_MINIMUM_DATA",
            "The aligned pair count is below the governed observation minimum.",
            "Provide more complete approved pairs.",
        )
    return (
        finite_array((aligned[0][item] for item in identifiers), "response"),
        finite_array((aligned[1][item] for item in identifiers), "response"),
    )


def _test_result(
    name: str,
    statistic: float,
    p_value: float,
    alternative: str,
    method: str,
    adjusted: float | None = None,
) -> TestStatistic:
    return TestStatistic(
        name=name,
        statistic=decimal_text(statistic),
        p_value=decimal_text(p_value),
        adjusted_p_value=decimal_text(p_value if adjusted is None else adjusted),
        alternative=alternative,
        method=method,
    )


def _two_group_test(test: str, left, right, alternative: str):
    from scipy import stats

    if test == "welch_t":
        result = stats.ttest_ind(left, right, equal_var=False, alternative=alternative)
        effect_name = "hedges_g"
        effect = hedges_g(left, right)
    elif test == "paired_t":
        result = stats.ttest_rel(left, right, alternative=alternative)
        effect_name = "paired_standardized_change"
        effect = paired_standardized_change(right, left)
    elif test == "mann_whitney":
        result = stats.mannwhitneyu(left, right, alternative=alternative)
        effect_name = "rank_biserial"
        effect = rank_biserial(left, right)
    elif test == "wilcoxon":
        result = stats.wilcoxon(left, right, alternative=alternative)
        effect_name = "rank_biserial"
        effect = rank_biserial(right, left, paired=True)
    else:
        raise _withheld(
            "STAT_METHOD_REFUSED",
            "The declared two-group test is outside the governed catalog.",
            "Choose a test defined by the analysis schema.",
        )
    return (
        _finite(result.statistic, "test statistic"),
        _finite(result.pvalue, "p-value"),
        effect_name,
        effect,
    )


def _post_hoc(
    context: MethodContext,
    groups: dict[str, object],
    *,
    selected: str,
    alternative: str,
    correction: str,
) -> tuple[tuple[TestStatistic, ...], tuple[Estimate, ...]]:
    declared = context.spec.method.parameters.get("post_hoc_pairs", ())
    pairs = tuple(tuple(str(label) for label in pair) for pair in declared)
    if not pairs:
        return (), ()
    if correction == "none":
        raise _withheld(
            "STAT_MULTIPLICITY_REQUIRED",
            "Multiple post-hoc comparisons require a declared correction.",
            "Use holm or benjamini-hochberg for the complete comparison family.",
        )
    compatible = "welch_t" if selected == "welch_anova" else "mann_whitney"
    raw: list[tuple[str, float, float, str, float]] = []
    for left_label, right_label in pairs:
        if left_label not in groups or right_label not in groups:
            raise _withheld(
                "STAT_POST_HOC_INVALID",
                "A declared post-hoc pair is not privacy-safe and available.",
                "Declare pairs only from eligible groups above the privacy floor.",
            )
        statistic, p_value, effect_name, effect = _two_group_test(
            compatible, groups[left_label], groups[right_label], alternative
        )
        raw.append(
            (
                f"{compatible}[{left_label},{right_label}]",
                statistic,
                p_value,
                effect_name,
                effect,
            )
        )
    adjusted = adjust_pvalues((item[2] for item in raw), correction)
    tests = tuple(
        _test_result(name, statistic, p_value, alternative, compatible, corrected)
        for (name, statistic, p_value, _, _), corrected in zip(
            raw, adjusted, strict=True
        )
    )
    effects = tuple(
        Estimate(f"{effect_name}[{name}]", decimal_text(effect), None)
        for name, _, _, effect_name, effect in raw
    )
    return tests, effects


def run_compare_groups(context: MethodContext) -> MethodResult:
    """Run exactly the declared group-comparison method."""

    from scipy import stats

    parameters = context.spec.method.parameters
    selected = str(parameters["test"])
    alternative = str(parameters["alternative"])
    level = str(parameters["confidence_level"])
    correction = str(parameters["correction"])
    groups, rows, suppressed = _prepared_groups(context)
    labels = _ordered_labels(context, set(groups))

    diagnostics: list[Diagnostic] = []
    if suppressed:
        diagnostics.append(
            Diagnostic(
                "STAT_GROUPS_SUPPRESSED",
                "warning",
                str(suppressed),
                "Groups below the approved minimum count were suppressed.",
            )
        )
    estimates = tuple(
        Estimate(f"group[{label}].count", decimal_text(len(groups[label])), None)
        for label in labels
    )

    if selected in _TWO_GROUP:
        if len(labels) != 2:
            raise _withheld(
                "STAT_GROUP_COUNT_INVALID",
                "The declared two-group test requires exactly two eligible groups.",
                "Provide exactly two groups above the approved privacy floor.",
            )
        left, right = groups[labels[0]], groups[labels[1]]
        if selected in _PAIRED:
            left, right = _paired_values(context, (labels[0], labels[1]), groups, rows)
        statistic, p_value, effect_name, effect = _two_group_test(
            selected, left, right, alternative
        )
        adjusted = adjust_pvalues((p_value,), correction)[0]
        tests = (
            _test_result(selected, statistic, p_value, alternative, selected, adjusted),
        )
        effects = (Estimate(effect_name, decimal_text(effect), None),)
        intervals: tuple[Interval, ...] = ()
        if selected in {"welch_t", "paired_t"}:
            paired = selected == "paired_t"

            def difference(first, second):
                import numpy as np

                if paired:
                    return np.mean(first - second)
                return np.mean(first) - np.mean(second)

            interval = bootstrap_interval(
                (left, right),
                difference,
                level,
                context.spec.random_seed,
                paired=paired,
            )
            intervals = (
                Interval(
                    "mean_difference",
                    interval.low,
                    interval.high,
                    interval.level,
                    interval.method,
                ),
            )
    elif selected in _OMNIBUS:
        if len(labels) < 3:
            raise _withheld(
                "STAT_GROUP_COUNT_INVALID",
                "The declared omnibus test requires at least three eligible groups.",
                "Provide at least three groups above the approved privacy floor.",
            )
        if alternative != "two-sided":
            raise _withheld(
                "STAT_ALTERNATIVE_INVALID",
                "Omnibus group tests require the two-sided alternative.",
                "Set method.parameters.alternative to two-sided.",
            )
        samples = tuple(groups[label] for label in labels)
        if selected == "welch_anova":
            result = stats.f_oneway(*samples, equal_var=False)
            effect_name = "omega_squared"
            effect = omega_squared(
                _finite(result.statistic, "test statistic"),
                group_count=len(samples),
                total_count=sum(len(sample) for sample in samples),
            )
        else:
            result = stats.kruskal(*samples)
            effect_name = "epsilon_squared"
            effect = epsilon_squared(
                _finite(result.statistic, "test statistic"),
                group_count=len(samples),
                total_count=sum(len(sample) for sample in samples),
            )
        statistic = _finite(result.statistic, "test statistic")
        p_value = _finite(result.pvalue, "p-value")
        tests = (_test_result(selected, statistic, p_value, alternative, selected),)
        effects = (Estimate(effect_name, decimal_text(effect), None),)
        intervals = ()
        post_tests, post_effects = _post_hoc(
            context,
            groups,
            selected=selected,
            alternative=alternative,
            correction=correction,
        )
        tests += post_tests
        effects += post_effects
    else:
        raise _withheld(
            "STAT_METHOD_REFUSED",
            "The declared group test is outside the governed catalog.",
            "Choose a test defined by the analysis schema.",
        )

    return MethodResult(
        estimates=estimates,
        effect_sizes=effects,
        intervals=intervals,
        tests=tests,
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Group comparisons are derived evidence, not proof of causation.",
        ),
    )
