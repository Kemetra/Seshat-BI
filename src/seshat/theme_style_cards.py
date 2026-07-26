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

from collections.abc import Callable

from seshat.color import is_valid_hex

# The theme spec's stated number-format vocabulary (section 5). Anything else is
# refused rather than passed through, mirroring how ``_VALID_SCALING`` constrains
# page-background scaling.
VALID_NUMBER_FORMATS: tuple[str, ...] = ("#,##0", "#,##0.00", "0.0%")

VALID_TITLE_ALIGNMENTS: tuple[str, ...] = ("left", "center", "right")

# The token keys ``build_star_cards``/``build_page_cards`` read, single-sourced
# here so both the reader (``theme_compile.chrome_from_tokens``/
# ``page_from_tokens``) and the writer (``theme_gen.render_tokens_yaml``) agree
# key-for-key on the same allow-list -- a key present in one but not the other
# is exactly the kind of drift that silently drops a generated card on a
# tokens->theme->tokens round trip (finding 2).
CHROME_TOKEN_KEYS: tuple[str, ...] = (
    "gridline",
    "border",
    "title_align",
    "data_labels",
    "number_format",
)
PAGE_TOKEN_KEYS: tuple[str, ...] = (
    "background",
    "background_transparency",
    "wallpaper",
    "wallpaper_transparency",
    "filter_pane_background",
    "filter_pane_text",
    "filter_card_applied",
    "filter_card_available",
)


class StyleCardError(Exception):
    """A style-card token problem surfaced cleanly (no traceback)."""


def _fill(hex_color: str) -> dict:
    """The theme JSON fill wrapper Power BI expects for a color value."""
    return {"solid": {"color": hex_color}}


def _require_hex(value: object, field: str) -> str:
    if not isinstance(value, str) or not is_valid_hex(value):
        raise StyleCardError(f"{field} must be a #RRGGBB hex color, got {value!r}")
    return value


