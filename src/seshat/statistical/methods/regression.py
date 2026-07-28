"""Governed associational regression with closed model-family dispatch."""

from __future__ import annotations

import math
import re
import warnings

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
from .common import finite_array, unit_for_role

_CAUSAL_LANGUAGE = re.compile(
    r"\b(?:causes?|caused|drives?|drove)\b|\bimpact\s+of\b",
    re.IGNORECASE,
)


def _withheld(code: str, message: str, recovery: str) -> AnalysisWithheld:
    return AnalysisWithheld((Blocker(code, message, recovery),))


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _aligned_data(context: MethodContext):
    indexes: list[int] = []
    for role in ("response", "predictor"):
        binding = context.spec.roles.get(role)
        if binding is None:
            raise _withheld(
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
    response: list[object] = []
    predictor: list[object] = []
    excluded = 0
    for row in context.data.rows:
        left, right = row[indexes[0]], row[indexes[1]]
        if _missing(left) or _missing(right):
            excluded += 1
            continue
        response.append(left)
        predictor.append(right)
    if excluded and context.spec.missing_policy == "fail":
        raise _withheld(
            "STAT_MISSING_DATA",
            "Regression input contains incomplete response/predictor rows.",
            "Resolve missing values or approve complete-case exclusion.",
        )
    y = finite_array(response, "response")
    x = finite_array(predictor, "predictor")
    minimum = max(3, context.spec.minimum_data.get("observations", 1))
    if len(y) < minimum:
        raise _withheld(
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
    if not all(math.isfinite(float(value)) for value in values):
        raise _withheld(
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
            (
                "warning"
                if family in {"poisson", "negative_binomial"} and dispersion > 2
                else "holds"
            ),
            decimal_text(dispersion),
            "Pearson chi-square divided by residual degrees of freedom.",
        ),
    )


def run_regress(context: MethodContext) -> MethodResult:
    """Fit one explicitly declared associational model without model search."""

    import numpy as np
    import statsmodels.api as sm
    from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

    if _CAUSAL_LANGUAGE.search(context.spec.question):
        raise _withheld(
            "STAT_CAUSAL_LANGUAGE",
            "The analysis question requests a causal interpretation.",
            "Rewrite and approve the question as an associational analysis.",
        )
    y, x, excluded = _aligned_data(context)
    if float(np.ptp(x)) <= np.finfo(float).eps:
        raise _withheld(
            "STAT_PREDICTOR_VARIANCE",
            "The predictor has zero or near-zero variance.",
            "Provide an informative approved predictor.",
        )
    design = sm.add_constant(x, has_constant="add")
    if len(y) - design.shape[1] <= 1:
        raise _withheld(
            "STAT_RESIDUAL_DF",
            "Too few residual degrees of freedom remain for governed inference.",
            "Provide more observations relative to the declared predictors.",
        )
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise _withheld(
            "STAT_SINGULAR_DESIGN",
            "The regression design matrix is singular.",
            "Remove redundant approved predictors or repair the sample.",
        )

    parameters = context.spec.method.parameters
    family = str(parameters["family"])
    covariance = str(parameters["covariance"])
    level = float(parameters["confidence_level"])
    if family == "logistic" and not set(np.unique(y)).issubset({0.0, 1.0}):
        raise _withheld(
            "STAT_LOGISTIC_RESPONSE",
            "Logistic regression requires a binary zero/one response.",
            "Bind an approved binary response or select another family.",
        )
    if family in {"poisson", "negative_binomial"} and np.any(y < 0):
        raise _withheld(
            "STAT_COUNT_RESPONSE",
            "Count regression requires a non-negative response.",
            "Bind an approved non-negative count response.",
        )

    fit_options = {} if covariance == "classical" else {"cov_type": covariance}
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if family == "ols":
                result = sm.OLS(y, design).fit(**fit_options)
            else:
                families = {
                    "logistic": sm.families.Binomial(),
                    "poisson": sm.families.Poisson(),
                    "negative_binomial": sm.families.NegativeBinomial(alpha=1.0),
                }
                result = sm.GLM(y, design, family=families[family]).fit(**fit_options)
    except (KeyError, ValueError, np.linalg.LinAlgError) as exc:
        raise _withheld(
            "STAT_MODEL_UNIDENTIFIED",
            "The declared regression model could not be identified.",
            "Provide a non-degenerate sample appropriate to the declared family.",
        ) from exc
    if any(issubclass(item.category, PerfectSeparationWarning) for item in caught):
        raise _withheld(
            "STAT_MODEL_UNIDENTIFIED",
            "The logistic response is perfectly separated by the predictor.",
            "Provide overlapping observations or revise the approved design.",
        )
    if not getattr(result, "converged", True):
        raise _withheld(
            "STAT_MODEL_UNIDENTIFIED",
            "The declared regression model did not converge.",
            "Review the family, sample, and approved model design.",
        )
    _finite_results(result)

    labels = ("intercept", "predictor")
    alpha = 1.0 - level
    confidence = result.conf_int(alpha=alpha)
    estimates: list[Estimate] = []
    intervals: list[Interval] = []
    tests: list[TestStatistic] = []
    response_unit = unit_for_role(context, "response")
    for index, label in enumerate(labels):
        estimates.extend(
            (
                Estimate(
                    f"coefficient:{label}",
                    decimal_text(result.params[index]),
                    response_unit if family == "ols" else None,
                ),
                Estimate(
                    f"standard_error:{label}",
                    decimal_text(result.bse[index]),
                    response_unit if family == "ols" else None,
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
                "t" if family == "ols" else "z",
            )
        )
    estimates.extend(
        (
            Estimate("sample_count", str(len(y)), None),
            Estimate("excluded_count", str(excluded), None),
            Estimate("aic", decimal_text(result.aic), None),
        )
    )
    if family == "ols":
        estimates.append(Estimate("r_squared", decimal_text(result.rsquared), None))
        diagnostics = _ols_diagnostics(result, design)
    else:
        estimates.extend(
            (
                Estimate("deviance", decimal_text(result.deviance), None),
                Estimate("pearson_chi2", decimal_text(result.pearson_chi2), None),
            )
        )
        diagnostics = _glm_diagnostics(result, family)
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
