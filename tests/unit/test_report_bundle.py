from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from seshat.report.bundle import (
    PENDING,
    ApprovedDesign,
    build_bundle,
    render_value,
)
from seshat.report.layout import ReportLayout, load_layout
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_LAYOUT_TEXT = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: [v1]
    page_break_before: false
"""

_OBS = [
    {
        "visual_id": "v1",
        "contract_id": "TotalSales",
        "metric": "TotalSales",
        "unit_kind": "currency",
        "label": None,
        "value": Decimal("1552071"),
    }
]


def _layout(tmp_path: Path) -> ReportLayout:
    path = tmp_path / "report-layout.yaml"
    path.write_text(_LAYOUT_TEXT, encoding="utf-8")
    return load_layout(path)


def test_currency_renders_to_two_places_with_grouping() -> None:
    assert render_value(Decimal("1552071"), "currency") == "1,552,071.00"


def test_count_renders_without_decimals() -> None:
    assert render_value(Decimal("12575"), "count") == "12,575"


def test_ratio_renders_as_a_percentage_to_two_places() -> None:
    assert render_value(Decimal("0.5037"), "ratio") == "50.37%"


def test_currency_rounds_half_up() -> None:
    assert render_value(Decimal("1.005"), "currency") == "1.01"


def test_unknown_unit_kind_is_refused() -> None:
    with pytest.raises(ReportError, match="unit_kind"):
        render_value(Decimal("1"), "furlongs")


def test_bundle_carries_the_rendered_text(tmp_path: Path) -> None:
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        design=ApprovedDesign(
            layout=_layout(tmp_path),
            contracts={
                "TotalSales": "mappings/retail_store_sales/metrics/TotalSales.yaml"
            },
        ),
        observations=_OBS,
    )
    figure = bundle.figures[0]
    assert figure.renderings["en"] == "1,552,071.00"
    assert figure.contract_id == "TotalSales"
    assert figure.value == Decimal("1552071")
    assert figure.citation_id == "TotalSales#v1"


def test_observation_without_an_approved_contract_is_refused(tmp_path: Path) -> None:
    rogue = [{**_OBS[0], "contract_id": "InventedMetric"}]
    with pytest.raises(ReportError, match="not an approved contract"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_layout(tmp_path), contracts={"TotalSales": "x.yaml"}
            ),
            observations=rogue,
        )


def test_observation_for_an_undeclared_visual_is_refused(tmp_path: Path) -> None:
    """The declared visual is supplied too, so this reaches the layout check rather
    than the completeness check."""
    rogue = [_OBS[0], {**_OBS[0], "visual_id": "v99"}]
    with pytest.raises(ReportError, match="not in the layout"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_layout(tmp_path), contracts={"TotalSales": "x.yaml"}
            ),
            observations=rogue,
        )


def test_missing_value_renders_as_pending_not_a_number(tmp_path: Path) -> None:
    """No data source must never become an invented figure."""
    pending = [{**_OBS[0], "value": None}]
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(
            layout=_layout(tmp_path), contracts={"TotalSales": "x.yaml"}
        ),
        observations=pending,
    )
    assert bundle.figures[0].renderings["en"] == PENDING
    assert bundle.figures[0].value is None


def test_sections_index_their_own_figures(tmp_path: Path) -> None:
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(
            layout=_layout(tmp_path), contracts={"TotalSales": "x.yaml"}
        ),
        observations=_OBS,
    )
    assert bundle.sections[0].figure_ids == ("v1",)
    assert bundle.section_ids == ("overview",)


def test_shipped_fixture_builds(tmp_path: Path) -> None:
    payload = yaml.safe_load(
        (_REPO / "tests/fixtures/report/board_pack.yaml").read_text(encoding="utf-8")
    )
    observations = [
        {**entry, "value": Decimal(str(entry["value"]))}
        for entry in payload["observations"]
    ]
    layout_path = tmp_path / "report-layout.yaml"
    layout_path.write_text(
        yaml.safe_dump(payload["layout"], sort_keys=False), encoding="utf-8"
    )
    bundle = build_bundle(
        table=payload["table"],
        generated_for=payload["generated_for"],
        design=ApprovedDesign(
            layout=load_layout(layout_path), contracts=payload["contracts"]
        ),
        observations=observations,
    )
    assert len(bundle.figures) == len(observations)
    assert bundle.section_ids == ("headline", "mix", "by_region")
    assert bundle.figures[4].renderings["en"] == "50.37%"
    assert bundle.figures[5].renderings["en"] == "612,480.25"
    # Every figure cites one of the five approved contracts.
    assert {figure.contract_id for figure in bundle.figures} <= set(
        payload["contracts"]
    )


# --- governed design enforcement (Codex findings 2, 3, 14, 15) --------------

_TWO_VISUAL_LAYOUT = """\
version: 1
cover_title_code: cover.x
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: [v1, v2]
    page_break_before: false
