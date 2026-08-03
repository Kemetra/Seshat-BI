from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from seshat.cli.commands.report import (
    EXIT_OK,
    EXIT_REFUSED,
    approved_contracts,
    build_report_parser,
    load_figure_plan,
    load_observations,
    report_main,
)
from seshat.report.gate import assert_renderable, stage_status
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_LAYOUT = {
    "version": 1,
    "cover_title_code": "cover.board_pack",
    "sections": [
        {
            "section_id": "headline",
            "order": 1,
            "heading_code": "section.headline",
            "visual_ids": ["v1"],
            "page_break_before": False,
        }
    ],
}


def _workspace(tmp_path: Path, *, status: str = "pass", contracts=("TotalSales",)):
    table = "demo_table"
    mappings = tmp_path / "mappings" / table
    (mappings / "design").mkdir(parents=True)
    (mappings / "metrics").mkdir(parents=True)
    for name in contracts:
        (mappings / "metrics" / f"{name}.yaml").write_text("id: x\n", encoding="utf-8")
    (mappings / "readiness-status.yaml").write_text(
        yaml.safe_dump(
            {"table": table, "stages": {"dashboard_ready": {"status": status}}}
        ),
        encoding="utf-8",
    )
    (mappings / "design" / "report-layout.yaml").write_text(
        yaml.safe_dump(_LAYOUT, sort_keys=False), encoding="utf-8"
    )
    observations = tmp_path / "obs.yaml"
    observations.write_text(
        yaml.safe_dump(
            {
                "observations": [
                    {
                        "visual_id": "v1",
                        "contract_id": "TotalSales",
                        "metric": "TotalSales",
                        "unit_kind": "currency",
                        "label": "Region A",
                        "value": "1552071",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return table, observations


def _args(tmp_path: Path, table: str, observations: Path, fmt: str = "html"):
    return build_report_parser().parse_args(
        [
            "--table",
            table,
            "--format",
            fmt,
            "--repo-root",
            str(tmp_path),
            "--observations",
            str(observations),
            "--output",
            str(tmp_path / "out"),
        ]
    )


def test_parser_requires_a_table() -> None:
    with pytest.raises(SystemExit):
        build_report_parser().parse_args(["--format", "html"])


def test_format_choices_are_the_three_surfaces() -> None:
    for surface in ("html", "xlsx", "pdf"):
        args = build_report_parser().parse_args(["--table", "t", "--format", surface])
        assert args.format == surface


def test_unknown_format_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_report_parser().parse_args(["--table", "t", "--format", "docx"])


def test_output_defaults_below_seshat_output() -> None:
    args = build_report_parser().parse_args(["--table", "t", "--format", "html"])
    assert str(args.output).startswith(".seshat-output")


def test_missing_readiness_file_is_not_a_pass(tmp_path: Path) -> None:
    """Absence of evidence is not evidence of approval."""
    assert stage_status(tmp_path, "absent_table") == "not_started"
    with pytest.raises(ReportError, match="not_started"):
        assert_renderable(tmp_path, "absent_table")


def test_a_readiness_file_that_is_not_a_mapping_is_not_a_pass(tmp_path: Path) -> None:
    """Malformed evidence is not evidence either."""
    path = tmp_path / "mappings" / "odd_table"
    path.mkdir(parents=True)
    (path / "readiness-status.yaml").write_text("- just\n- a list\n", encoding="utf-8")
    assert stage_status(tmp_path, "odd_table") == "not_started"
    with pytest.raises(ReportError, match="not_started"):
        assert_renderable(tmp_path, "odd_table")


def test_an_unreadable_readiness_file_refuses_rather_than_defaulting(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mappings" / "broken_table"
    path.mkdir(parents=True)
    (path / "readiness-status.yaml").write_text("stages: [oops\n", encoding="utf-8")
    with pytest.raises(ReportError, match="cannot read"):
        stage_status(tmp_path, "broken_table")


def test_gate_reads_the_recorded_status(tmp_path: Path) -> None:
    table, _ = _workspace(tmp_path, status="warning")
    assert stage_status(tmp_path, table) == "warning"
    with pytest.raises(ReportError, match="dashboard_ready"):
        assert_renderable(tmp_path, table)


def test_gate_passes_when_recorded_pass(tmp_path: Path) -> None:
    table, _ = _workspace(tmp_path)
    assert assert_renderable(tmp_path, table) is None


def test_shipped_table_is_gated_on_its_real_status() -> None:
    """retail_store_sales records dashboard_ready: pass, so it is renderable."""
    assert stage_status(_REPO, "retail_store_sales") == "pass"


def test_contract_ids_come_from_committed_metric_files(tmp_path: Path) -> None:
    table, _ = _workspace(tmp_path, contracts=("TotalSales", "TotalQuantity"))
    contracts = approved_contracts(tmp_path, table)
    assert set(contracts) == {"TotalSales", "TotalQuantity"}


def test_a_table_with_no_contracts_yields_none(tmp_path: Path) -> None:
    table, _ = _workspace(tmp_path, contracts=())
    assert approved_contracts(tmp_path, table) == {}


def test_observations_parse_to_exact_decimals(tmp_path: Path) -> None:
    _, observations = _workspace(tmp_path)
    parsed = load_observations(observations)
    assert parsed[0]["value"] == Decimal("1552071")
    assert isinstance(parsed[0]["value"], Decimal)


def test_a_non_decimal_observation_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump({"observations": [{"visual_id": "v1", "value": "twelve"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ReportError, match="not an exact decimal"):
        load_observations(path)


def test_empty_observations_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text(yaml.safe_dump({"observations": []}), encoding="utf-8")
    with pytest.raises(ReportError, match="no observations"):
        load_observations(path)


def test_blocked_gate_returns_exit_two(tmp_path: Path) -> None:
    table, observations = _workspace(tmp_path, status="blocked")
    assert report_main(_args(tmp_path, table, observations)) == EXIT_REFUSED


def test_missing_observations_flag_refuses_rather_than_inventing(
    tmp_path: Path,
) -> None:
    table, _ = _workspace(tmp_path)
    args = build_report_parser().parse_args(
        ["--table", table, "--format", "html", "--repo-root", str(tmp_path)]
    )
    assert report_main(args) == EXIT_REFUSED


def test_html_render_writes_a_document(tmp_path: Path) -> None:
    pytest.importorskip("jinja2", reason="requires the `report` extra")
    table, observations = _workspace(tmp_path)
    args = _args(tmp_path, table, observations)
    assert report_main(args) == EXIT_OK
    written = tmp_path / "out" / f"{table}.html"
    assert written.is_file()
    document = written.read_text(encoding="utf-8")
    assert "1,552,071.00" in document
    assert 'data-contract="TotalSales"' in document


def test_xlsx_render_writes_a_workbook(tmp_path: Path) -> None:
    pytest.importorskip("xlsxwriter", reason="requires the `report` extra")
    pytest.importorskip("jinja2", reason="requires the `report` extra")
    table, observations = _workspace(tmp_path)
    args = _args(tmp_path, table, observations, fmt="xlsx")
    assert report_main(args) == EXIT_OK
    written = tmp_path / "out" / f"{table}.xlsx"
    assert written.read_bytes()[:2] == b"PK"


def test_an_unapproved_contract_refuses_the_render(tmp_path: Path) -> None:
    pytest.importorskip("jinja2", reason="requires the `report` extra")
    table, observations = _workspace(tmp_path, contracts=("SomethingElse",))
    assert report_main(_args(tmp_path, table, observations)) == EXIT_REFUSED


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
