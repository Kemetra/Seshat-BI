import pytest

from seshat.theme_style_cards import (
    VALID_NUMBER_FORMATS,
    StyleCardError,
    build_page_cards,
    build_star_cards,
)

pytestmark = pytest.mark.unit

CHROME = {
    "gridline": "#E1DFDD",
    "border": "#C8C6C4",
    "title_align": "left",
    "data_labels": False,
}


def test_build_star_cards_emits_both_axes_and_border():
    cards = build_star_cards(CHROME)
    assert set(cards) == {"categoryAxis", "valueAxis", "border", "title", "labels"}
    assert cards["categoryAxis"] == [
        {"gridlineColor": {"solid": {"color": "#E1DFDD"}}, "gridlineShow": True}
    ]
    assert cards["border"] == [{"color": {"solid": {"color": "#C8C6C4"}}, "show": True}]


def test_gridline_none_turns_gridlines_off_without_a_color():
    cards = build_star_cards({**CHROME, "gridline": None})
    assert cards["categoryAxis"] == [{"gridlineShow": False}]
    assert cards["valueAxis"] == [{"gridlineShow": False}]


def test_out_of_vocabulary_number_format_is_refused():
    with pytest.raises(StyleCardError, match="number_format"):
        build_star_cards({**CHROME, "number_format": "0.000"})


def test_every_valid_number_format_is_refused_no_verified_emission_key():
    """Finding 3: owner ruled against inventing a wildcard theme key -- Power
    BI's "*" section accepts ANY key name (patternProperties ^.+$), so a
    guessed key would be silently ignored by Desktop. No verified emission key
    exists yet, so chrome.number_format is refused outright rather than
    accepted and silently dropped (a fail-open in the artifact)."""
    for fmt in VALID_NUMBER_FORMATS:
        with pytest.raises(StyleCardError, match="number_format"):
            build_star_cards({**CHROME, "number_format": fmt})


def test_invalid_hex_is_refused():
    with pytest.raises(StyleCardError, match="gridline"):
        build_star_cards({**CHROME, "gridline": "not-a-hex"})


def test_bad_title_alignment_is_refused():
    with pytest.raises(StyleCardError, match="title_align"):
        build_star_cards({**CHROME, "title_align": "justified"})


def test_empty_chrome_emits_no_cards():
    assert build_star_cards({}) == {}


PAGE = {
    "background": "#FFFFFF",
    "background_transparency": 0,
    "wallpaper": "#F3F2F1",
    "wallpaper_transparency": 0,
    "filter_pane_background": "#FFFFFF",
    "filter_pane_text": "#252423",
    "filter_card_applied": "#E1DFDD",
    "filter_card_available": "#FFFFFF",
}


def test_page_cards_use_outspace_for_wallpaper():
    """outspace IS the wallpaper card per the published schema."""
    cards = build_page_cards(PAGE)
    assert cards["background"] == [
        {"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0.0}
    ]
    assert cards["outspace"] == [
        {"color": {"solid": {"color": "#F3F2F1"}}, "transparency": 0.0}
    ]


def test_filter_card_is_an_array_keyed_by_id():
    """filterCard carries a $id discriminator for its two states."""
    cards = build_page_cards(PAGE)
    ids = [c["$id"] for c in cards["filterCard"]]
    assert ids == ["Applied", "Available"]


def test_filter_pane_card_emitted():
    cards = build_page_cards(PAGE)
    assert cards["outspacePane"][0]["backgroundColor"] == {
        "solid": {"color": "#FFFFFF"}
    }


def test_page_transparency_out_of_range_is_refused():
    with pytest.raises(StyleCardError, match="background_transparency"):
        build_page_cards({**PAGE, "background_transparency": 150})


def test_empty_page_emits_no_cards():
    assert build_page_cards({}) == {}


def _flatten_dict_keys(value: dict) -> list[str]:
    """``_flatten_keys`` helper: a dict's own keys plus every nested key."""
    keys: list[str] = []
    for k, v in value.items():
        keys.append(k)
        keys.extend(_flatten_keys(v))
    return keys


def _flatten_list_keys(value: list) -> list[str]:
    """``_flatten_keys`` helper: every nested key across a list's items."""
    keys: list[str] = []
    for item in value:
        keys.extend(_flatten_keys(item))
    return keys


def _flatten_keys(value: object) -> list[str]:
    """Every dict key anywhere in ``value``, recursively (order not asserted)."""
    if isinstance(value, dict):
        return _flatten_dict_keys(value)
    if isinstance(value, list):
        return _flatten_list_keys(value)
    return []


# Independent literal (not imported from the builder): every key this appearance
# card vocabulary is allowed to contain. $id is the filterCard state
# discriminator, not filter STATE itself (Applied/Available are look presets,
# not a selection).
_APPEARANCE_ONLY_KEYS = {
    "color",
    "solid",
    "transparency",
    "backgroundColor",
    "foregroundColor",
    "$id",
}

# Words that would indicate the card touches filter STATE (a live selection,
# a bound field, or a filter expression) rather than pure appearance. None of
# these may appear anywhere in build_page_cards' output, as a substring of any
# emitted key.
_FILTER_STATE_WORDS = (
    "selection",
    "selected",
    "field",
    "expression",
    "condition",
    "restatement",
    "value",
    "target",
    "operator",
)


def test_page_cards_never_touch_filter_state():
    """Spec-promised boundary: build_page_cards is appearance-only. Within each
    emitted card's own contents (not the top-level card names, which are
    legitimate Power BI card identifiers like "outspacePane"/"filterCard"), the
    key set is a subset of the appearance-only vocabulary and contains nothing
    resembling a selection/field/filter-state key -- pin the guarantee so a
    future card addition cannot silently smuggle in filter state."""
    cards = build_page_cards(PAGE)  # maximal input: all 8 keys declared
    assert cards, "sanity: the maximal PAGE fixture must emit at least one card"
    inner_keys: set[str] = set()
    for card_body in cards.values():
        inner_keys.update(_flatten_keys(card_body))
    assert inner_keys <= _APPEARANCE_ONLY_KEYS, (
        f"unexpected key(s) outside the appearance-only vocabulary: "
        f"{inner_keys - _APPEARANCE_ONLY_KEYS}"
    )
    for key in inner_keys:
        lowered = key.lower()
        for word in _FILTER_STATE_WORDS:
            assert word not in lowered, (
                f"key {key!r} contains filter-state word {word!r} -- "
                "build_page_cards must never touch filter STATE"
            )
