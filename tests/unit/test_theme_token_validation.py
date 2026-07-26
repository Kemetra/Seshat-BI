"""Fail-closed token validation and property-level pruning (#520, #521).

Both issues share one shape: a present-but-wrong input, or a human's hand-tune,
silently degrades to a no-op or an overwrite while the command exits 0. These
tests assert the ERROR IS RAISED (or the conflict IS registered) rather than
merely that the bad value is absent from the output -- the weaker oracle passes
for the wrong reason, because the value is absent either way.
"""

from __future__ import annotations

import json

import pytest

from seshat.theme_compile import ThemeCompileError, _human_owned_visual_styles
from seshat.theme_gen import ThemeSeed, build_palette, render_theme_json
from seshat.theme_style_cards import StyleCardError, build_page_cards

pytestmark = pytest.mark.unit

_SEED = dict(
    name="probe",
    mode="light",
    accent="#2A6FB0",
    background="#FFFFFF",
    text_primary="#1A1A1A",
    text_secondary="#444444",
    text_muted="#666666",
    data_colors=None,
    good="#107C10",
    neutral="#797775",
    bad="#A4262C",
)


def _rendered(**kw) -> dict:
    seed = ThemeSeed(**_SEED, **kw)
    return json.loads(render_theme_json(build_palette(seed), seed))["visualStyles"]


# --------------------------------------------------------------------------
# #520 -- property-axis pruning
# --------------------------------------------------------------------------


def test_human_property_inside_a_generated_card_survives_pruning():
    """#520: pruning is card-level while emission is property-level, so a human
    property hand-tuned INSIDE a generated card is pruned from both sides of the
    comparison and silently overwritten by `theme-compile --force`.

    Reachable with NO chrome/page tokens at all: `title` and `labels` are
    emitted unconditionally, and both are in main's owned-cards set.
    """
    rendered = _rendered()
    assert "title" in rendered["*"]["*"], "precondition: title emits unconditionally"

    # A card is a LIST of property bags -- [{prop: value, ...}] -- per the
    # published schema, and the generator writes fontFamily/fontSize into it.
    existing = {
        "*": {
            "*": {
                "title": [
                    {
                        "fontFamily": "Segoe UI Semibold",  # generator-owned
                        "fontSize": 12,  # generator-owned
                        "wordWrap": False,  # HUMAN
                        "alignment": "center",  # HUMAN
                    }
                ]
            }
        }
    }
    remainder = _human_owned_visual_styles(existing, rendered)
    kept = remainder["*"]["*"]["title"]
    assert kept == [{"wordWrap": False, "alignment": "center"}]


def test_a_fully_generated_card_still_prunes_to_nothing():
    """The negative half: a card carrying ONLY generator-owned properties must
    still prune away, or every token change would register a false conflict."""
    rendered = _rendered()
    emitted = rendered["*"]["*"]["title"]
    remainder = _human_owned_visual_styles({"*": {"*": {"title": emitted}}}, rendered)
    assert remainder == {}


def test_a_card_the_generator_never_emitted_survives_whole():
    """Card-axis behaviour (already fixed) must not regress while fixing the
    property axis."""
    rendered = _rendered()
    assert "categoryAxis" not in rendered["*"]["*"]
    existing = {"*": {"*": {"categoryAxis": [{"gridlineStyle": "dotted"}]}}}
    assert _human_owned_visual_styles(existing, rendered) == existing


# --------------------------------------------------------------------------
# #521 -- unknown / misspelled token keys
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("group", "bad_key"),
    [("chrome", "data_label"), ("page", "wallpaper_transparancy")],
)
def test_unknown_token_key_is_rejected(group, bad_key):
    """#521 finding 1: the allow-list comprehension drops an unknown key and
    compilation succeeds, so a typo is indistinguishable from an absent group."""
    from seshat.theme_compile import chrome_from_tokens, page_from_tokens

    reader = chrome_from_tokens if group == "chrome" else page_from_tokens
    with pytest.raises(ThemeCompileError, match=bad_key):
        reader({group: {bad_key: "#000000"}})


def test_known_token_keys_are_still_accepted():
    """The guard must not reject the real vocabulary."""
    from seshat.theme_compile import chrome_from_tokens, page_from_tokens

    assert chrome_from_tokens({"chrome": {"gridline": "#767676"}}) == {
        "gridline": "#767676"
    }
    assert page_from_tokens({"page": {"background": "#F3F3F3"}}) == {
        "background": "#F3F3F3"
    }


# --------------------------------------------------------------------------
# #521 -- filter-pane contrast
# --------------------------------------------------------------------------


def test_unreadable_filter_pane_pair_is_rejected():
    """#521 finding 2: identical filter-pane text/background validate as hex and
    emit unchanged, producing an unreadable pane at 1:1 contrast."""
    with pytest.raises(StyleCardError, match="filter_pane"):
        build_page_cards(
            {"filter_pane_text": "#808080", "filter_pane_background": "#808080"}
        )


def test_readable_filter_pane_pair_is_accepted():
    """A legible pair must still compile -- the gate is contrast, not presence."""
    cards = build_page_cards(
        {"filter_pane_text": "#1A1A1A", "filter_pane_background": "#FFFFFF"}
    )
    assert "outspacePane" in cards


def test_filter_pane_colour_alone_is_not_contrast_checked():
    """One half of the pair cannot be checked against an undeclared other half;
    it must not raise."""
    assert "outspacePane" in build_page_cards({"filter_pane_text": "#1A1A1A"})


# --------------------------------------------------------------------------
# #521 -- orphaned transparency
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct_key", "color_key"),
    [
        ("background_transparency", "background"),
        ("wallpaper_transparency", "wallpaper"),
    ],
)
def test_transparency_without_its_colour_is_rejected(pct_key, color_key):
    """#521 finding 3: the early return discards a declared transparency and
    compilation still succeeds, so a valid-looking token has no effect."""
    with pytest.raises(StyleCardError, match=pct_key):
        build_page_cards({pct_key: 50})


def test_transparency_with_its_colour_is_accepted():
    cards = build_page_cards({"background": "#F3F3F3", "background_transparency": 50})
    assert cards["background"][0]["transparency"] == 50
