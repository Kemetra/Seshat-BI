"""``seshat report --from-gold``: the live-figure path of the command.

Split from `test_report_cli.py` because it exercises a different seam -- the driver
and the signed bindings -- and shares only the workspace scaffolding.

No real database is touched. `_wire` stands in for the driver exactly as the
value-check tests do, so these assertions are about the command's wiring and its
refusals, not about Postgres.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from seshat.cli.commands.report import (
    EXIT_OK,
    EXIT_REFUSED,
    build_report_parser,
    report_main,
)
from seshat.report.model import ReportError
from seshat.report.plan import load_figure_plan
from tests.unit._report_helpers import workspace as _workspace

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

# --- increment B: figures from gold -----------------------------------------

_PLAN = {
    "table": "demo_table",
    "figures": [{"visual_id": "v1", "unit_kind": "currency", "label": None}],
}

_BINDING_MAP = """\
# Visual -> contract binding map -- demo

```yaml
schema: seshat.binding-map/v1
table: demo_table
visuals:
  - visual_id: v1
    page: overview
    contract: TotalSales
```
"""

_CONTRACT = {
    "name": "TotalSales",
    "binds_to": {"gold_table": "gold.fct_demo", "columns": ["total_spent"]},
    "definition": {"kind": "base", "aggregation": "sum", "filter": []},
}


class _Runner:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.sql: list[str] = []

    def run(self, sql: str, params: tuple = ()) -> list:
        self.sql.append(sql)
        return self.rows


def _gold_workspace(tmp_path: Path):
    """A workspace whose contracts carry definitions and whose bindings are signed."""
    table, _ = _workspace(tmp_path)
    mappings = tmp_path / "mappings" / table
    (mappings / "metrics" / "TotalSales.yaml").write_text(
        yaml.safe_dump(_CONTRACT, sort_keys=False), encoding="utf-8"
    )
    (mappings / "design" / "visual-contract-binding-map.md").write_text(
        _BINDING_MAP, encoding="utf-8"
    )
    plan = tmp_path / "plan.yaml"
    plan.write_text(yaml.safe_dump(_PLAN, sort_keys=False), encoding="utf-8")
    return table, plan


def _gold_args(tmp_path: Path, table: str, plan: Path, fmt: str = "html"):
    return build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            fmt,
            "--repo-root",
            str(tmp_path),
            "--from-gold",
            "--figure-plan",
            str(plan),
            "--output",
            str(tmp_path / "out"),
        ]
    )


def _wire(monkeypatch, rows):
    """Stand in for the driver seam, exactly as the value-check tests do."""
    from seshat import cli

    runner = _Runner(rows)
    monkeypatch.setattr(cli, "_ensure_driver", lambda: True, raising=False)
    monkeypatch.setattr(cli, "_make_runner", lambda config: runner, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host:5432/db")
    return runner


def test_both_figure_sources_at_once_is_refused(tmp_path: Path) -> None:
    table, observations = _workspace(tmp_path)
    args = build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            "html",
            "--repo-root",
            str(tmp_path),
            "--from-gold",
            "--observations",
            str(observations),
        ]
    )
    assert report_main(args) == EXIT_REFUSED


def test_from_gold_without_a_plan_is_refused(tmp_path: Path) -> None:
    table, _ = _workspace(tmp_path)
    args = build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            "html",
            "--repo-root",
            str(tmp_path),
            "--from-gold",
        ]
    )
    assert report_main(args) == EXIT_REFUSED


def test_a_plan_without_from_gold_is_refused(tmp_path: Path) -> None:
    """A plan carries no values, so on its own it renders nothing."""
    table, plan = _gold_workspace(tmp_path)
    args = build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            "html",
            "--repo-root",
            str(tmp_path),
            "--figure-plan",
            str(plan),
        ]
    )
    assert report_main(args) == EXIT_REFUSED


def test_a_plan_carrying_a_value_is_refused(tmp_path: Path) -> None:
    """Discarding it silently would let an operator believe a stale number was
    checked against the warehouse."""
    path = tmp_path / "plan.yaml"
    path.write_text(
        yaml.safe_dump({"figures": [{"visual_id": "v1", "value": "999"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ReportError, match="carries a value"):
        load_figure_plan(path)


def test_an_empty_plan_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text(yaml.safe_dump({"figures": []}), encoding="utf-8")
    with pytest.raises(ReportError, match="declares no figures"):
        load_figure_plan(path)


def test_a_valueless_plan_loads(tmp_path: Path) -> None:
    path = tmp_path / "plan.yaml"
    path.write_text(yaml.safe_dump(_PLAN, sort_keys=False), encoding="utf-8")
    assert load_figure_plan(path)[0]["visual_id"] == "v1"


def test_the_shipped_plan_fixture_carries_no_values() -> None:
    plan = load_figure_plan(_REPO / "tests/fixtures/report/board_pack_plan.yaml")
    assert len(plan) == 4
    assert all(entry.get("value") is None for entry in plan)


def test_from_gold_renders_the_live_number(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("jinja2", reason="requires the `report` extra")
    table, plan = _gold_workspace(tmp_path)
    runner = _wire(monkeypatch, [(Decimal("2400000.5"),)])
    assert report_main(_gold_args(tmp_path, table, plan)) == EXIT_OK
    document = (tmp_path / "out" / f"{table}.html").read_text(encoding="utf-8")
    assert "2,400,000.50" in document
    assert 'data-contract="TotalSales"' in document
    assert runner.sql == ['SELECT sum("total_spent") FROM "gold"."fct_demo"']


def test_an_unreachable_number_renders_pending_not_a_guess(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("jinja2", reason="requires the `report` extra")
    table, plan = _gold_workspace(tmp_path)
    _wire(monkeypatch, [(None,)])
    assert report_main(_gold_args(tmp_path, table, plan)) == EXIT_OK
    document = (tmp_path / "out" / f"{table}.html").read_text(encoding="utf-8")
    assert "PENDING LIVE DATA" in document


def test_a_plan_that_disagrees_with_the_signed_bindings_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """The design review decides the citation, not the operator's plan."""
    table, plan = _gold_workspace(tmp_path)
    plan.write_text(
        yaml.safe_dump(
            {
                "figures": [
                    {
                        "visual_id": "v1",
                        "contract_id": "SomethingElse",
                        "unit_kind": "currency",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _wire(monkeypatch, [(Decimal("1"),)])
    assert report_main(_gold_args(tmp_path, table, plan)) == EXIT_REFUSED


def test_from_gold_without_the_driver_refuses_with_the_extra_named(
    tmp_path: Path, monkeypatch
) -> None:
    from seshat import cli

    table, plan = _gold_workspace(tmp_path)
    monkeypatch.setattr(cli, "_ensure_driver", lambda: False, raising=False)
    assert report_main(_gold_args(tmp_path, table, plan)) == EXIT_REFUSED


def test_the_gate_still_applies_to_a_live_render(tmp_path: Path, monkeypatch) -> None:
    """Reading real numbers does not exempt a table from needing an approved design."""
    table, plan = _gold_workspace(tmp_path)
    (tmp_path / "mappings" / table / "readiness-status.yaml").write_text(
        yaml.safe_dump(
            {"table": table, "stages": {"dashboard_ready": {"status": "blocked"}}}
        ),
        encoding="utf-8",
    )
    _wire(monkeypatch, [(Decimal("1"),)])
    assert report_main(_gold_args(tmp_path, table, plan)) == EXIT_REFUSED