def _require_pct(value: object, field: str) -> float:
    """A transparency percent in [0, 100], or raise naming the offending field.

    Mirrors ``_require_hex``'s "validate and return, or raise cleanly" shape so
    every token guard in this module fails the same way (a ``StyleCardError``
    naming the field, never a bare traceback).
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StyleCardError(f"{field} must be a number, got {value!r}")
    if not (0.0 <= float(value) <= 100.0):
        raise StyleCardError(f"{field} must be in [0, 100], got {value!r}")
    return float(value)


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


def _apply_number_format(chrome: dict, cards: dict[str, list[dict]]) -> None:
    """Refuse ``chrome.number_format`` outright -- no verified emission key.

    OWNER-RULED (finding 3, PR #518 review): Power BI's ``"*"`` wildcard theme
    section accepts ANY key name (``patternProperties: ^.+$``), so a guessed
    key would be silently ignored by Desktop -- a fail-open in the artifact,
    worse than emitting nothing. The verified key names that DO exist in the
    published schema (``formatString``, ``labelDisplayUnits``, ``labelFormat``,
    ``labelPrecision``, ``displayUnits``) live under NAMED visual types, not
    the ``"*"`` wildcard this builder targets, so none of them apply here.
    Rather than accept the token and silently drop it (the prior behaviour --
    validate-then-discard, invisible to the caller), refuse it explicitly so
    a caller cannot believe ``number_format`` took effect. ``VALID_NUMBER_FORMATS``
    stays exported: other code/tests still reference the vocabulary.
    """
    fmt = chrome["number_format"]
    if fmt not in VALID_NUMBER_FORMATS:
        raise StyleCardError(
            f"number_format must be one of {VALID_NUMBER_FORMATS}, got {fmt!r}"
        )
    raise StyleCardError(
        f"number_format {fmt!r} is a valid theme-spec value but no verified "
        "reportThemeSchema key exists to emit it under visualStyles['*']['*'] "
        "-- Power BI's '*' wildcard section accepts any key name and would "
        "silently ignore a guessed one, so this is refused rather than "
        "accepted-then-dropped. Omit chrome.number_format until a verified "
        "emission key is confirmed."
    )


def _apply_gridline(chrome: dict, cards: dict[str, list[dict]]) -> None:
    """Emit matching ``categoryAxis``/``valueAxis`` gridline cards."""
    axis = _axis_card(chrome["gridline"])
    cards["categoryAxis"] = axis
    cards["valueAxis"] = list(axis)


def _apply_border(chrome: dict, cards: dict[str, list[dict]]) -> None:
    """Emit the ``border`` card: visible with a color, or explicitly off."""
    border = chrome["border"]
    if border is None:
        cards["border"] = [{"show": False}]
    else:
        cards["border"] = [
            {"color": _fill(_require_hex(border, "border")), "show": True}
        ]


def _apply_title_align(chrome: dict, cards: dict[str, list[dict]]) -> None:
    """Merge ``alignment`` into the existing title card rather than replace it.

    ``cards.setdefault("title", [{}])`` preserves any font card already present
    (or later added) for "title" -- ``render_theme_json`` relies on this merge,
    not overwrite, semantics.
    """
    align = chrome["title_align"]
    if align not in VALID_TITLE_ALIGNMENTS:
        raise StyleCardError(
            f"title_align must be one of {VALID_TITLE_ALIGNMENTS}, got {align!r}"
        )
    cards.setdefault("title", [{}])[0]["alignment"] = align


def _apply_data_labels(chrome: dict, cards: dict[str, list[dict]]) -> None:
    """Emit the ``labels`` card's ``show`` flag."""
    show = chrome["data_labels"]
    if not isinstance(show, bool):
        raise StyleCardError(f"data_labels must be true or false, got {show!r}")
    cards["labels"] = [{"show": show}]


# Dispatch table: token key -> the builder that handles it. Each builder reads
# its own key from ``chrome`` and mutates ``cards`` in place; ``build_star_cards``
# is then a single loop over this table instead of one branching block per key.
_STAR_CARD_BUILDERS: dict[str, Callable[[dict, dict[str, list[dict]]], None]] = {
    "number_format": _apply_number_format,
    "gridline": _apply_gridline,
    "border": _apply_border,
    "title_align": _apply_title_align,
    "data_labels": _apply_data_labels,
}


def build_star_cards(chrome: dict) -> dict[str, list[dict]]:
    """Section 5 cards for ``visualStyles["*"]["*"]``.

    ``chrome`` keys (all optional): ``gridline`` (hex or None), ``border`` (hex or
    None), ``title_align``, ``data_labels`` (bool), ``number_format``. An empty
    mapping yields no cards, so a theme that declares no chrome is unchanged.

    Dispatches to ``_STAR_CARD_BUILDERS`` -- one small function per token key --
    so adding/reviewing a key touches one function, not a growing if-chain.
    """
    if not chrome:
        return {}
    cards: dict[str, list[dict]] = {}
    for key, builder in _STAR_CARD_BUILDERS.items():
        if key in chrome:
            builder(chrome, cards)
    return cards


def _colored_card(page: dict, color_key: str, pct_key: str) -> list[dict] | None:
    """One color+transparency card, or None when the color is not declared.

    A transparency declared WITHOUT its colour is refused rather than dropped
    (#521): Power BI has no card to hang it on, so the early return would leave
    a valid-looking committed token with no effect and no explanation.
    """
    if color_key not in page:
        if pct_key in page:
            raise StyleCardError(
                f"{pct_key} is declared without {color_key}; a transparency "
                f"needs the colour it applies to -- declare {color_key} or "
                f"remove {pct_key}"
            )
        return None
    color = _require_hex(page[color_key], color_key)
    card: dict = {"color": _fill(color)}
    if pct_key in page:
        card["transparency"] = _require_pct(page[pct_key], pct_key)
    return [card]


def _outspace_pane_card(page: dict) -> list[dict] | None:
    """The ``outspacePane`` card (filter pane background/text), or None.

    When BOTH halves are declared they are gated against the WCAG AA text floor
    (#521). The palette-level contrast checks look at the palette text roles and
    the chrome borders/gridlines, never at this pair, so an unreadable filter
    pane -- identical fg/bg is the degenerate case -- otherwise validates as two
    fine hex values and ships.

    Presence is tested with ``in``, never ``.get(...) is not None``: a key
    PRESENT with a null value is a malformed input, not an absent one, and must
    reach ``_require_hex`` to be refused. Skipping it would silently drop the
    setting -- and silently skip the contrast gate when only one half is null.
    """
    pane: dict = {}
    has_bg = "filter_pane_background" in page
    has_text = "filter_pane_text" in page
    if has_bg:
        pane["backgroundColor"] = _fill(
            _require_hex(page["filter_pane_background"], "filter_pane_background")
        )
    if has_text:
        pane["foregroundColor"] = _fill(
            _require_hex(page["filter_pane_text"], "filter_pane_text")
        )
    if has_bg and has_text:
        _require_readable_pair(page["filter_pane_text"], page["filter_pane_background"])
    return [pane] if pane else None


def _require_readable_pair(text: str, background: str) -> None:
    """Refuse a filter-pane pair below the AA text contrast floor."""
    from seshat.color import contrast_ratio
    from seshat.theme_gen import AA_FLOOR

    ratio = contrast_ratio(text, background)
    if ratio < AA_FLOOR:
        raise StyleCardError(
            f"filter_pane_text {text} on filter_pane_background {background} "
            f"has contrast {ratio:.2f}:1 -- below the {AA_FLOOR}:1 WCAG AA text "
            f"floor; the filter pane would be unreadable"
        )


def _filter_state_cards(page: dict) -> list[dict] | None:
    """The ``filterCard`` array (one object per $id state), or None.

    filterCard is an ARRAY discriminated by $id -- one object per state.
    """
    filter_cards: list[dict] = []
    for state, key in (
        ("Applied", "filter_card_applied"),
        ("Available", "filter_card_available"),
    ):
        if key in page:
            filter_cards.append(
                {"$id": state, "backgroundColor": _fill(_require_hex(page[key], key))}
            )
    return filter_cards if filter_cards else None


def build_page_cards(page: dict) -> dict[str, list[dict]]:
    """Sections 6 and 7 cards for ``visualStyles["page"]["*"]``.

    Both spec sections land under the SAME ``page`` visual type per the published
    schema, which admits exactly ten cards there; four are in scope:
    ``background`` and ``outspace`` (section 7 -- ``outspace`` IS the wallpaper),
    plus ``outspacePane`` and ``filterCard`` (section 6).

    Section 6 styles the filter pane's LOOK only. Nothing here reads or writes
    filter state, selections, or bound fields.
    """
    if not page:
        return {}
    cards: dict[str, list[dict]] = {}
    for card_name, value in (
        ("background", _colored_card(page, "background", "background_transparency")),
        ("outspace", _colored_card(page, "wallpaper", "wallpaper_transparency")),
        ("outspacePane", _outspace_pane_card(page)),
        ("filterCard", _filter_state_cards(page)),
    ):
        if value is not None:
            cards[card_name] = value
    return cards
