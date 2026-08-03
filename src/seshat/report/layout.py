"""The print overlay: paging and section order, and nothing about meaning.

A dashboard layout has no page boxes, so this artifact supplies them. It is
deliberately unable to state a figure: the loader refuses any key that names a
value or a metric, because the moment an overlay can carry a number there are two
places a report's figures come from -- and then a board pack and a dashboard can
disagree with nothing to arbitrate.

Headings are governed CODES rather than text, for the reason Khepri's chart module
gives for the same choice: composing a sentence here would put untranslated
English on an Arabic page.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.report.model import GOVERNED_CHART_KINDS, ReportError
from seshat.report.reading import (
    required_int,
    required_list,
    required_mapping,
    required_text,
    required_text_list,
)

LAYOUT_TEMPLATE_NAME = "report-layout.yaml"

# Keys that would let presentation state meaning.
_FORBIDDEN_KEYS = ("value", "metric", "figure", "contract", "measure", "dax", "sql")
# Keys that would put untranslated prose on a page.
_PROSE_KEYS = ("heading", "title", "caption", "text", "label")


@dataclass(frozen=True, slots=True)
class LayoutSection:
    section_id: str
    order: int
    heading_code: str
    visual_ids: tuple[str, ...]
    page_break_before: bool
    # Which chart FORM this section is drawn as, or None for tables only. A form
    # is presentation, so it belongs here; what the figures MEAN stays in the
    # approved contracts.
    chart_kind: str | None = None


@dataclass(frozen=True, slots=True)
class ReportLayout:
    cover_title_code: str
    sections: tuple[LayoutSection, ...]


def load_layout(path: Path) -> ReportLayout:
    raw = _document(path)
    cover = _cover_title_code(raw, path)
    sections = tuple(_section(entry, path) for entry in _raw_sections(raw, path))
    _assert_ordered(sections, path)
    return ReportLayout(cover_title_code=cover, sections=sections)


def _document(path: Path) -> dict:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read layout {path}: {exc}") from exc
    return required_mapping(raw, refusal=f"layout {path} is not a mapping")


def _cover_title_code(raw: dict, path: Path) -> str:
    return required_text(
        raw, "cover_title_code", refusal=f"layout {path} has no cover_title_code"
    )


def _raw_sections(raw: dict, path: Path) -> list:
    return required_list(raw, "sections", refusal=f"layout {path} declares no sections")


def _assert_ordered(sections: tuple[LayoutSection, ...], path: Path) -> None:
    """Sections are read in file order, so the declared order has to agree with it."""
    orders = [section.order for section in sections]
    if orders != sorted(orders):
        raise ReportError(f"layout {path} sections are out of order: {orders}")


def _reject_meaning(entry: dict, section_id: str) -> None:
    for key in entry:
        lowered = str(key).lower()
        if any(bad in lowered for bad in _FORBIDDEN_KEYS):
            raise ReportError(
                f"section {section_id!r} key {key!r}: the print overlay cannot "
                "introduce a figure -- meaning belongs to the approved contracts"
            )
        if lowered in _PROSE_KEYS:
            raise ReportError(
                f"section {section_id!r} key {key!r}: use heading_code, not prose, "
                "so the wording resolves per language"
            )


def _section(entry: object, path: Path) -> LayoutSection:
    section = required_mapping(
        entry, refusal=f"layout {path} has a non-mapping section"
    )
    section_id = required_text(
        section, "section_id", refusal=f"layout {path} has a section with no section_id"
    )
    _reject_meaning(section, section_id)
    return LayoutSection(
        section_id=section_id,
        order=required_int(
            section, "order", refusal=f"section {section_id!r} needs an int order"
        ),
        heading_code=required_text(
            section,
            "heading_code",
            refusal=f"section {section_id!r} needs a heading_code",
        ),
        visual_ids=required_text_list(
            section,
            "visual_ids",
            refusal=f"section {section_id!r} needs a non-empty visual_ids of strings",
        ),
        page_break_before=bool(section.get("page_break_before", False)),
        chart_kind=_chart_kind(section, section_id),
    )


def _chart_kind(entry: dict, section_id: str) -> str | None:
    kind = entry.get("chart_kind")
    if kind is None:
        return None
    if not isinstance(kind, str) or kind not in GOVERNED_CHART_KINDS:
        raise ReportError(
            f"section {section_id!r} chart_kind {kind!r} is outside the governed "
            f"set {sorted(GOVERNED_CHART_KINDS)}"
        )
    return kind
