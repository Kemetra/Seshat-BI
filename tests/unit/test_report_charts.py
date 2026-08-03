from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.report.charts import (
    CHART_HEIGHT,
    CHART_WIDTH,
    COORDINATE_PRECISION,
    build_chart,
)
from seshat.report.model import (
    CHART_BAR,
    CHART_LINE,
    DIRECTION_LTR,
    DIRECTION_RTL,
    ChartSpec,
    CitedFigure,
    ReportError,
)

pytestmark = pytest.mark.unit


def _figure(
    figure_id: str,
    value: str | None,
    label: str | None = None,
    unit_kind: str = "currency",
) -> CitedFigure:
    return CitedFigure(
        figure_id=figure_id,
        citation_id=f"TotalSales#{figure_id}",
        contract_id="TotalSales",
        metric="TotalSales",
        unit_kind=unit_kind,
        kind="series",
        section="headline",
        label=label,
        value=None if value is None else Decimal(value),
        renderings={"en": value or "[PENDING LIVE DATA]"},
    )


_SERIES = (
    _figure("a", "100", "Jan"),
    _figure("b", "250", "Feb"),
    _figure("c", "175", "Mar"),
)
_SPEC = ChartSpec(kind=CHART_BAR, figure_ids=("a", "b", "c"))


def test_bar_chart_produces_one_mark_per_figure() -> None:
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    assert view is not None
    assert len(view.marks) == 3


def test_canvas_travels_with_the_view() -> None:
    """A viewBox written literally in a template would drift from the geometry."""
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    assert Decimal(view.width) == CHART_WIDTH
    assert Decimal(view.height) == CHART_HEIGHT


def test_coordinates_are_exact_decimal_strings_never_floats() -> None:
    """A float coordinate would put binary floating point on a governed figure."""
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    for mark in view.marks:
        for coordinate in (mark.x, mark.y, mark.width, mark.height):
            assert isinstance(coordinate, str)
            parsed = Decimal(coordinate)  # exact, or this raises
            assert -parsed.as_tuple().exponent == COORDINATE_PRECISION


def test_view_returns_no_markup() -> None:
    """The module returns geometry; a Jinja macro writes the elements."""
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    rendered = repr(view)
    assert "<svg" not in rendered
    assert "<rect" not in rendered


def test_titles_are_codes_not_prose() -> None:
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    assert view.title_code == "chart_title.headline"
    assert view.description_code == "chart_description.bar"
    assert " " not in view.title_code


def test_customer_labels_are_carried_verbatim_and_not_localized() -> None:
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    labels = {label.value: label.localize for label in view.labels}
    assert labels == {"Jan": False, "Feb": False, "Mar": False}


def test_a_figure_without_a_label_falls_back_to_a_metric_code() -> None:
    series = (_figure("a", "100"), _figure("b", "250"))
    view = build_chart(
        ChartSpec(kind=CHART_BAR, figure_ids=("a", "b")),
        series,
        direction=DIRECTION_LTR,
    )
    assert all(label.value == "metric.TotalSales" for label in view.labels)
    assert all(label.localize for label in view.labels)


def test_a_governed_label_is_marked_for_localization() -> None:
    series = (_figure("a", "100", "prior_period"), _figure("b", "250", "budget"))
    view = build_chart(
        ChartSpec(kind=CHART_BAR, figure_ids=("a", "b")),
        series,
        direction=DIRECTION_LTR,
    )
    assert {label.value for label in view.labels} == {
        "label.prior_period",
        "label.budget",
    }
    assert all(label.localize for label in view.labels)


def test_rtl_mirrors_the_category_axis_only() -> None:
    ltr = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    rtl = build_chart(_SPEC, _SERIES, direction=DIRECTION_RTL)
    assert [mark.x for mark in ltr.marks] != [mark.x for mark in rtl.marks]
    # The value axis must not flip, or proportions read upside down.
    assert [mark.y for mark in ltr.marks] == [mark.y for mark in rtl.marks]


def test_a_missing_figure_refuses_the_chart() -> None:
    """Drawing from whatever was found would plot an unauthorized series."""
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a", "absent"))
    assert build_chart(spec, _SERIES, direction=DIRECTION_LTR) is None


def test_a_single_point_yields_no_chart() -> None:
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a",))
    assert build_chart(spec, _SERIES, direction=DIRECTION_LTR) is None


def test_a_pending_value_yields_no_chart() -> None:
    """A governed gap may not be rendered as a zero."""
    series = (_figure("a", "100"), _figure("b", None))
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a", "b"))
    assert build_chart(spec, series, direction=DIRECTION_LTR) is None


def test_mixed_units_yield_no_chart() -> None:
    """One axis states one dimension; a ratio beside a count scales to nothing."""
    series = (_figure("a", "25", unit_kind="count"), _figure("b", "0.18", "x", "ratio"))
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a", "b"))
    assert build_chart(spec, series, direction=DIRECTION_LTR) is None


def test_a_flat_series_yields_no_chart() -> None:
    series = (_figure("a", "0"), _figure("b", "0"))
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a", "b"))
    assert build_chart(spec, series, direction=DIRECTION_LTR) is None


def test_bar_chart_has_no_polyline() -> None:
    view = build_chart(_SPEC, _SERIES, direction=DIRECTION_LTR)
    assert view.polyline == ""


def test_line_chart_polyline_is_derived_from_the_marks() -> None:
    spec = ChartSpec(kind=CHART_LINE, figure_ids=("a", "b", "c"))
    view = build_chart(spec, _SERIES, direction=DIRECTION_LTR)
    points = view.polyline.split(" ")
    assert len(points) == len(view.marks)
    # Each point's y is exactly the mark's y -- derivation, not a second sum.
    assert [point.split(",")[1] for point in points] == [m.y for m in view.marks]


def test_negative_values_hang_from_the_zero_line() -> None:
    series = (_figure("a", "-50", "Jan"), _figure("b", "100", "Feb"))
    spec = ChartSpec(kind=CHART_BAR, figure_ids=("a", "b"))
    view = build_chart(spec, series, direction=DIRECTION_LTR)
    assert all(Decimal(mark.height) >= 0 for mark in view.marks)


def test_unknown_chart_kind_is_refused_at_the_spec() -> None:
    with pytest.raises(ReportError, match="chart kind"):
        ChartSpec(kind="pie", figure_ids=("a",))


def test_empty_chart_spec_is_refused() -> None:
    with pytest.raises(ReportError, match="at least one figure"):
        ChartSpec(kind=CHART_BAR, figure_ids=())
