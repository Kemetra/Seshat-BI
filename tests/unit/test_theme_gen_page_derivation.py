"""Findings 1 and 2 from issue #521 -- the ``page``/``chrome`` token groups
must derive into a dark seed, and the non-text contrast gate must measure the
ground those groups actually render, not the raw declared color.

Both findings were filed as "plausible from the code path but not individually
reproduced". Each test here asserts the OBSERVABLE change (a value inverted, a
gate raising or NOT raising) rather than the mere absence of a bad value from
output -- an absence oracle passes for the wrong reason, since the value is
absent either way.
"""

import pytest

from seshat.color import composite_over, contrast_ratio
from seshat.theme_gen import (
    _CHROME_COLOR_KEYS,
    _PAGE_COLOR_KEYS,
    AA_NON_TEXT_FLOOR,
    ThemeGenError,
    ThemeSeed,
    build_palette,
    check_non_text_contrast_or_raise,
    derive_dark_seed,
    generate_pair,
)
from seshat.theme_style_cards import CHROME_TOKEN_KEYS, PAGE_TOKEN_KEYS

pytestmark = pytest.mark.unit

# Non-color keys in each vocabulary: the exhaustion guard below pins that every
# shipped token key is deliberately classified as either color or non-color, so
# adding a key to the vocabulary without classifying it fails loudly instead of
# silently passing a light color into a dark theme (finding 2's root cause).
_PAGE_NON_COLOR_KEYS = ("background_transparency", "wallpaper_transparency")
_CHROME_NON_COLOR_KEYS = ("title_align", "data_labels", "number_format")


def _seed(**over) -> ThemeSeed:
    base = dict(
        name="page-derive-test",
        mode="light",
        accent="#118DFF",
        background="#FFFFFF",
        text_primary="#252423",
        text_secondary="#605E5C",
        text_muted="#605E5C",
        data_colors=("#118DFF", "#E66C37", "#1AAB40"),
        good="#1AAB40",
        neutral="#D9B300",
        bad="#D64550",
    )
    base.update(over)
    return ThemeSeed(**base)


# --------------------------------------------------------------------------
# Finding 2 -- derive_dark_seed must not pass page/chrome through unchanged
# --------------------------------------------------------------------------


def test_dark_derive_inverts_page_background():
    """The filed bug: a light page.background reaches the 'dark' theme intact.

    Reproduced on 2da8358 -- the palette background inverted to #000000 while
    the emitted page card stayed #FFFFFF, so the dark theme painted a white
    page.
    """
    dark = derive_dark_seed(_seed(page={"background": "#FFFFFF"}))
    assert dark.page["background"] != "#FFFFFF", (
        "page.background passed through unchanged -- the dark theme would "
        "paint a white page"
    )
    # Asserts the derived value, not merely that it changed: a dark page must
    # actually be darker than the light one it came from.
    assert contrast_ratio(dark.page["background"], "#FFFFFF") > 4.5


def test_dark_derive_inverts_every_declared_page_color_key():
    """Every color-valued page key derives (D1), not just ``background``."""
    declared = {key: "#FFFFFF" for key in _PAGE_COLOR_KEYS}
    dark = derive_dark_seed(_seed(page=declared))
    for key in _PAGE_COLOR_KEYS:
        assert dark.page[key] != "#FFFFFF", f"page.{key} did not derive"


def test_dark_derive_inverts_chrome_color_keys():
    dark = derive_dark_seed(_seed(chrome={"gridline": "#E0E0E0", "border": "#D8D8D8"}))
    assert dark.chrome["gridline"] != "#E0E0E0"
    assert dark.chrome["border"] != "#D8D8D8"


def test_dark_derive_leaves_non_color_keys_untouched():
    """Transparencies and formatting keys are not colors -- inverting them
    would corrupt them (a 50% transparency has no 'dark' counterpart)."""
    light = _seed(
        page={"background": "#FFFFFF", "background_transparency": 50},
        chrome={"gridline": "#E0E0E0", "title_align": "left"},
    )
    dark = derive_dark_seed(light)
    assert dark.page["background_transparency"] == 50
    assert dark.chrome["title_align"] == "left"


def test_dark_derive_preserves_explicit_null_as_off():
    """``None`` is an explicit "off" declaration, not a color to invert."""
    dark = derive_dark_seed(_seed(chrome={"border": None}, page={"wallpaper": None}))
    assert dark.chrome["border"] is None
    assert dark.page["wallpaper"] is None


def test_dark_derive_does_not_fabricate_undeclared_keys():
    """An undeclared key stays undeclared -- the derivation never invents a
    token the author did not write."""
    dark = derive_dark_seed(_seed(page={"background": "#FFFFFF"}))
    assert set(dark.page) == {"background"}


def test_dark_derive_with_no_page_or_chrome_is_unchanged():
    """Regression: the overwhelmingly common seed declares neither group."""
    dark = derive_dark_seed(_seed())
    assert not dark.page
    assert not dark.chrome


def test_color_key_sets_exhaust_the_shipped_vocabularies():
    """The gate-must-match-reader invariant, applied to a derivation.

    A key added to PAGE_TOKEN_KEYS/CHROME_TOKEN_KEYS without being classified
    here would silently pass a light-mode color into a dark theme -- exactly
    how finding 2 arose. Fail loudly at test time instead.
    """
    assert set(_PAGE_COLOR_KEYS) <= set(PAGE_TOKEN_KEYS)
    assert set(_CHROME_COLOR_KEYS) <= set(CHROME_TOKEN_KEYS)
    assert set(_PAGE_COLOR_KEYS) | set(_PAGE_NON_COLOR_KEYS) == set(PAGE_TOKEN_KEYS)
    assert set(_CHROME_COLOR_KEYS) | set(_CHROME_NON_COLOR_KEYS) == set(
        CHROME_TOKEN_KEYS
    )


