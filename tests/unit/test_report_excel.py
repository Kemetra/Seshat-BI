from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

pytest.importorskip("xlsxwriter", reason="requires the `report` extra")
pytest.importorskip("jinja2", reason="requires the `report` extra")

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


def _render(tmp_path: Path, label: str = "Region A"):
    from seshat.report.bundle import ApprovedDesign, build_bundle
    from seshat.report.excel import ExcelReportRenderer
    from seshat.report.layout import load_layout

    path = tmp_path / "report-layout.yaml"
    path.write_text(_LAYOUT_TEXT, encoding="utf-8")
    layout = load_layout(path)
    bundle = build_bundle(
        table="retail_store_sales",
        generated_for="board",
        design=ApprovedDesign(layout=layout, contracts={"TotalSales": "x.yaml"}),
        observations=[
            {
                "visual_id": "v1",
                "contract_id": "TotalSales",
                "metric": "TotalSales",
                "unit_kind": "currency",
                "label": label,
                "value": Decimal("1552071"),
            }
        ],
    )
    return ExcelReportRenderer().render(bundle, layout, "en")


def _sheet_xml(workbook_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        name = next(n for n in archive.namelist() if n.endswith("sheet1.xml"))
        return archive.read(name).decode("utf-8")


def _all_xml(workbook_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        return "".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def test_workbook_is_produced(tmp_path: Path) -> None:
    assert _render(tmp_path).workbook_bytes[:2] == b"PK"


def test_figure_text_is_present(tmp_path: Path) -> None:
    assert "1,552,071.00" in _all_xml(_render(tmp_path).workbook_bytes)


def test_no_cell_is_numeric(tmp_path: Path) -> None:
    """Money as a numeric cell would round-trip through IEEE 754."""
    xml = _sheet_xml(_render(tmp_path).workbook_bytes)
    assert 't="n"' not in xml


def test_formula_prefix_is_inert(tmp_path: Path) -> None:
    workbook = _render(tmp_path, label='=HYPERLINK("http://evil")').workbook_bytes
    xml = _all_xml(workbook)
    assert "<f>" not in xml
    assert "HYPERLINK" in xml  # verbatim, and dead


def test_leading_plus_and_at_are_inert(tmp_path: Path) -> None:
    for hostile in ("+1+1", "-1-1", "@SUM(A1)"):
        xml = _all_xml(_render(tmp_path, label=hostile).workbook_bytes)
        assert "<f>" not in xml


def test_no_totals_row_arithmetic(tmp_path: Path) -> None:
    """A SUM would look like diligence and be a second source of numbers."""
    xml = _all_xml(_render(tmp_path).workbook_bytes)
    assert "SUM(" not in xml


def test_contract_is_recorded_beside_every_figure(tmp_path: Path) -> None:
    assert "TotalSales" in _all_xml(_render(tmp_path).workbook_bytes)


def test_provenance_sheet_is_written(tmp_path: Path) -> None:
    xml = _all_xml(_render(tmp_path).workbook_bytes)
    assert "Provenance" in xml
    assert "seshat.report.excel.v1" in xml


def test_workbook_options_disable_every_coercion() -> None:
    from seshat.report.excel import WORKBOOK_OPTIONS

    assert WORKBOOK_OPTIONS["strings_to_formulas"] is False
    assert WORKBOOK_OPTIONS["strings_to_urls"] is False
    assert WORKBOOK_OPTIONS["strings_to_numbers"] is False


def test_module_contains_no_arithmetic_on_a_figure() -> None:
    """The one place arithmetic happens is bundle.py, not here."""
    source = (Path(__file__).parents[2] / "src/seshat/report/excel.py").read_text(
        encoding="utf-8"
    )
    body = source.split('"""', 2)[-1]
    assert "Decimal" not in body
    assert ".value" not in body


def test_sheet_name_is_made_safe() -> None:
    from seshat.report.excel import sheet_name

    assert sheet_name("a/b:c") == "a_b_c"
    assert len(sheet_name("x" * 60)) == 31
    assert sheet_name("") == "section"


# --- worksheet naming -------------------------------------------------------


def test_sections_normalising_to_one_name_get_distinct_tabs() -> None:
    """`sales/east` and `sales:east` both normalise to `sales_east`.

    A collision raises DuplicateWorksheetName from xlsxwriter and produces NO
    workbook, so the whole report is lost to a section-naming coincidence.
    """
    from seshat.report.excel import unique_sheet_names

    names = unique_sheet_names(["sales/east", "sales:east", "sales*east"])
    assert names[0] == "sales_east"
    assert len(set(names)) == 3


def test_case_only_variants_get_distinct_tabs() -> None:
    """Excel matches tab names case-insensitively."""
    from seshat.report.excel import unique_sheet_names

    names = unique_sheet_names(["Mix", "mix"])
    assert len({name.casefold() for name in names}) == 2


def test_a_section_cannot_take_the_provenance_tab() -> None:
    """Otherwise the sheet recording where the figures came from is the one lost."""
    from seshat.report.excel import unique_sheet_names

    assert unique_sheet_names(["Provenance"])[0].casefold() != "provenance"


def test_long_ids_sharing_a_prefix_get_distinct_tabs() -> None:
    """Names are truncated to 31 characters, so a shared prefix collides."""
    from seshat.report.excel import unique_sheet_names

    long_a = "a_very_long_section_identifier_one"
    long_b = "a_very_long_section_identifier_two"
    names = unique_sheet_names([long_a, long_b])
    assert len(set(names)) == 2
    assert all(len(name) <= 31 for name in names)
