"""The figure plan, read and checked against the signed bindings.

`figure_requests` is where the operator's plan meets the design review's decision,
so these tests pin which one wins and what happens when they disagree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seshat.report.binding import BindingMap, VisualBinding
from seshat.report.model import ReportError
from seshat.report.plan import contract_payloads, figure_requests, load_figure_plan

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_MAP = BindingMap(
    table="demo_table",
    bindings=(
        VisualBinding(visual_id="v01", contract="TotalSales"),
        VisualBinding(visual_id="v02", contract="TransactionCount"),
    ),
)


def _plan(tmp_path: Path, figures: list[dict]) -> Path:
    path = tmp_path / "plan.yaml"
    path.write_text(yaml.safe_dump({"figures": figures}), encoding="utf-8")
    return path


# --- loading ----------------------------------------------------------------


def test_a_valueless_plan_loads(tmp_path: Path) -> None:
    path = _plan(tmp_path, [{"visual_id": "v01", "unit_kind": "currency"}])
    assert load_figure_plan(path)[0]["visual_id"] == "v01"


def test_a_missing_plan_refuses(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="cannot read figure plan"):
        load_figure_plan(tmp_path / "absent.yaml")


def test_an_unparseable_plan_refuses(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text("figures: [oops\n", encoding="utf-8")
    with pytest.raises(ReportError, match="cannot read figure plan"):
        load_figure_plan(path)


def test_a_plan_that_is_not_a_mapping_refuses(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ReportError, match="not a mapping"):
        load_figure_plan(path)


def test_an_empty_plan_refuses(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="declares no figures"):
        load_figure_plan(_plan(tmp_path, []))


def test_a_plan_carrying_any_value_refuses(tmp_path: Path) -> None:
    """Even one value: --from-gold would discard it, and silence would leave the
    operator believing it had been checked against the warehouse."""
    path = _plan(
        tmp_path,
        [
            {"visual_id": "v01", "unit_kind": "currency"},
            {"visual_id": "v02", "value": 3},
        ],
    )
    with pytest.raises(ReportError, match="carries a value"):
        load_figure_plan(path)


def test_an_explicit_null_value_is_not_a_value(tmp_path: Path) -> None:
    """`label: null`/`value: null` is how YAML spells "absent"."""
    path = _plan(tmp_path, [{"visual_id": "v01", "unit_kind": "count", "value": None}])
    assert len(load_figure_plan(path)) == 1


# --- requests ---------------------------------------------------------------


def test_the_citation_comes_from_the_binding_map() -> None:
    """The plan never states it here, and the request still carries it."""
    requests = figure_requests([{"visual_id": "v01", "unit_kind": "currency"}], _MAP)
    assert requests[0].contract_id == "TotalSales"
    assert requests[0].unit_kind == "currency"
    assert requests[0].label is None


def test_a_plan_agreeing_with_the_map_is_accepted() -> None:
    requests = figure_requests(
        [{"visual_id": "v02", "contract_id": "TransactionCount", "unit_kind": "count"}],
        _MAP,
    )
    assert requests[0].contract_id == "TransactionCount"


def test_a_plan_disagreeing_with_the_map_refuses() -> None:
    with pytest.raises(ReportError, match="binding map binds it to 'TotalSales'"):
        figure_requests([{"visual_id": "v01", "contract_id": "TransactionCount"}], _MAP)


def test_a_visual_the_map_does_not_bind_refuses() -> None:
    with pytest.raises(ReportError, match="not bound"):
        figure_requests([{"visual_id": "v99"}], _MAP)


def test_a_label_is_carried_so_observe_can_refuse_the_breakdown() -> None:
    """`plan` does not decide breakdowns are impossible -- `observe` does. The label
    has to survive this far for that refusal to fire."""
    requests = figure_requests([{"visual_id": "v01", "label": "North"}], _MAP)
    assert requests[0].label == "North"


# --- contracts --------------------------------------------------------------


def test_the_shipped_contracts_all_load() -> None:
    payloads = contract_payloads(_REPO, "retail_store_sales")
    assert set(payloads) == {
        "TotalSales",
        "TotalQuantity",
        "TransactionCount",
        "AvgTransactionValue",
        "DiscountedTransactionRate",
    }
    assert payloads["TotalSales"]["definition"]["aggregation"] == "sum"


def test_a_table_with_no_metrics_directory_yields_nothing(tmp_path: Path) -> None:
    assert contract_payloads(tmp_path, "absent_table") == {}


def test_an_unreadable_contract_refuses_rather_than_being_skipped(
    tmp_path: Path,
) -> None:
    """A skipped contract makes its figure look unattributable, which reads as a
    design fault rather than as a broken file."""
    metrics = tmp_path / "mappings" / "t" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "Broken.yaml").write_text("name: [oops\n", encoding="utf-8")
    with pytest.raises(ReportError, match="cannot read contract"):
        contract_payloads(tmp_path, "t")
