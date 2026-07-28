"""Governed associational regression with closed model-family dispatch."""

from __future__ import annotations

import math
import re
import warnings

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
from .common import finite_array, unit_for_role

_CAUSAL_LANGUAGE = re.compile(
    r"\b(?:causes?|caused|drives?|drove)\b|\bimpact\s+of\b",
    re.IGNORECASE,
)

_COUNT_FAMILIES = frozenset({"poisson", "negative_binomial"})

_COEFFICIENT_LABELS = ("intercept", "predictor")


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return withheld(code, message, recovery)


def _unidentified(message: str, recovery: str) -> AnalysisWithheld:
    return _withheld("STAT_MODEL_UNIDENTIFIED", message, recovery)


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _role_indexes(context: MethodContext) -> tuple[int, ...]:
    indexes: list[int] = []
    for role in ("response", "predictor"):
        binding = context.spec.roles.get(role)
        require(
            binding is not None,
            "STAT_METHOD_ROLE_MISSING",
            f"The governed {role} role is not bound.",
            "Bind both response and predictor roles.",
        )
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
    """Split the rows into complete response/predictor pairs and an excluded count."""

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
        "Regression input contains incomplete response/predictor rows.",
        "Resolve missing values or approve complete-case exclusion.",
    )
    return pairs, excluded


def _aligned_data(context: MethodContext):
    pairs, excluded = _complete_pairs(context, _role_indexes(context))
    y = finite_array([pair[0] for pair in pairs], "response")
    x = finite_array([pair[1] for pair in pairs], "predictor")
    minimum = max(3, context.spec.minimum_data.get("observations", 1))
    require(
        len(y) >= minimum,
        "STAT_MINIMUM_DATA",
        f"Regression retains {len(y)} rows; the governed minimum is {minimum}.",
        "Provide more complete approved observations.",
    )
    return y, x, excluded


def _finite_results(result) -> None:
    values = (
        *result.params,
        *result.bse,
        *result.pvalues,
        *result.conf_int().ravel(),
        *result.fittedvalues,
    )
    require(
        all(math.isfinite(float(value)) for value in values),
        "STAT_MODEL_NON_FINITE",
        "The fitted model produced non-finite evidence.",
        "Revise the declared design or provide a more informative sample.",
    )


def _ols_diagnostics(result, design) -> tuple[Diagnostic, ...]:
    import numpy as np
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.stattools import jarque_bera

    residuals = result.resid
    jb_stat, jb_p, _, _ = jarque_bera(residuals)
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, design)
    cooks = result.get_influence().cooks_distance[0]
    max_cook = float(np.max(cooks))
    threshold = 4.0 / len(residuals)
    condition = float(np.linalg.cond(design))
    vif = float(variance_inflation_factor(design, 1))
    return (
        Diagnostic(
            "STAT_RESIDUAL_NORMALITY",
            "holds" if jb_p >= 0.05 else "warning",
            decimal_text(jb_p),
            "Jarque-Bera residual-normality p-value.",
        ),
        Diagnostic(
            "STAT_HETEROSKEDASTICITY",
            "holds" if bp_p >= 0.05 else "warning",
            decimal_text(bp_p),
            "Breusch-Pagan heteroskedasticity p-value.",
        ),
        Diagnostic(
            "STAT_INFLUENCE",
            "warning" if max_cook > threshold else "holds",
            decimal_text(max_cook),
            "Maximum Cook's distance; the reference threshold is 4/n.",
        ),
        Diagnostic(
            "STAT_REGRESSION_CONDITION",
            "warning" if condition > 30 else "holds",
            decimal_text(condition),
            "Design-matrix condition number.",
        ),
        Diagnostic(
            "STAT_REGRESSION_VIF",
            "warning" if vif > 5 else "holds",
            decimal_text(vif),
            "Predictor variance inflation factor.",
        ),
    )


def _glm_diagnostics(result, family: str) -> tuple[Diagnostic, ...]:
    dispersion = float(result.pearson_chi2 / result.df_resid)
    over_dispersed = family in _COUNT_FAMILIES and dispersion > 2
    return (
        Diagnostic(
            "STAT_GLM_CONVERGENCE",
            "holds" if result.converged else "violated",
            str(bool(result.converged)).lower(),
            "Iteratively reweighted fitting convergence state.",
        ),
        Diagnostic(
            "STAT_GLM_DEVIANCE",
            "holds",
            decimal_text(result.deviance),
            "Model deviance is recorded as an observed diagnostic.",
        ),
        Diagnostic(
            "STAT_GLM_DISPERSION",
            "warning" if over_dispersed else "holds",
            decimal_text(dispersion),
            "Pearson chi-square divided by residual degrees of freedom.",
        ),
    )


def _design(y, x):
    """Build the intercept design matrix once every identifiability guard holds."""

    import numpy as np
    import statsmodels.api as sm

    require(
        float(np.ptp(x)) > np.finfo(float).eps,
        "STAT_PREDICTOR_VARIANCE",
        "The predictor has zero or near-zero variance.",
        "Provide an informative approved predictor.",
    )
    design = sm.add_constant(x, has_constant="add")
    require(
        len(y) - design.shape[1] > 1,
        "STAT_RESIDUAL_DF",
        "Too few residual degrees of freedom remain for governed inference.",
        "Provide more observations relative to the declared predictors.",
    )
    require(
        np.linalg.matrix_rank(design) >= design.shape[1],
        "STAT_SINGULAR_DESIGN",
        "The regression design matrix is singular.",
        "Remove redundant approved predictors or repair the sample.",
    )
    return design


