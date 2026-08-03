"""The governed Excel surface: a workbook that only transcribes a bundle.

The discipline here is ported from ``Khepri/src/khepri/rra/rendering/excel.py`` at
commit ``7a1e3fd`` -- the sheet layout is Seshat's, but every rule below is
Khepri's and every reason it gives applies unchanged.

**The failure this exists to prevent.** A spreadsheet is the one surface a customer
can edit, re-sort, and hand to somebody else, and it is the only surface whose
cells can *execute*. Two things follow.

The first is formula injection. Excel treats a cell whose text begins ``=``,
``+``, ``-``, or ``@`` as a formula, and a cell that looks like an address as a
link. A label is customer-derived. So every cell here is written through
``write_string``, which never interprets, and the workbook additionally disables
formula, URL and number coercion. A hostile label reaches the cell verbatim and
inert -- verbatim because editing it would make this module a thing that decides
content.

The second is arithmetic. A ``SUM`` in a totals row would look like diligence.
There is no arithmetic in this module: every figure is the exact string
:mod:`seshat.report.bundle` produced.

**Why no cell is a number.** Excel stores every numeric cell as an IEEE 754
double, so writing a governed total as a number would round money through exactly
the representation a governed figure must not touch. Figures are written as the
decimal strings they were computed to -- which also preserves precision as a
statement: ``500.0`` and ``500.00`` are the same number and a different claim.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass

import xlsxwriter

from seshat.report.html import FigureCell, build_sections
from seshat.report.layout import ReportLayout
from seshat.report.model import ReportBundle
from seshat.report.vocabulary import Vocabulary

EXCEL_SURFACE_VERSION = "seshat.report.excel.v1"

# Every coercion XlsxWriter would otherwise apply to a string, switched off.
# `strings_to_numbers` is disabled for the same reason as the other two: a
# governed decimal that became a number would become a float.
WORKBOOK_OPTIONS = {
    "strings_to_formulas": False,
    "strings_to_urls": False,
    "strings_to_numbers": False,
    "in_memory": True,
}

_HEADER_FIGURE = "figure"
_HEADER_LABEL = "label"
_HEADER_VALUE = "value"
_HEADER_CONTRACT = "approved_contract"
_HEADER_CAVEAT = "caveat"
_PROVENANCE_SHEET = "Provenance"
_PROVENANCE_FIELD = "field"
_PROVENANCE_VALUE = "value"

# The only strings a cell may hold besides bundle content. Anything else in a cell
# came from the bundle, which is what keeps this module from deciding content.
GOVERNED_LABELS = frozenset(
    {
        EXCEL_SURFACE_VERSION,
        _HEADER_FIGURE,
        _HEADER_LABEL,
        _HEADER_VALUE,
        _HEADER_CONTRACT,
        _HEADER_CAVEAT,
        _PROVENANCE_SHEET,
        _PROVENANCE_FIELD,
        _PROVENANCE_VALUE,
        "table",
        "generated_for",
        "surface_version",
    }
)

_HEADERS = (_HEADER_FIGURE, _HEADER_LABEL, _HEADER_VALUE, _HEADER_CONTRACT)

# Excel caps a sheet name at 31 characters and forbids several punctuation marks.
_SHEET_NAME_LIMIT = 31
_SHEET_FORBIDDEN = ":\\/?*[]"


@dataclass(frozen=True, slots=True)
class ExcelSurface:
    workbook_bytes: bytes
    language: str
    surface_version: str = EXCEL_SURFACE_VERSION


def sheet_name(section_id: str) -> str:
    """A section id made safe for a sheet tab, deterministically."""
    cleaned = "".join(
        "_" if character in _SHEET_FORBIDDEN else character for character in section_id
    )
    return cleaned[:_SHEET_NAME_LIMIT] or "section"


def unique_sheet_names(section_ids: Sequence[str]) -> list[str]:
    """One distinct tab per section, in order.

    Normalising is lossy in three ways that all collide: forbidden characters map
    to the same underscore (``sales/east`` and ``sales:east``), Excel matches tab
    names case-insensitively, and names are truncated to 31 characters so long ids
    can share a prefix. A collision raises ``DuplicateWorksheetName`` from
    xlsxwriter and produces NO workbook at all, so the whole report is lost to a
    section-naming coincidence.

    The reserved provenance tab is claimed up front: a section called
    ``Provenance`` would otherwise take the tab that records where the figures came
    from, and the provenance write would be the one that failed.
    """
    names: list[str] = []
    claimed = {_PROVENANCE_SHEET.casefold()}
    for section_id in section_ids:
        base = sheet_name(section_id)
        candidate = base
        suffix = 2
        while candidate.casefold() in claimed:
            # Trim the base so the disambiguating suffix cannot push the name past
            # Excel's limit and re-collide.
            tail = f"_{suffix}"
            candidate = base[: _SHEET_NAME_LIMIT - len(tail)] + tail
            suffix += 1
        claimed.add(candidate.casefold())
        names.append(candidate)
    return names


class ExcelReportRenderer:
    """Writes the workbook. Holds no state between renders."""

    def render(
        self, bundle: ReportBundle, layout: ReportLayout, vocabulary: Vocabulary
    ) -> ExcelSurface:
        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, dict(WORKBOOK_OPTIONS))
        try:
            views = build_sections(bundle, layout, vocabulary)
            names = unique_sheet_names([view.section_id for view in views])
            for view, name in zip(views, names, strict=True):
                self._write_section(workbook, view, name)
            self._write_provenance(workbook, bundle)
        finally:
            workbook.close()
        return ExcelSurface(
            workbook_bytes=stream.getvalue(), language=vocabulary.language
        )

    def _write_section(self, workbook, section, name: str) -> None:
        sheet = workbook.add_worksheet(name)
        for column, header in enumerate(_HEADERS):
            sheet.write_string(0, column, header)
        for row, cell in enumerate(section.cells, start=1):
            self._write_cell(sheet, row, cell)
        self._write_caveats(sheet, section, start=len(section.cells) + 2)

    def _write_caveats(self, sheet, section, *, start: int) -> None:
        """The approved caveats for this section, on the sheet that carries its
        figures. A workbook is the surface most likely to be forwarded on its own,
        so a caveat that reached only the page would be the one lost."""
        for offset, caveat in enumerate(section.caveats):
            sheet.write_string(start + offset, 0, _HEADER_CAVEAT)
            sheet.write_string(start + offset, 1, caveat)

    def _write_cell(self, sheet, row: int, cell: FigureCell) -> None:
        # write_string never interprets. Nothing here inspects `value`.
        sheet.write_string(row, 0, cell.figure_id)
        sheet.write_string(row, 1, cell.label or "")
        sheet.write_string(row, 2, cell.text)
        sheet.write_string(row, 3, cell.contract_id)

    def _write_provenance(self, workbook, bundle: ReportBundle) -> None:
        sheet = workbook.add_worksheet(_PROVENANCE_SHEET)
        sheet.write_string(0, 0, _PROVENANCE_FIELD)
        sheet.write_string(0, 1, _PROVENANCE_VALUE)
        rows = (
            ("table", bundle.identity.table),
            ("generated_for", bundle.identity.generated_for),
            ("surface_version", EXCEL_SURFACE_VERSION),
        )
        for row, (field, value) in enumerate(rows, start=1):
            sheet.write_string(row, 0, field)
            sheet.write_string(row, 1, value)
