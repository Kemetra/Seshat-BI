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
    load_observations,
    report_main,
)
from seshat.report.gate import assert_renderable, stage_evidence, stage_status
from seshat.report.model import ReportError
from tests.unit._report_helpers import workspace as _workspace

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]


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


def test_a_pass_with_no_evidence_is_refused(tmp_path: Path) -> None:
    """A status with nothing behind it is not an approval.

    A bare `dashboard_ready: pass`, or a mapping whose evidence list is empty, is
    how an unreviewed design reaches a board's desk.
    """
    table, _ = _workspace(tmp_path, evidence=())
    assert stage_status(tmp_path, table) == "pass"
    assert stage_evidence(tmp_path, table) == ()
    with pytest.raises(ReportError, match="records no evidence"):
        assert_renderable(tmp_path, table)


def test_a_bare_pass_token_carries_no_evidence(tmp_path: Path) -> None:
    path = tmp_path / "mappings" / "bare_table"
    path.mkdir(parents=True)
    (path / "readiness-status.yaml").write_text(
        yaml.safe_dump({"stages": {"dashboard_ready": "pass"}}), encoding="utf-8"
    )
    assert stage_status(tmp_path, "bare_table") == "pass"
    assert stage_evidence(tmp_path, "bare_table") == ()
    with pytest.raises(ReportError, match="records no evidence"):
        assert_renderable(tmp_path, "bare_table")


def test_the_shipped_table_records_real_evidence() -> None:
    """The stricter gate holds for the table the kit actually ships."""
    assert len(stage_evidence(_REPO, "retail_store_sales")) >= 1