def _assert_family_response(family: str, y) -> None:
    """Hold the response shape each declared family requires."""

    import numpy as np

    require(
        family != "logistic" or set(np.unique(y)).issubset({0.0, 1.0}),
        "STAT_LOGISTIC_RESPONSE",
        "Logistic regression requires a binary zero/one response.",
        "Bind an approved binary response or select another family.",
    )
    require(
        family not in _COUNT_FAMILIES or not np.any(y < 0),
        "STAT_COUNT_RESPONSE",
        "Count regression requires a non-negative response.",
        "Bind an approved non-negative count response.",
    )


def _raw_fit(family: str, fit_options: dict[str, object], y, design):
    """Dispatch to exactly the declared family's estimator."""

    import statsmodels.api as sm

    if family == "ols":
        return sm.OLS(y, design).fit(**fit_options)
    families = {
        "logistic": sm.families.Binomial(),
        "poisson": sm.families.Poisson(),
        "negative_binomial": sm.families.NegativeBinomial(alpha=1.0),
    }
    return sm.GLM(y, design, family=families[family]).fit(**fit_options)


def _assert_identified(result, caught) -> None:
    """Refuse a fit that separated perfectly or never converged."""

    from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

    require(
        not any(issubclass(item.category, PerfectSeparationWarning) for item in caught),
        "STAT_MODEL_UNIDENTIFIED",
        "The logistic response is perfectly separated by the predictor.",
        "Provide overlapping observations or revise the approved design.",
    )
    require(
        getattr(result, "converged", True),
        "STAT_MODEL_UNIDENTIFIED",
        "The declared regression model did not converge.",
        "Review the family, sample, and approved model design.",
    )


def _fitted_model(family: str, covariance: str, y, design):
    """Fit exactly the declared family; never search for a better one."""

    import numpy as np

    fit_options = {} if covariance == "classical" else {"cov_type": covariance}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = _raw_fit(family, fit_options, y, design)
    except (KeyError, ValueError, np.linalg.LinAlgError) as exc:
        raise _unidentified(
            "The declared regression model could not be identified.",
            "Provide a non-degenerate sample appropriate to the declared family.",
        ) from exc
    _assert_identified(result, caught)
    _finite_results(result)
    return result


def _coefficient_evidence(result, family: str, level: float, unit: str | None):
    """Report one estimate, interval, and test per declared coefficient."""

    confidence = result.conf_int(alpha=1.0 - level)
    estimates: list[Estimate] = []
    intervals: list[Interval] = []
    tests: list[TestStatistic] = []
    statistic = "t" if family == "ols" else "z"
    for index, label in enumerate(_COEFFICIENT_LABELS):
        estimates.extend(
            (
                Estimate(
                    f"coefficient:{label}",
                    decimal_text(result.params[index]),
                    unit,
                ),
                Estimate(
                    f"standard_error:{label}",
                    decimal_text(result.bse[index]),
                    unit,
                ),
            )
        )
        intervals.append(
            Interval(
                f"coefficient:{label}",
                decimal_text(confidence[index, 0]),
                decimal_text(confidence[index, 1]),
                decimal_text(level),
                "wald",
            )
        )
        tests.append(
            TestStatistic(
                f"coefficient:{label}",
                decimal_text(result.tvalues[index]),
                decimal_text(result.pvalues[index]),
                decimal_text(result.pvalues[index]),
                "two-sided",
                statistic,
            )
        )
    return estimates, intervals, tests


def _fit_evidence(result, family: str, design):
    """Report the family-specific fit estimates and their diagnostics."""

    if family == "ols":
        estimates = [Estimate("r_squared", decimal_text(result.rsquared), None)]
        return estimates, _ols_diagnostics(result, design)
    estimates = [
        Estimate("deviance", decimal_text(result.deviance), None),
        Estimate("pearson_chi2", decimal_text(result.pearson_chi2), None),
    ]
    return estimates, _glm_diagnostics(result, family)


def run_regress(context: MethodContext) -> MethodResult:
    """Fit one explicitly declared associational model without model search."""

    require(
        not _CAUSAL_LANGUAGE.search(context.spec.question),
        "STAT_CAUSAL_LANGUAGE",
        "The analysis question requests a causal interpretation.",
        "Rewrite and approve the question as an associational analysis.",
    )
    y, x, excluded = _aligned_data(context)
    design = _design(y, x)
    parameters = context.spec.method.parameters
    family = str(parameters["family"])
    level = float(parameters["confidence_level"])
    _assert_family_response(family, y)
    result = _fitted_model(family, str(parameters["covariance"]), y, design)

    unit = unit_for_role(context, "response") if family == "ols" else None
    estimates, intervals, tests = _coefficient_evidence(result, family, level, unit)
    estimates.extend(
        (
            Estimate("sample_count", str(len(y)), None),
            Estimate("excluded_count", str(excluded), None),
            Estimate("aic", decimal_text(result.aic), None),
        )
    )
    fit_estimates, diagnostics = _fit_evidence(result, family, design)
    estimates.extend(fit_estimates)
    if excluded:
        diagnostics += (
            Diagnostic(
                "STAT_MISSING_ROWS_EXCLUDED",
                "warning",
                str(excluded),
                "Incomplete response/predictor rows were excluded.",
            ),
        )
    return MethodResult(
        estimates=tuple(estimates),
        intervals=tuple(intervals),
        tests=tuple(tests),
        diagnostics=diagnostics,
        interpretation_cautions=(
            "Associational model only; coefficients do not establish causality.",
        ),
    )
