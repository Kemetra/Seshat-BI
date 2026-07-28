"""Oracle and refusal tests for governed associational regression."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from types import MappingProxyType

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("statsmodels")

import numpy as np  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from seshat.statistical.contracts import (  # noqa: E402
    AnalysisSpec,
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
    MethodSpec,
)
from seshat.statistical.methods.regression import run_regress  # noqa: E402
from seshat.statistical.policy import PolicyContext  # noqa: E402
from seshat.statistical.providers.base import (  # noqa: E402
    ProviderProvenance,
    RectangularData,
)

pytestmark = pytest.mark.statistics


def _context(
    response,
    predictor,
    *,
    family="ols",
    covariance="HC3",
    question="Are the approved measures associated?",
    missing_policy="complete_case",
) -> MethodContext:
    rows = tuple(zip(response, predictor, strict=True))
    spec = AnalysisSpec(
        "1.0",
        "regression_example",
        1,
        "sample",
        question,
        "weekly",
        "Example Analyst",
        PurePosixPath("mappings/sample/readiness-status.yaml"),
        (PurePosixPath("mappings/sample/metrics/ApprovedMetric.yaml"),),
        MappingProxyType({"kind": "local_csv", "dataset_id": "sample"}),
        MappingProxyType({"grain": "one row", "inclusion": (), "exclusion": ()}),
        MappingProxyType(
            {
                "response": ColumnBinding("response", "number"),
                "predictor": ColumnBinding("predictor", "number"),
            }
        ),
        MethodSpec(
            "regress",
            "1.0",
            MappingProxyType(
                {
                    "family": family,
                    "covariance": covariance,
                    "confidence_level": "0.95",
                }
            ),
        ),
        missing_policy,
        MappingProxyType({"observations": 3, "groups": 1, "seasonal_cycles": 0}),
        1729,
        MappingProxyType(
            {
                "classification": "none",
                "approval_evidence": (),
                "minimum_group_count": 1,
            }
        ),
        MappingProxyType({}),
    )
    data = RectangularData(
        ("response", "predictor"),
        rows,
        len(rows),
        0,
        (),
        ProviderProvenance("local_csv", "local_csv:test", "a" * 64, None, None),
    )
    policy = PolicyContext(
        "sample",
        Path("readiness-status.yaml"),
        "1",
        (),
        frozenset({"gold.sample"}),
        MappingProxyType({"gold.sample": frozenset({"response", "predictor"})}),
    )
    return MethodContext(spec, policy, data)


def _estimate(result, name: str) -> float:
    return float(next(item.value for item in result.estimates if item.name == name))


def test_ols_matches_statsmodels_hc3_and_emits_diagnostics() -> None:
    x = np.arange(1.0, 11.0)
    y = np.array([2.1, 4.2, 5.7, 8.5, 9.8, 12.4, 13.7, 16.8, 17.5, 20.9])
    expected = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HC3")

    actual = run_regress(_context(y, x))

    assert _estimate(actual, "coefficient:predictor") == pytest.approx(
        expected.params[1]
    )
    assert _estimate(actual, "standard_error:predictor") == pytest.approx(
        expected.bse[1]
    )
    assert _estimate(actual, "r_squared") == pytest.approx(expected.rsquared)
    assert any(item.code == "STAT_REGRESSION_CONDITION" for item in actual.diagnostics)
    assert "do not establish causality" in actual.interpretation_cautions[0]


@pytest.mark.parametrize(
    ("family", "response", "family_object"),
    (
        (
            "logistic",
            [0, 0, 1, 0, 1, 1, 0, 1, 1, 1],
            sm.families.Binomial(),
        ),
        (
            "poisson",
            [0, 1, 1, 2, 1, 3, 2, 4, 3, 5],
            sm.families.Poisson(),
        ),
        (
            "negative_binomial",
            [0, 1, 0, 3, 1, 5, 2, 7, 4, 8],
            sm.families.NegativeBinomial(alpha=1.0),
        ),
    ),
)
def test_glm_families_match_statsmodels(family, response, family_object) -> None:
    x = np.arange(1.0, 11.0)
    expected = sm.GLM(
        np.asarray(response, dtype=float),
        sm.add_constant(x),
        family=family_object,
    ).fit(cov_type="HC3")

    actual = run_regress(_context(response, x, family=family))

    assert _estimate(actual, "coefficient:predictor") == pytest.approx(
        expected.params[1]
    )
    assert _estimate(actual, "standard_error:predictor") == pytest.approx(
        expected.bse[1]
    )
    assert _estimate(actual, "deviance") == pytest.approx(expected.deviance)
    assert any(item.code == "STAT_GLM_CONVERGENCE" for item in actual.diagnostics)


def test_complete_case_records_aligned_exclusions() -> None:
    result = run_regress(_context([1, 2, None, 4, 5, 6], [1, None, 3, 4, 5, 6]))
    assert _estimate(result, "sample_count") == 4
    assert _estimate(result, "excluded_count") == 2


@pytest.mark.parametrize(
    ("family", "response", "predictor", "code"),
    (
        ("logistic", [0, 1, 2, 1], [1, 2, 3, 4], "STAT_LOGISTIC_RESPONSE"),
        ("poisson", [0, 1, -1, 2], [1, 2, 3, 4], "STAT_COUNT_RESPONSE"),
        ("ols", [1, 2, 3, 4], [1, 1, 1, 1], "STAT_PREDICTOR_VARIANCE"),
        ("ols", [1, 2, 3], [1, 2, 3], "STAT_RESIDUAL_DF"),
    ),
)
def test_invalid_designs_are_withheld(family, response, predictor, code) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_regress(_context(response, predictor, family=family))
    assert exc_info.value.blockers[0].code == code


def test_causal_question_is_refused() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_regress(
            _context(
                [1, 2, 3, 5],
                [1, 2, 4, 6],
                question="What impact of predictor drives the response?",
            )
        )
    assert exc_info.value.blockers[0].code == "STAT_CAUSAL_LANGUAGE"


def test_perfect_logistic_separation_is_withheld() -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_regress(
            _context(
                [0, 0, 0, 1, 1, 1],
                [1, 2, 3, 4, 5, 6],
                family="logistic",
            )
        )
    assert exc_info.value.blockers[0].code == "STAT_MODEL_UNIDENTIFIED"
