from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from seshat.report.bundle import PENDING, build_bundle, render_value
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
        layout=_layout(tmp_path),
        contracts={"TotalSales": "mappings/retail_store_sales/metrics/TotalSales.yaml"},
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
            layout=_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            observations=rogue,
        )


def test_observation_for_an_undeclared_visual_is_refused(tmp_path: Path) -> None:
    rogue = [{**_OBS[0], "visual_id": "v99"}]
    with pytest.raises(ReportError, match="not in the layout"):
        build_bundle(
            table="t",
            generated_for="board",
            layout=_layout(tmp_path),
            contracts={"TotalSales": "x.yaml"},
            observations=rogue,
        )


def test_missing_value_renders_as_pending_not_a_number(tmp_path: Path) -> None:
    """No data source must never become an invented figure."""
    pending = [{**_OBS[0], "value": None}]
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=_layout(tmp_path),
        contracts={"TotalSales": "x.yaml"},
        observations=pending,
    )
    assert bundle.figures[0].renderings["en"] == PENDING
    assert bundle.figures[0].value is None


def test_sections_index_their_own_figures(tmp_path: Path) -> None:
    bundle = build_bundle(
        table="t",
        generated_for="board",
        layout=_layout(tmp_path),
        contracts={"TotalSales": "x.yaml"},
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
        layout=load_layout(layout_path),
        contracts=payload["contracts"],
        observations=observations,
    )
    assert len(bundle.figures) == len(observations)
    assert bundle.section_ids == ("headline", "mix")
    assert bundle.figures[4].renderings["en"] == "50.37%"
