"""Strict numerical preparation shared by every statistical method."""

from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.statistical.contracts import AnalysisWithheld
from seshat.statistical.methods.common import finite_array

pytestmark = pytest.mark.statistics


def test_finite_array_accepts_decimal_integer_float_and_text() -> None:
    values = finite_array((Decimal("1.25"), 2, 3.5, "4.75"), "response")
    assert values.tolist() == [1.25, 2.0, 3.5, 4.75]


@pytest.mark.parametrize("value", (True, False, "not-a-number", object()))
def test_finite_array_refuses_non_numeric_values(value: object) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        finite_array((value,), "response")
    assert exc_info.value.blockers[0].code == "STAT_NON_NUMERIC_INPUT"


def test_absent_privacy_floor_is_refused_not_defaulted_to_one() -> None:
    """A spec path without pii.minimum_group_count must not get floor=1 (no
    suppression) from safe_groups while describe crashes on the same spec."""
    from dataclasses import replace
    from types import MappingProxyType

    from seshat.statistical.contracts import ColumnBinding
    from seshat.statistical.methods.common import safe_groups

    from ._support import SpecSettings, method_context

    settings = SpecSettings(
        analysis_id="floor_example",
        question="Q?",
        method_id="describe",
        parameters={},
        roles={
            "response": ColumnBinding("value", "number"),
            "group": ColumnBinding("group", "category"),
        },
    )
    context = method_context(settings, ("value", "group"), [(1.0, "A")])
    context = replace(
        context,
        spec=replace(context.spec, pii=MappingProxyType({"classification": "none"})),
    )
    with pytest.raises(AnalysisWithheld) as exc_info:
        safe_groups(context)
    assert exc_info.value.blockers[0].code == "STAT_PRIVACY_FLOOR_INVALID"


@pytest.mark.parametrize("value", (float("nan"), float("inf"), "-Infinity", "NaN"))
def test_finite_array_refuses_non_finite_values(value: object) -> None:
    with pytest.raises(AnalysisWithheld) as exc_info:
        finite_array((value,), "response")
    assert exc_info.value.blockers[0].code == "STAT_NON_FINITE_INPUT"
