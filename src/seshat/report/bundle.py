"""The one place a report's arithmetic and formatting happen.

Every surface downstream transcribes :attr:`CitedFigure.renderings`. That is why
this module exists: a figure is computed and formatted exactly once, so a workbook
and a PDF cannot round the same number differently -- neither of them rounds
anything.

``observations`` is the seam Increment B replaces with a gold query. Its shape does
not change when that happens, which is the point of putting the seam here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal

from seshat.report.layout import ReportLayout
from seshat.report.model import (
    BundleIdentity,
    CitedFigure,
    ReportBundle,
    ReportError,
    Section,
)

UNIT_KINDS = ("currency", "count", "ratio")

# What a figure slot says when no data source was reachable. Never a number:
# a document with invented figures is worse than a document with none.
PENDING = "[PENDING LIVE DATA]"

_CENTS = Decimal("0.01")


def render_value(value: Decimal, unit_kind: str) -> str:
    """The single formatting rule. Surfaces reproduce this string verbatim."""
    if unit_kind not in UNIT_KINDS:
        raise ReportError(
            f"unknown unit_kind {unit_kind!r}; expected one of {list(UNIT_KINDS)}"
        )
    if unit_kind == "currency":
        return f"{value.quantize(_CENTS, rounding=ROUND_HALF_UP):,}"
    if unit_kind == "count":
        return f"{value.quantize(Decimal(1), rounding=ROUND_HALF_UP):,}"
    percent = (value * 100).quantize(_CENTS, rounding=ROUND_HALF_UP)
    return f"{percent}%"


def build_bundle(
    *,
    table: str,
    generated_for: str,
    layout: ReportLayout,
    contracts: Mapping[str, str],
    observations: Sequence[Mapping[str, object]],
) -> ReportBundle:
    """Compute and format every figure once, then freeze it."""
    declared = {
        visual_id: section.section_id
        for section in layout.sections
        for visual_id in section.visual_ids
    }
    figures = tuple(
        _figure(entry, declared=declared, contracts=contracts) for entry in observations
    )
    sections = tuple(
        Section(
            section_id=section.section_id,
            order=section.order,
            figure_ids=tuple(
                figure.figure_id
                for figure in figures
                if figure.section == section.section_id
            ),
        )
        for section in layout.sections
    )
    return ReportBundle(
        identity=BundleIdentity(
            table=table, journey="report", generated_for=generated_for
        ),
        figures=figures,
        caveats=(),
        sections=sections,
    )


def _figure(
    entry: Mapping[str, object],
    *,
    declared: Mapping[str, str],
    contracts: Mapping[str, str],
) -> CitedFigure:
    visual_id = str(entry.get("visual_id") or "")
    contract_id = str(entry.get("contract_id") or "")
    if visual_id not in declared:
        raise ReportError(
            f"observation for visual {visual_id!r} is not in the layout; the "
            "overlay decides what appears"
        )
    if contract_id not in contracts:
        raise ReportError(
            f"visual {visual_id!r} cites {contract_id!r}, which is not an approved "
            "contract; an unattributed figure refuses the render"
        )
    unit_kind = str(entry.get("unit_kind") or "")
    raw = entry.get("value")
    value = raw if isinstance(raw, Decimal) else None
    text = PENDING if value is None else render_value(value, unit_kind)
    label = entry.get("label")
    return CitedFigure(
        figure_id=visual_id,
        citation_id=f"{contract_id}#{visual_id}",
        contract_id=contract_id,
        metric=str(entry.get("metric") or contract_id),
        unit_kind=unit_kind or "count",
        kind="total",
        section=declared[visual_id],
        label=str(label) if isinstance(label, str) else None,
        value=value,
        renderings={"en": text},
    )
