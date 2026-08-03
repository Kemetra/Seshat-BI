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
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ApprovedDesign:
    """The two things an owner approved, travelling together.

    They are one argument because they are one decision: the overlay says what
    appears and in what order, the contracts say what a figure is allowed to cite,
    and a bundle built from one without the other is not built from an approved
    design at all.
    """

    layout: ReportLayout
    contracts: Mapping[str, str]


def build_bundle(
    *,
    table: str,
    generated_for: str,
    design: ApprovedDesign,
    observations: Sequence[Mapping[str, object]],
) -> ReportBundle:
    """Compute and format every figure once, then freeze it."""
    layout = design.layout
    declared = {
        visual_id: section.section_id
        for section in layout.sections
        for visual_id in section.visual_ids
    }
    figures = tuple(
        _figure(entry, declared=declared, contracts=design.contracts)
        for entry in observations
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
    visual_id = _text(entry, "visual_id")
    contract_id = _text(entry, "contract_id")
    _assert_attributable(visual_id, contract_id, declared=declared, contracts=contracts)
    unit_kind = _text(entry, "unit_kind")
    value = _exact_value(entry)
    return CitedFigure(
        figure_id=visual_id,
        citation_id=f"{contract_id}#{visual_id}",
        contract_id=contract_id,
        metric=_text(entry, "metric") or contract_id,
        unit_kind=unit_kind or "count",
        kind="total",
        section=declared[visual_id],
        label=_label(entry),
        value=value,
        renderings={"en": _rendering(value, unit_kind)},
    )


def _assert_attributable(
    visual_id: str,
    contract_id: str,
    *,
    declared: Mapping[str, str],
    contracts: Mapping[str, str],
) -> None:
    """A figure has to be both asked for and attributable, or it does not appear."""
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


def _text(entry: Mapping[str, object], key: str) -> str:
    return str(entry.get(key) or "")


def _exact_value(entry: Mapping[str, object]) -> Decimal | None:
    """Only an exact ``Decimal`` counts as data.

    Anything else -- a float that already lost precision, a string, a missing key
    -- reads as no observation, which renders as :data:`PENDING` rather than a
    number nobody computed.
    """
    raw = entry.get("value")
    return raw if isinstance(raw, Decimal) else None


def _label(entry: Mapping[str, object]) -> str | None:
    label = entry.get("label")
    return label if isinstance(label, str) else None


def _rendering(value: Decimal | None, unit_kind: str) -> str:
    return PENDING if value is None else render_value(value, unit_kind)
