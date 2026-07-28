"""Governed descriptive statistics with robust outlier summaries."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..contracts import Diagnostic, Estimate, MethodContext, MethodResult
from ..evidence import decimal_text
from .common import (
    NumericSample,
    finite_array,
    numeric_role,
    safe_groups,
    unit_for_role,
)

_ROBUST_Z_SCALE = 0.6744897501960817
_MAD_THRESHOLD = 3.5
_IQR_MULTIPLIER = 1.5


@dataclass(frozen=True, slots=True)
class _Style:
    """How one summary block is labelled and which robust rules it applies."""

    prefix: str
    unit: str | None
    quantiles: tuple[str, ...]
    outlier_rule: str


@dataclass(frozen=True, slots=True)
class _Counts:
    observed: int
    missing: int
    excluded: int
    distinct: int


@dataclass(frozen=True, slots=True)
class _Spread:
    """The robust spread the quantile block measures and outliers reuse."""

    q1: float
    q3: float
    iqr: float
    median: float
    mad: float


def _value(value: float | int) -> str | None:
    return decimal_text(value) if math.isfinite(float(value)) else None


def _estimate(name: str, value: float | int | None, unit: str | None) -> Estimate:
    return Estimate(name, None if value is None else _value(value), unit)


def _named(
    style: _Style, name: str, value: float | int | None, unit_scope: bool = True
):
    return _estimate(f"{style.prefix}{name}", value, style.unit if unit_scope else None)


def _count_estimates(style: _Style, counts: _Counts | None, observed: int):
    if counts is None:
        return [_named(style, "count_observed", observed, False)]
    return [
        _named(style, "count_observed", counts.observed, False),
        _named(style, "count_missing", counts.missing, False),
        _named(style, "count_excluded", counts.excluded, False),
        _named(style, "count_distinct", counts.distinct, False),
    ]


def _location_estimates(values, style: _Style) -> list[Estimate]:
    import numpy as np

    return [
        _named(style, "minimum", float(np.min(values))),
        _named(style, "maximum", float(np.max(values))),
        _named(style, "mean", float(np.mean(values))),
        _named(style, "median", float(np.median(values))),
        _named(style, "variance_population", float(np.var(values, ddof=0))),
        _named(style, "std_population", float(np.std(values, ddof=0))),
    ]


def _sample_dispersion(values, style: _Style):
    """Sample variance and deviation, which one observation cannot support."""

    import numpy as np

    if len(values) > 1:
        estimates = [
            _named(style, "variance_sample", float(np.var(values, ddof=1))),
            _named(style, "std_sample", float(np.std(values, ddof=1))),
        ]
        return estimates, []
    undefined = [
        _named(style, "variance_sample", None),
        _named(style, "std_sample", None),
    ]
    warning = Diagnostic(
        "STAT_SAMPLE_DISPERSION_UNDEFINED",
        "warning",
        "n=1",
        "Sample variance and standard deviation require at least two observations.",
    )
    return undefined, [warning]


def _quantile_estimates(values, style: _Style):
    import numpy as np

    requested = tuple((text, float(text)) for text in style.quantiles)
    measured = np.quantile(values, [number for _, number in requested])
    estimates = [
        _named(style, f"quantile_{text}", float(value))
        for (text, _), value in zip(requested, measured, strict=True)
    ]
    q1, q3 = np.quantile(values, [0.25, 0.75])
    median = float(np.median(values))
    spread = _Spread(
        q1=float(q1),
        q3=float(q3),
        iqr=float(q3 - q1),
        median=median,
        mad=float(np.median(np.abs(values - median))),
    )
    estimates.append(_named(style, "iqr", spread.iqr))
    estimates.append(_named(style, "mad", spread.mad))
    return estimates, spread


def _shape_estimates(values, style: _Style):
    """Skewness and kurtosis, which a constant sample leaves undefined."""

    import numpy as np
    from scipy import stats

    if bool(np.all(values == values[0])):
        undefined = [
            _named(style, "skewness", None, False),
            _named(style, "kurtosis", None, False),
        ]
        warning = Diagnostic(
            "STAT_SHAPE_UNDEFINED",
            "warning",
            "constant sample",
            "Skewness and kurtosis are undefined for a constant sample.",
        )
        return undefined, [warning]
    estimates = [
        _named(style, "skewness", float(stats.skew(values, bias=False)), False),
        _named(style, "kurtosis", float(stats.kurtosis(values, bias=False)), False),
    ]
    return estimates, []


def _iqr_outliers(values, style: _Style, spread: _Spread) -> list[Estimate]:
    import numpy as np

    low = spread.q1 - _IQR_MULTIPLIER * spread.iqr
    high = spread.q3 + _IQR_MULTIPLIER * spread.iqr
    outliers = int(np.count_nonzero((values < low) | (values > high)))
    return [_named(style, "outlier_count", outliers, False)]


def _robust_z_outliers(values, style: _Style, spread: _Spread):
    import numpy as np

    if spread.mad == 0:
        warning = Diagnostic(
            "STAT_MAD_ZERO",
            "warning",
            "0",
            "MAD is zero, so robust z-score outlier classification is undefined.",
        )
        return [_named(style, "outlier_count", None, False)], [warning]
    robust_z = _ROBUST_Z_SCALE * (values - spread.median) / spread.mad
    outliers = int(np.count_nonzero(np.abs(robust_z) > _MAD_THRESHOLD))
    return [_named(style, "outlier_count", outliers, False)], []


def _outlier_estimates(values, style: _Style, spread: _Spread):
    if style.outlier_rule == "none":
        declined = Diagnostic(
            "STAT_OUTLIER_RULE_NONE",
            "not_applicable",
            None,
            "No robust outlier classification was requested.",
        )
        return [_named(style, "outlier_count", None, False)], [declined]
    if style.outlier_rule == "iqr":
        return _iqr_outliers(values, style, spread), []
    return _robust_z_outliers(values, style, spread)


def _summary(
    values, style: _Style, counts: _Counts | None = None
) -> tuple[list[Estimate], list[Diagnostic]]:
    """Report one labelled summary block in its fixed evidence order."""

    estimates = _count_estimates(style, counts, len(values))
    estimates.extend(_location_estimates(values, style))
    dispersion, diagnostics = _sample_dispersion(values, style)
    estimates.extend(dispersion)
    quantiles, spread = _quantile_estimates(values, style)
    estimates.extend(quantiles)
    shape, shape_diagnostics = _shape_estimates(values, style)
    estimates.extend(shape)
    diagnostics.extend(shape_diagnostics)
    outliers, outlier_diagnostics = _outlier_estimates(values, style, spread)
    estimates.extend(outliers)
    diagnostics.extend(outlier_diagnostics)
    return estimates, diagnostics


def _suppression_diagnostics(suppressed: int, missing_labels: int) -> list[Diagnostic]:
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
    if missing_labels:
        diagnostics.append(
            Diagnostic(
                "STAT_GROUP_LABELS_MISSING",
                "warning",
                str(missing_labels),
                "Rows with missing group labels were excluded from group summaries.",
            )
        )
    return diagnostics


def _grouped_summaries(context: MethodContext, sample: NumericSample, style: _Style):
    """Summarize each group that still meets the approved privacy floor."""

    grouped = safe_groups(context)
    by_row = dict(zip(sample.row_indices, sample.values.tolist(), strict=True))
    privacy_floor = int(context.spec.pii["minimum_group_count"])
    suppressed = grouped.suppressed_count
    estimates: list[Estimate] = []
    diagnostics: list[Diagnostic] = []
    for group in grouped.groups:
        retained = [by_row[index] for index in group.row_indices if index in by_row]
        if len(retained) < privacy_floor:
            suppressed += 1
            continue
        group_style = _Style(
            prefix=f"group[{group.label}].",
            unit=style.unit,
            quantiles=style.quantiles,
            outlier_rule=style.outlier_rule,
        )
        group_estimates, group_diagnostics = _summary(
            finite_array(retained, "response"), group_style
        )
        estimates.extend(group_estimates)
        diagnostics.extend(group_diagnostics)
    diagnostics.extend(_suppression_diagnostics(suppressed, grouped.missing_count))
    return estimates, diagnostics


def run_describe(context: MethodContext) -> MethodResult:
    """Compute finite univariate and privacy-safe grouped summaries."""

    sample = numeric_role(context, "response")
    parameters = context.spec.method.parameters
    style = _Style(
        prefix="",
        unit=unit_for_role(context, "response"),
        quantiles=tuple(str(item) for item in parameters.get("quantiles", ("0.5",))),
        outlier_rule=str(parameters.get("outlier_rule", "none")),
    )
    counts = _Counts(
        observed=sample.retained_count,
        missing=sample.total_count - sample.retained_count,
        excluded=sample.excluded_count,
        distinct=len(set(sample.values.tolist())),
    )
    estimates, diagnostics = _summary(sample.values, style, counts)
    if "group" in context.spec.roles:
        group_estimates, group_diagnostics = _grouped_summaries(context, sample, style)
        estimates.extend(group_estimates)
        diagnostics.extend(group_diagnostics)
    return MethodResult(
        estimates=tuple(estimates),
        diagnostics=tuple(diagnostics),
        interpretation_cautions=(
            "Extreme values are observations for review, not proof of data error.",
        ),
    )