"""

_RATE_CONTRACT = {
    "name": "DiscountRate",
    "definition": {
        "numerator": {"aggregation": "count_rows"},
        "denominator": {"aggregation": "count_rows"},
        "expected_value": {"value": "0.5", "aggregation": "ratio"},
    },
}


def _two_visual_layout(tmp_path: Path) -> ReportLayout:
    path = tmp_path / "two.yaml"
    path.write_text(_TWO_VISUAL_LAYOUT, encoding="utf-8")
    return load_layout(path)


def _obs(visual_id: str, contract_id: str = "TotalSales", **kwargs) -> dict:
    return {
        "visual_id": visual_id,
        "contract_id": contract_id,
        "metric": contract_id,
        "unit_kind": "currency",
        "label": None,
        "value": Decimal("10"),
        **kwargs,
    }


def test_a_duplicated_visual_observation_is_refused(tmp_path: Path) -> None:
    """Surfaces index figures by id, so one silently replaced the other and
    published the wrong governed number."""
    with pytest.raises(ReportError, match="observed more than once"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_two_visual_layout(tmp_path),
                contracts={"TotalSales": "x.yaml"},
            ),
            observations=[_obs("v1"), _obs("v1"), _obs("v2")],
        )


def test_an_omitted_visual_refuses_when_there_are_no_bindings(tmp_path: Path) -> None:
    """A partial file rendered an apparently complete pack with a KPI missing."""
    with pytest.raises(ReportError, match="no figure was supplied"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_two_visual_layout(tmp_path),
                contracts={"TotalSales": "x.yaml"},
            ),
            observations=[_obs("v1")],
        )


def test_an_omitted_visual_becomes_pending_when_bindings_exist(tmp_path: Path) -> None:
    """The visual stays on the page, stating that its number is not there."""
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(
            layout=_two_visual_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            bindings={"v1": "TotalSales", "v2": "TotalSales"},
        ),
        observations=[_obs("v1")],
    )
    by_id = {figure.figure_id: figure for figure in bundle.figures}
    assert by_id["v2"].renderings["en"] == PENDING
    assert by_id["v2"].contract_id == "TotalSales"
    assert by_id["v1"].renderings["en"] == "10.00"


def test_citing_the_wrong_approved_contract_is_refused(tmp_path: Path) -> None:
    """Membership let a TotalSales visual be populated and labelled as
    TotalQuantity while still advertising governed provenance."""
    with pytest.raises(ReportError, match="binding map binds it to 'TotalSales'"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_two_visual_layout(tmp_path),
                contracts={"TotalSales": "a.yaml", "TotalQuantity": "b.yaml"},
                bindings={"v1": "TotalSales", "v2": "TotalSales"},
            ),
            observations=[_obs("v1", "TotalQuantity"), _obs("v2")],
        )


def test_the_metric_name_comes_from_the_contract(tmp_path: Path) -> None:
    """An observation could name any metric beside a correct contract id, so a
    figure could be labelled as measuring something it did not."""
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(
            layout=_two_visual_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            definitions={"TotalSales": {"name": "TotalSales"}},
        ),
        observations=[
            _obs("v1", metric="SomethingElseEntirely"),
            _obs("v2"),
        ],
    )
    assert bundle.figures[0].metric == "TotalSales"


def test_a_rate_contract_declared_as_currency_is_refused(tmp_path: Path) -> None:
    """A TotalSales observation declaring ratio published 155207100.00%; the
    inverse is just as wrong."""
    with pytest.raises(ReportError, match="declares itself a rate"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_two_visual_layout(tmp_path),
                contracts={"DiscountRate": "x.yaml"},
                definitions={"DiscountRate": _RATE_CONTRACT},
            ),
            observations=[
                _obs("v1", "DiscountRate"),
                _obs("v2", "DiscountRate", unit_kind="ratio"),
            ],
        )


def test_a_non_rate_declared_as_a_ratio_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="does not declare itself a rate"):
        build_bundle(
            table="t",
            generated_for="board",
            design=ApprovedDesign(
                layout=_two_visual_layout(tmp_path),
                contracts={"TotalSales": "x.yaml"},
                definitions={"TotalSales": {"name": "TotalSales", "definition": {}}},
            ),
            observations=[_obs("v1", unit_kind="ratio"), _obs("v2")],
        )


def test_an_average_may_stay_currency_though_its_sql_divides(tmp_path: Path) -> None:
    """The distinction I got wrong first: division is not a percentage."""
    average = {
        "name": "AvgTransactionValue",
        "definition": {
            "numerator": {"aggregation": "sum"},
            "denominator": {"aggregation": "count_rows"},
        },
    }
    bundle = build_bundle(
        table="t",
        generated_for="board",
        design=ApprovedDesign(
            layout=_two_visual_layout(tmp_path),
            contracts={"AvgTransactionValue": "x.yaml"},
            definitions={"AvgTransactionValue": average},
        ),
        observations=[
            _obs("v1", "AvgTransactionValue"),
            _obs("v2", "AvgTransactionValue"),
        ],
    )
    assert bundle.figures[0].renderings["en"] == "10.00"
