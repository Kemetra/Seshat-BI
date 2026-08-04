from __future__ import annotations

from decimal import Decimal

import pytest

from seshat.report.model import (
    BundleIdentity,
    CitedFigure,
    ReportBundle,
    ReportError,
    Section,
)

pytestmark = pytest.mark.unit


def _figure(
    figure_id: str = "f1", contract_id: str = "TotalSales", **over
) -> CitedFigure:
    fields = {
        "figure_id": figure_id,
        "citation_id": "c1",
        "contract_id": contract_id,
        "metric": "TotalSales",
        "unit_kind": "currency",
        "kind": "total",
        "section": "s1",
        "label": None,
        "value": Decimal("1552071.00"),
        "renderings": {"en": "1,552,071.00"},
    }
    fields.update(over)
    return CitedFigure(**fields)


def _bundle(*figures: CitedFigure) -> ReportBundle:
    return ReportBundle(
        identity=BundleIdentity(
            table="retail_store_sales", journey="first-hour", generated_for="board"
        ),
        figures=figures or (_figure(),),
        caveats=(),
        sections=(Section(section_id="s1", order=1, figure_ids=("f1",)),),
    )


def test_bundle_exposes_ordered_section_ids() -> None:
    assert _bundle().section_ids == ("s1",)


def test_figure_without_contract_id_is_refused() -> None:
    with pytest.raises(ReportError, match="contract"):
        _figure(contract_id="")


def test_figure_without_a_rendering_is_refused() -> None:
    """A surface may only reproduce text, so text must exist."""
    with pytest.raises(ReportError, match="rendering"):
        _figure(renderings={})


def test_figure_without_an_id_is_refused() -> None:
    with pytest.raises(ReportError, match="figure_id"):
        _figure(figure_id="")


def test_section_must_index_a_known_figure() -> None:
    with pytest.raises(ReportError, match="unknown figure"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(),),
            caveats=(),
            sections=(Section("s1", 1, ("missing",)),),
        )


def test_every_figure_must_belong_to_a_declared_section() -> None:
    with pytest.raises(ReportError, match="no declared section"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(), _figure(figure_id="f2")),
            caveats=(),
            sections=(Section("s1", 1, ("f1",)),),
        )


def test_sections_must_be_ordered() -> None:
    with pytest.raises(ReportError, match="order"):
        ReportBundle(
            identity=BundleIdentity("t", "j", "board"),
            figures=(_figure(),),
            caveats=(),
            sections=(
                Section("s2", 2, ("f1",)),
                Section("s1", 1, ()),
            ),
        )


def test_figure_is_immutable() -> None:
    with pytest.raises(Exception):
        _figure().figure_id = "other"  # type: ignore[misc]


def test_a_pending_figure_may_carry_no_value() -> None:
    """No data source must be expressible without inventing a number."""
    figure = _figure(value=None, renderings={"en": "[PENDING LIVE DATA]"})
    assert figure.value is None
    assert figure.renderings["en"] == "[PENDING LIVE DATA]"