# --------------------------------------------------------------------------
# Finding 1 -- the non-text gate must measure the COMPOSITED ground
# --------------------------------------------------------------------------


def test_transparent_page_background_does_not_hide_an_invisible_border():
    """The confirmed fail-open: a near-white border passes at 14.60:1 against
    a fully-transparent dark page.background while truly rendering at 1.23:1.
    """
    seed = _seed(
        background="#FFFFFF",
        page={"background": "#101820", "background_transparency": 100},
        chrome={"border": "#E8E8E8"},
    )
    # Precondition: the raw declared ground is what made this pass before.
    assert contrast_ratio("#E8E8E8", "#101820") > AA_NON_TEXT_FLOOR
    assert contrast_ratio("#E8E8E8", "#FFFFFF") < AA_NON_TEXT_FLOOR

    with pytest.raises(ThemeGenError, match="border"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_transparent_page_background_does_not_refuse_a_visible_border():
    """The same root cause, opposite direction -- and the reason the fix must
    correct the GROUND rather than add a one-sided tolerance.

    A dark border over a fully-transparent white page.background truly renders
    on the dark palette background at 12.55:1 -- plainly visible -- yet the
    uncomposited gate measured 1.43:1 and refused it.
    """
    seed = _seed(
        background="#101820",
        text_primary="#F3F2F1",
        text_secondary="#C8C6C4",
        text_muted="#C8C6C4",
        page={"background": "#FFFFFF", "background_transparency": 100},
        chrome={"border": "#D8D8D8"},
    )
    assert contrast_ratio("#D8D8D8", "#FFFFFF") < AA_NON_TEXT_FLOOR
    assert contrast_ratio("#D8D8D8", "#101820") > AA_NON_TEXT_FLOOR

    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_opaque_page_background_is_measured_as_declared():
    """Endpoint: transparency 0 means fully opaque, so the ground is exactly
    the declared page.background (composite_over's documented convention)."""
    seed = _seed(
        background="#101820",
        text_primary="#F3F2F1",
        text_secondary="#C8C6C4",
        text_muted="#C8C6C4",
        page={"background": "#FFFFFF", "background_transparency": 0},
        chrome={"border": "#E8E8E8"},
    )
    # Near-white border on an opaque white page is invisible and must refuse,
    # even though the palette background behind it is dark.
    with pytest.raises(ThemeGenError, match="border"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_partial_transparency_measures_the_composited_ground():
    """A mid-range transparency composites rather than snapping to an endpoint."""
    seed = _seed(
        background="#FFFFFF",
        page={"background": "#000000", "background_transparency": 50},
        chrome={"border": "#9A9A9A"},
    )
    expected = composite_over("#000000", "#FFFFFF", 50)
    ratio = contrast_ratio("#9A9A9A", expected)
    if ratio < AA_NON_TEXT_FLOOR:
        with pytest.raises(ThemeGenError, match="border"):
            check_non_text_contrast_or_raise(build_palette(seed), seed)
    else:
        check_non_text_contrast_or_raise(build_palette(seed), seed)
    # The gate must report the composited ground, never the raw declared one.
    assert expected != "#000000"


def test_no_transparency_declared_keeps_todays_behavior():
    """Regression: a page.background with no transparency key is measured
    exactly as declared -- unchanged from before this fix."""
    seed = _seed(
        background="#FFFFFF",
        page={"background": "#101820"},
        chrome={"border": "#E8E8E8"},
    )
    check_non_text_contrast_or_raise(build_palette(seed), seed)


# --------------------------------------------------------------------------
# The derived pair as a committed artifact
# --------------------------------------------------------------------------


def test_derived_dark_tokens_file_carries_the_inverted_page_group(tmp_path):
    """``render_tokens_yaml`` persists ``chrome``/``page`` (#523), so the dark
    tokens YAML a human edits next must carry the INVERTED values.

    Without this the inversion could be right in the emitted theme.json and
    wrong in the artifact the author opens -- two sources of truth disagreeing.
    Also asserts the file re-reads as a mapping, so the derived output does not
    round-trip into a parse error.
    """
    import yaml

    light = _seed(page={"background": "#FFFFFF"}, chrome={"gridline": "#767676"})
    _, dark_written = generate_pair(light, tmp_path)

    tokens = [p for p in dark_written if p.suffix in (".yaml", ".yml")]
    assert tokens, "the dark side of the pair wrote no tokens file"
    parsed = yaml.safe_load(tokens[0].read_text(encoding="utf-8"))
    assert parsed["page"]["background"] == "#000000"
    assert parsed["chrome"]["gridline"] != "#767676"


def test_pair_attributes_a_derived_seed_failure_to_the_derivation(tmp_path):
    """A gate failure on the DERIVED seed must say so.

    Inverting both halves of a pair does not preserve their contrast ratio, so
    a pane pair that cleared AA in light mode can fail once derived. Per D1 the
    refusal is correct -- but an unattributed error sends the author to debug
    the light tokens they wrote, which are not at fault.
    """
    # Verified pair: #878787 on #000000 clears AA at 5.85:1, but inverting both
    # halves yields 4.42:1 -- below the floor. Inversion preserves neither the
    # ratio nor its sign, so this is a real reachable state, not a contrivance.
    light = _seed(
        page={"filter_pane_background": "#000000", "filter_pane_text": "#878787"}
    )
    with pytest.raises(ThemeGenError, match="DERIVED dark seed"):
        generate_pair(light, tmp_path)
