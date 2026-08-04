from __future__ import annotations

from pathlib import Path

import pytest

from seshat.report.layout import load_layout
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_VALID = """\
version: 1
cover_title_code: cover.board_pack
sections:
  - section_id: overview
    order: 1
    heading_code: section.overview
    visual_ids: [v1, v2]
    page_break_before: false
  - section_id: detail
    order: 2
    heading_code: section.detail
    visual_ids: [v3]
    page_break_before: true
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "report-layout.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_layout_loads(tmp_path: Path) -> None:
    layout = load_layout(_write(tmp_path, _VALID))
    assert layout.cover_title_code == "cover.board_pack"
    assert [section.section_id for section in layout.sections] == ["overview", "detail"]
    assert layout.sections[1].page_break_before is True


def test_out_of_order_sections_are_refused(tmp_path: Path) -> None:
    text = _VALID.replace("order: 1", "order: 5")
    with pytest.raises(ReportError, match="order"):
        load_layout(_write(tmp_path, text))


def test_layout_may_not_introduce_a_figure(tmp_path: Path) -> None:
    """Presentation only: a value or metric in the overlay is a governance leak."""
    text = _VALID + "    value: 1234\n"
    with pytest.raises(ReportError, match="cannot introduce"):
        load_layout(_write(tmp_path, text))


def test_layout_may_not_name_a_contract(tmp_path: Path) -> None:
    text = _VALID + "    contract_id: TotalSales\n"
    with pytest.raises(ReportError, match="cannot introduce"):
        load_layout(_write(tmp_path, text))


def test_layout_may_not_carry_prose(tmp_path: Path) -> None:
    """Headings are governed codes, so no untranslated English reaches a page."""
    text = _VALID.replace("heading_code: section.overview", 'heading: "Overview"')
    with pytest.raises(ReportError, match="heading_code"):
        load_layout(_write(tmp_path, text))


def test_section_needs_at_least_one_visual(tmp_path: Path) -> None:
    text = _VALID.replace("visual_ids: [v3]", "visual_ids: []")
    with pytest.raises(ReportError, match="visual_ids"):
        load_layout(_write(tmp_path, text))


def test_missing_cover_title_code_is_refused(tmp_path: Path) -> None:
    text = _VALID.replace("cover_title_code: cover.board_pack\n", "")
    with pytest.raises(ReportError, match="cover_title_code"):
        load_layout(_write(tmp_path, text))


def test_unreadable_layout_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="cannot read"):
        load_layout(tmp_path / "absent.yaml")


def test_shipped_template_loads() -> None:
    layout = load_layout(_REPO / "templates" / "report-layout.yaml")
    assert layout.sections


def test_chart_kind_is_optional(tmp_path: Path) -> None:
    layout = load_layout(_write(tmp_path, _VALID))
    assert layout.sections[0].chart_kind is None


def test_governed_chart_kind_is_accepted(tmp_path: Path) -> None:
    text = _VALID.replace(
        "    visual_ids: [v1, v2]\n", "    visual_ids: [v1, v2]\n    chart_kind: bar\n"
    )
    layout = load_layout(_write(tmp_path, text))
    assert layout.sections[0].chart_kind == "bar"


def test_ungoverned_chart_kind_is_refused(tmp_path: Path) -> None:
    text = _VALID.replace(
        "    visual_ids: [v1, v2]\n", "    visual_ids: [v1, v2]\n    chart_kind: pie\n"
    )
    with pytest.raises(ReportError, match="chart_kind"):
        load_layout(_write(tmp_path, text))


def test_a_visual_repeated_in_one_section_is_refused(tmp_path: Path) -> None:
    """It would render the same governed figure twice."""
    path = tmp_path / "layout.yaml"
    path.write_text(
        """\
version: 1
cover_title_code: cover.x
sections:
  - section_id: a
    order: 1
    heading_code: section.a
    visual_ids: [v1, v1]
    page_break_before: false
""",
        encoding="utf-8",
    )
    with pytest.raises(ReportError, match="more than once"):
        load_layout(path)


def test_a_visual_repeated_across_sections_is_refused(tmp_path: Path) -> None:
    """Worse than a duplicate: the bundle maps visual to section once, so the
    figure lands in the last section claiming it and vanishes from the first."""
    path = tmp_path / "layout.yaml"
    path.write_text(
        """\
version: 1
cover_title_code: cover.x
sections:
  - section_id: a
    order: 1
    heading_code: section.a
    visual_ids: [v1]
    page_break_before: false
  - section_id: b
    order: 2
    heading_code: section.b
    visual_ids: [v1]
    page_break_before: false
""",
        encoding="utf-8",
    )
    with pytest.raises(ReportError, match="more than once"):
        load_layout(path)
