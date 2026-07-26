"""Power BI theme style-card builders (theme spec sections 5/6/7).

Pure functions: committed design tokens in, theme-JSON card dicts out. No I/O, no
file reads, no validation of the wider theme -- ``theme_gen`` owns those. Split
from ``theme_gen`` so neither module carries both the palette pipeline and the
card vocabularies.

Every key path here is verified against Microsoft's published validation schema
(``reportThemeSchema-2.156.json``, ``microsoft/powerbi-desktop-samples``):

    visualStyles > <visualName> > <stylePresetName> > <cardName> > [{prop: value}]

Stdlib only. Uses no pbi-cli, no live Power BI, no network.
"""

from __future__ import annotations

from seshat.color import is_valid_hex

# The theme spec's stated number-format vocabulary (section 5). Anything else is
# refused rather than passed through, mirroring how ``_VALID_SCALING`` constrains
# page-background scaling.
VALID_NUMBER_FORMATS: tuple[str, ...] = ("#,##0", "#,##0.00", "0.0%")

VALID_TITLE_ALIGNMENTS: tuple[str, ...] = ("left", "center", "right")


class StyleCardError(Exception):
    """A style-card token problem surfaced cleanly (no traceback)."""


def _fill(hex_color: str) -> dict:
    """The theme JSON fill wrapper Power BI expects for a color value."""
    return {"solid": {"color": hex_color}}


def _require_hex(value: object, field: str) -> str:
    if not isinstance(value, str) or not is_valid_hex(value):
        raise StyleCardError(f"{field} must be a #RRGGBB hex color, got {value!r}")
    return value


def _axis_card(gridline: object) -> list[dict]:
    """One axis card: gridline color when declared, else gridlines off.

    ``None`` is a deliberate "no gridlines" declaration, not a missing value --
    it emits ``gridlineShow: False`` rather than omitting the card, so the intent
    is explicit in the theme a human reviews.
    """
    if gridline is None:
        return [{"gridlineShow": False}]
    color = _require_hex(gridline, "gridline")
    return [{"gridlineColor": _fill(color), "gridlineShow": True}]


def build_star_cards(chrome: dict) -> dict[str, list[dict]]:
    """Section 5 cards for ``visualStyles["*"]["*"]``.

    ``chrome`` keys (all optional): ``gridline`` (hex or None), ``border`` (hex or
    None), ``title_align``, ``data_labels`` (bool), ``number_format``. An empty
    mapping yields no cards, so a theme that declares no chrome is unchanged.

    NOTE: ``number_format`` is validated against ``VALID_NUMBER_FORMATS`` (refuse
    fast on a bad token) but does not yet emit a card -- the brief that specified
    this builder gives a vocabulary to validate against but no verified
    ``reportThemeSchema-2.156.json`` key path to write it to (the per-visual
    ``labelPrecision``/format keys live under named visual types, not the ``"*"``
    wildcard this builder targets). Flagged as a known gap rather than guessing a
    key; a follow-up task should confirm the correct path before wiring emission.
    """
    if not chrome:
        return {}
    cards: dict[str, list[dict]] = {}

    if "number_format" in chrome:
        fmt = chrome["number_format"]
        if fmt not in VALID_NUMBER_FORMATS:
            raise StyleCardError(
                f"number_format must be one of {VALID_NUMBER_FORMATS}, got {fmt!r}"
            )

    if "gridline" in chrome:
        axis = _axis_card(chrome["gridline"])
        cards["categoryAxis"] = axis
        cards["valueAxis"] = list(axis)

    if "border" in chrome:
        border = chrome["border"]
        if border is None:
            cards["border"] = [{"show": False}]
        else:
            cards["border"] = [
                {"color": _fill(_require_hex(border, "border")), "show": True}
            ]

    if "title_align" in chrome:
        align = chrome["title_align"]
        if align not in VALID_TITLE_ALIGNMENTS:
            raise StyleCardError(
                f"title_align must be one of {VALID_TITLE_ALIGNMENTS}, got {align!r}"
            )
        cards.setdefault("title", [{}])[0]["alignment"] = align

    if "data_labels" in chrome:
        show = chrome["data_labels"]
        if not isinstance(show, bool):
            raise StyleCardError(f"data_labels must be true or false, got {show!r}")
        cards["labels"] = [{"show": show}]

    return cards
