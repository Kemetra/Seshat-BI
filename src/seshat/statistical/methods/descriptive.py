"""Governed descriptive statistics with robust outlier summaries."""

from __future__ import annotations

import math
from collections.abc import Iterable

from ..contracts import Diagnostic, Estimate, MethodContext, MethodResult
from ..evidence import decimal_text
from .common import finite_array, numeric_role, safe_groups, unit_for_role

_ROBUST_Z_SCALE = 0.6744897501960817
_MAD_THRESHOLD = 3.5
_IQR_MULTIPLIER = 1.5


def _value(value: float | int) -> str | None:
    return decimal_text(value) if math.isfinite(float(value)) else None


def _estimate(name: str, value: float | int | None, unit: str | None) -> Estimate:
    return Estimate(name, None if value is None else _value(value), unit)


def _summary(
    values,
    *,
    prefix: str,
    unit: str | None,
    quantiles: Iterable[str],
    outlier_rule: str,
    include_counts: tuple[int, int, int, int] | None = None,
) -> tuple[list[Estimate], list[Diagnostic]]:
    import numpy as np
    from scipy import stats

    count = len(values)
    estimates: list[Estimate] = []
    diagnostics: list[Diagnostic] = []

    def add(name: str, value: float | int | None, result_unit: str | None = unit):
        estimates.append(_estimate(f"{prefix}{name}", value, result_unit))

    if include_counts is not None:
        observed, missing, excluded, distinct = include_counts
        add("count_observed", observed, None)
        add("count_missing", missing, None)
        add("count_excluded", excluded, None)
        add("count_distinct", distinct, None)
    else:
        add("count_observed", count, None)

    add("minimum", float(np.min(values)))
    add("maximum", float(np.max(values)))
    add("mean", float(np.mean(values)))
    add("median", float(np.median(values)))
    add("variance_population", float(np.var(values, ddof=0)))
    add("std_population", float(np.std(values, ddof=0)))
    if count > 1:
        add("variance_sample", float(np.var(values, ddof=1)))
        add("std_sample", float(np.std(values, ddof=1)))
    else:
        add("variance_sample", None)
        add("std_sample", None)
        diagnostics.append(
            Diagnostic(
                "STAT_SAMPLE_DISPERSION_UNDEFINED",
                "warning",
                "n=1",
                (
                    "Sample variance and standard deviation require at least "
                    "two observations."
                ),
            )
        )

    requested = tuple((text, float(text)) for text in quantiles)
    quantile_values = {
        text: float(value)
        for (text, _), value in zip(
            requested,
            np.quantile(values, [number for _, number in requested]),
            strict=True,
        )
    }
    for text, _ in requested:
        add(f"quantile_{text}", quantile_values[text])
    q1, q3 = np.quantile(values, [0.25, 0.75])
    iqr = float(q3 - q1)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    add("iqr", iqr)
    add("mad", mad)

    constant = bool(np.all(values == values[0]))
    if constant:
        add("skewness", None, None)
        add("kurtosis", None, None)
        diagnostics.append(
            Diagnostic(
                "STAT_SHAPE_UNDEFINED",
                "warning",
                "constant sample",
                "Skewness and kurtosis are undefined for a constant sample.",
            )
        )
    else:
        add("skewness", float(stats.skew(values, bias=False)), None)
        add("kurtosis", float(stats.kurtosis(values, bias=False)), None)

    if outlier_rule == "none":
        add("outlier_count", None, None)
        diagnostics.append(
            Diagnostic(
                "STAT_OUTLIER_RULE_NONE",
                "not_applicable",
                None,
                "No robust outlier classification was requested.",
            )
        )
    elif outlier_rule == "iqr":
        low = float(q1 - _IQR_MULTIPLIER * iqr)
        high = float(q3 + _IQR_MULTIPLIER * iqr)
        add(
            "outlier_count",
            int(np.count_nonzero((values < low) | (values > high))),
            None,
        )
    elif mad == 0:
        add("outlier_count", None, None)
        diagnostics.append(
            Diagnostic(
                "STAT_MAD_ZERO",
                "warning",
                "0",
                "MAD is zero, so robust z-score outlier classification is undefined.",
            )
        )
    else:
        robust_z = _ROBUST_Z_SCALE * (values - median) / mad
        add(
            "outlier_count",
            int(np.count_nonzero(np.abs(robust_z) > _MAD_THRESHOLD)),
            None,
        )
    return estimates, diagnostics


def run_describe(context: MethodContext) -> MethodResult:
    """Compute finite univariate and privacy-safe grouped summaries."""

    sample = numeric_role(context, "response")
    values = sample.values
    unit = unit_for_role(context, "response")
    parameters = context.spec.method.parameters
    quantiles = tuple(str(item) for item in parameters.get("quantiles", ("0.5",)))
    outlier_rule = str(parameters.get("outlier_rule", "none"))
    missing = sample.total_count - sample.retained_count
    estimates, diagnostics = _summary(
        values,
        prefix="",
        unit=unit,
        quantiles=quantiles,
        outlier_rule=outlier_rule,
        include_counts=(
            sample.retained_count,
            missing,
            sample.excluded_count,
            len(set(values.tolist())),
        ),
    )

    if "group" in context.spec.roles:
        grouped = safe_groups(context)
        by_row = dict(zip(sample.row_indices, values.tolist(), strict=True))
        privacy_floor = int(context.spec.pii["minimum_group_count"])
        suppressed = grouped.suppressed_count
        for group in grouped.groups:
            retained = [by_row[index] for index in group.row_indices if index in by_row]
            if len(retained) < privacy_floor:
                suppressed += 1
                continue
            group_estimates, group_diagnostics = _summary(
                finite_array(retained, "response"),
                prefix=f"group[{group.label}].",
                unit=unit,
                quantiles=quantiles,
                outlier_rule=outlier_rule,
            )
            estimates.extend(group_estimates)
            diagnostics.extend(group_diagnostics)
        if suppressed:
            diagnostics.append(
                Diagnostic(
                    "STAT_GROUPS_SUPPRESSED",
                    "warning",
                    str(suppressed),
                    "Groups below the approved minimum count were suppressed.",
                )
            )
        if grouped.missing_count:
            diagnostics.append(
                Diagnostic(
                    "STAT_GROUP_LABELS_MISSING",
                    "warning",
                    str(grouped.missing_count),
                    (
                        "Rows with missing group labels were excluded from "
                        "group summaries."
                    ),
                )
            )

    return MethodResult(
        estimates=tuple(estimates),
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Extreme values are observations for review, not proof of data error.",
        ),
    )
