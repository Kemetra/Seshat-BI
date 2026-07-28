"""Oracle and safeguard tests for governed group comparisons."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

# The numerical stack is an optional extra; collection-skip without it so the
# base `.[dev]` suite never fails on an import it is not meant to satisfy.
pytest.importorskip("numpy")
pytest.importorskip("scipy")

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from seshat.statistical.contracts import (  # noqa: E402
    AnalysisWithheld,
    ColumnBinding,
    MethodContext,
)
from seshat.statistical.methods.groups import run_compare_groups  # noqa: E402

from ._support import SpecSettings, method_context  # noqa: E402

pytestmark = pytest.mark.statistics


@dataclass(frozen=True, slots=True)
class _Options:
    """The knobs a group-comparison test varies on the governed specification."""

    identifiers: dict[str, list[str]] | None = None
    correction: str = "none"
    post_hoc_pairs: tuple[tuple[str, str], ...] = ()
    group_order: tuple[str, ...] | None = None
    privacy_floor: int = 2


def _group_rows(grouped: dict[str, list[float]], identifiers) -> list[tuple]:
    rows: list[tuple] = []
    for label, values in grouped.items():
        for index, value in enumerate(values):
            row = [value, label]
            if identifiers is not None:
                row.append(identifiers[label][index])
            rows.append(tuple(row))
    return rows


def _context(
    grouped: dict[str, list[float]], test: str, **overrides: object
) -> MethodContext:
    options = _Options(**overrides)  # type: ignore[arg-type]
    paired = options.identifiers is not None
    columns = ("value", "group", "identifier") if paired else ("value", "group")
    roles = {
        "response": ColumnBinding("value", "number"),
        "group": ColumnBinding("group", "category"),
    }
    if paired:
        roles["identifier"] = ColumnBinding("identifier", "identifier")
    parameters: dict[str, object] = {
        "test": test,
        "alternative": "two-sided",
        "confidence_level": "0.95",
        "correction": options.correction,
        "group_order": options.group_order or tuple(grouped),
    }
    if options.post_hoc_pairs:
        parameters["post_hoc_pairs"] = options.post_hoc_pairs
    settings = SpecSettings(
        analysis_id="groups_example",
        question="Do approved groups differ?",
        method_id="compare_groups",
        parameters=parameters,
        roles=roles,
        minimum_data={"observations": 2, "groups": 2, "seasonal_cycles": 0},
        privacy_floor=options.privacy_floor,
    )
    return method_context(settings, columns, _group_rows(grouped, options.identifiers))


def _test(result, name: str):
    return next(item for item in result.tests if item.name == name)


def _effect(result, name: str) -> float:
    return float(next(item.value for item in result.effect_sizes if item.name == name))


@pytest.mark.parametrize("selected", ("welch_t", "mann_whitney"))
def test_independent_two_group_tests_match_scipy(selected: str) -> None:
    left = np.array([1.0, 2.0, 4.0, 5.0])
    right = np.array([3.0, 6.0, 7.0, 10.0])
    result = run_compare_groups(
        _context({"A": left.tolist(), "B": right.tolist()}, selected)
    )
    expected = (
        stats.ttest_ind(left, right, equal_var=False)
        if selected == "welch_t"
        else stats.mannwhitneyu(left, right)
    )
    observed = _test(result, selected)
    assert float(observed.statistic) == pytest.approx(expected.statistic)
    assert float(observed.p_value) == pytest.approx(expected.pvalue)
    assert observed.adjusted_p_value == observed.p_value
    assert result.effect_sizes[0].name in {"hedges_g", "rank_biserial"}
    if selected == "welch_t":
        assert result.intervals[0].name == "mean_difference"


@pytest.mark.parametrize("selected", ("paired_t", "wilcoxon"))
def test_paired_tests_match_scipy_and_preserve_identifier_alignment(
    selected: str,
) -> None:
    left = np.array([1.0, 2.0, 3.0, 5.0])
    right = np.array([8.0, 2.0, 4.0, 7.0])
    identifiers = {
        "A": ["p1", "p2", "p3", "p4"],
        "B": ["p4", "p1", "p2", "p3"],
    }
    aligned_right = np.array([2.0, 4.0, 7.0, 8.0])
    result = run_compare_groups(
        _context(
            {"A": left.tolist(), "B": right.tolist()},
            selected,
            identifiers=identifiers,
        )
    )
    expected = (
        stats.ttest_rel(left, aligned_right)
        if selected == "paired_t"
        else stats.wilcoxon(left, aligned_right)
    )
    observed = _test(result, selected)
    assert float(observed.statistic) == pytest.approx(expected.statistic)
    assert float(observed.p_value) == pytest.approx(expected.pvalue)


@pytest.mark.parametrize("selected", ("welch_anova", "kruskal_wallis"))
def test_omnibus_tests_match_scipy(selected: str) -> None:
    groups = {
        "A": [1.0, 2.0, 3.0, 4.0],
        "B": [3.0, 5.0, 7.0, 8.0],
        "C": [8.0, 9.0, 10.0, 12.0],
    }
    arrays = tuple(np.asarray(values) for values in groups.values())
    result = run_compare_groups(_context(groups, selected))
    expected = (
        stats.f_oneway(*arrays, equal_var=False)
        if selected == "welch_anova"
        else stats.kruskal(*arrays)
    )
    observed = _test(result, selected)
    assert float(observed.statistic) == pytest.approx(expected.statistic)
    assert float(observed.p_value) == pytest.approx(expected.pvalue)
    assert result.effect_sizes[0].name in {"omega_squared", "epsilon_squared"}


def test_reversing_declared_group_order_reverses_signed_effect_only() -> None:
    groups = {"A": [1.0, 2.0, 4.0, 5.0], "B": [3.0, 6.0, 7.0, 10.0]}
    forward = run_compare_groups(_context(groups, "welch_t", group_order=("A", "B")))
    reverse = run_compare_groups(_context(groups, "welch_t", group_order=("B", "A")))
    assert _effect(reverse, "hedges_g") == pytest.approx(-_effect(forward, "hedges_g"))
    assert _test(reverse, "welch_t").p_value == _test(forward, "welch_t").p_value


@pytest.mark.parametrize(
    "identifiers",
    (
        None,
        {"A": ["p1", "p1"], "B": ["p1", "p2"]},
        {"A": ["p1", "p2"], "B": ["p1", "p3"]},
    ),
)
def test_paired_methods_require_unique_matched_identifiers(identifiers) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_compare_groups(
            _context(
                {"A": [1.0, 2.0], "B": [2.0, 4.0]},
                "paired_t",
                identifiers=identifiers,
            )
        )
    assert exc_info.value.blockers[0].code in {
        "STAT_PAIR_IDENTIFIER_MISSING",
        "STAT_PAIRING_INVALID",
    }


def test_post_hoc_family_requires_correction_and_records_adjusted_values() -> None:
    groups = {
        "A": [1.0, 2.0, 3.0, 4.0],
        "B": [3.0, 5.0, 7.0, 8.0],
        "C": [8.0, 9.0, 10.0, 12.0],
    }
    pairs = (("A", "B"), ("A", "C"))
    with pytest.raises(AnalysisWithheld) as exc_info:
        run_compare_groups(_context(groups, "welch_anova", post_hoc_pairs=pairs))
    assert exc_info.value.blockers[0].code == "STAT_MULTIPLICITY_REQUIRED"

    result = run_compare_groups(
        _context(
            groups,
            "welch_anova",
            post_hoc_pairs=pairs,
            correction="holm",
        )
    )
    post_hoc = result.tests[1:]
    assert len(post_hoc) == 2
    assert all(item.adjusted_p_value is not None for item in post_hoc)


def test_suppressed_group_label_never_enters_results() -> None:
    result = run_compare_groups(
        _context(
            {"A": [1.0, 2.0, 3.0], "B": [4.0, 5.0, 6.0], "private": [100.0]},
            "welch_t",
            group_order=("A", "B"),
            privacy_floor=2,
        )
    )
    assert "private" not in repr(result)
    assert any(item.code == "STAT_GROUPS_SUPPRESSED" for item in result.diagnostics)
