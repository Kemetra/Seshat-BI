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
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read layout {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ReportError(f"layout {path} is not a mapping")
    cover = raw.get("cover_title_code")
    if not isinstance(cover, str) or not cover:
        raise ReportError(f"layout {path} has no cover_title_code")
    raw_sections = raw.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ReportError(f"layout {path} declares no sections")
    sections = tuple(_section(entry, path) for entry in raw_sections)
    orders = [section.order for section in sections]
    if orders != sorted(orders):
        raise ReportError(f"layout {path} sections are out of order: {orders}")
    return ReportLayout(cover_title_code=cover, sections=sections)


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
    if not isinstance(entry, dict):
        raise ReportError(f"layout {path} has a non-mapping section")
    section_id = entry.get("section_id")
    if not isinstance(section_id, str) or not section_id:
        raise ReportError(f"layout {path} has a section with no section_id")
    _reject_meaning(entry, section_id)
    order = entry.get("order")
    if not isinstance(order, int):
        raise ReportError(f"section {section_id!r} needs an int order")
    heading = entry.get("heading_code")
    if not isinstance(heading, str) or not heading:
        raise ReportError(f"section {section_id!r} needs a heading_code")
    visuals = entry.get("visual_ids")
    if not isinstance(visuals, list) or not visuals:
        raise ReportError(f"section {section_id!r} needs a non-empty visual_ids")
    if not all(isinstance(visual, str) for visual in visuals):
        raise ReportError(f"section {section_id!r} visual_ids must all be strings")
    return LayoutSection(
        section_id=section_id,
        order=order,
        heading_code=heading,
        visual_ids=tuple(visuals),
        page_break_before=bool(entry.get("page_break_before", False)),
        chart_kind=_chart_kind(entry, section_id),
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
