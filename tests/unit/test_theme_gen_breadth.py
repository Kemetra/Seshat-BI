import json
from collections.abc import Callable

import pytest

from seshat.color import contrast_ratio
from seshat.theme_gen import (
    AA_NON_TEXT_FLOOR,
    ThemeGenError,
    ThemeSeed,
    _validate_and_collect,
    build_palette,
    check_non_text_contrast_or_raise,
    render_theme_json,
)

pytestmark = pytest.mark.unit


def _seed(**over) -> ThemeSeed:
    base = dict(
        name="breadth-test",
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


def test_no_chrome_emits_no_section5_cards():
    """Regression: an existing caller's output is unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert set(star) == {"title", "labels"}


def test_chrome_emits_gridline_and_border_cards():
    seed = _seed(chrome={"gridline": "#E1DFDD", "border": "#C8C6C4"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert star["categoryAxis"][0]["gridlineColor"] == {"solid": {"color": "#E1DFDD"}}
    assert star["border"][0]["show"] is True


def test_chrome_title_align_preserves_the_font_cards():
    """Regression: title_align/data_labels must not clobber the font cards.

    build_star_cards returns "title": [{"alignment": ...}] and
    "labels": [{"show": ...}] -- a naive dict.update at the wiring site would
    replace, not merge, wiping fontFamily/fontSize that render_theme_json
    already put there.
    """
    seed = _seed(chrome={"title_align": "left", "data_labels": True})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    star = doc["visualStyles"]["*"]["*"]
    assert star["title"][0]["fontSize"] == 12
    assert star["title"][0]["fontFamily"] == "Segoe UI Semibold"
    assert star["title"][0]["alignment"] == "left"
    assert star["labels"][0]["fontFamily"] == "Segoe UI"
    assert star["labels"][0]["show"] is True


def test_no_page_tokens_emits_no_page_visual_type():
    """Regression: absent page tokens leave visualStyles shape unchanged."""
    seed = _seed()
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    assert set(doc["visualStyles"]) == {"*"}


def test_page_tokens_emit_page_visual_type():
    seed = _seed(page={"background": "#FFFFFF", "wallpaper": "#F3F2F1"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    page = doc["visualStyles"]["page"]["*"]
    assert set(page) == {"background", "outspace"}


def test_page_cards_survive_a_compile_round_trip():
    """The Task-1 carve-out must not read generated page cards as hand-tuning."""
    from seshat.theme_compile import _human_owned_visual_styles

    seed = _seed(page={"background": "#FFFFFF"}, chrome={"gridline": "#E1DFDD"})
    doc = json.loads(render_theme_json(build_palette(seed), seed))
    vs = doc["visualStyles"]
    assert _human_owned_visual_styles(vs, vs) == {}


def test_invisible_gridline_is_refused():
    """A gridline nearly identical to the background must not pass."""
    seed = _seed(chrome={"gridline": "#FEFEFE"})  # on #FFFFFF background
    # Oracle: compute the ratio independently rather than trusting the module.
    assert contrast_ratio("#FEFEFE", "#FFFFFF") < AA_NON_TEXT_FLOOR
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_legible_gridline_passes():
    seed = _seed(chrome={"gridline": "#767676"})
    assert contrast_ratio("#767676", "#FFFFFF") >= AA_NON_TEXT_FLOOR
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_no_chrome_is_vacuously_fine():
    seed = _seed()
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_gridlines_off_is_not_a_contrast_failure():
    """None means gridlines off -- there is nothing to be invisible."""
    seed = _seed(chrome={"gridline": None})
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_generate_refuses_an_invisible_border_end_to_end(tmp_path):
    """The gate must run in the validate-before-write path, not just standalone."""
    seed = _seed(chrome={"border": "#FEFEFE"})
    with pytest.raises(ThemeGenError, match="border"):
        _validate_and_collect(seed, tmp_path, False)


def test_malformed_gridline_hex_raises_theme_gen_error_not_traceback():
    """A non-hex chrome color must fail cleanly, matching the module's
    "never a traceback" contract -- not leak a raw ValueError from
    contrast_ratio's hex parsing."""
    seed = _seed(chrome={"gridline": "nope"})
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


# --- Finding A: the non-text contrast gate must measure against the EMITTED
# page background (seed.page["background"]), not the palette background --
# when a page.background override is declared, it is what gridlines/borders
# actually render against in the compiled theme.


def test_gridline_invisible_against_declared_page_background_is_refused():
    """Repro: gridline #767676 passes against the palette bg #FFFFFF (4.54:1)
    but is truly invisible (1.00:1) against the DECLARED page.background
    #767676 that theme-spec sections 6/7 actually paint behind it. The gate
    must use the emitted ground, or an invisible gridline sails through the
    very check meant to catch invisible gridlines."""
    seed = _seed(chrome={"gridline": "#767676"}, page={"background": "#767676"})
    assert contrast_ratio("#767676", "#FFFFFF") >= AA_NON_TEXT_FLOOR  # passes on palette bg
    assert contrast_ratio("#767676", "#767676") < AA_NON_TEXT_FLOOR  # fails on real ground
    with pytest.raises(ThemeGenError, match="gridline"):
        check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_no_page_group_gridline_check_is_unchanged():
    """Regression: with no `page` declared at all, the ground is still the
    palette background -- a #767676 gridline on a #FFFFFF palette bg still
    passes, exactly as before this fix."""
    seed = _seed(chrome={"gridline": "#767676"})
    assert seed.page is None
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_gridline_legible_against_declared_page_background_passes():
    """Proves the RIGHT ground is used, not just a tightened floor: a
    gridline that would FAIL against the palette background must still PASS
    when it is legible against the declared page.background it actually
    renders on."""
    seed = _seed(chrome={"gridline": "#F5F5F5"}, page={"background": "#000000"})
    # Fails against the (irrelevant) palette background:
    assert contrast_ratio("#F5F5F5", "#FFFFFF") < AA_NON_TEXT_FLOOR
    # Passes against the declared page background it actually renders on:
    assert contrast_ratio("#F5F5F5", "#000000") >= AA_NON_TEXT_FLOOR
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def test_page_group_without_background_key_falls_back_to_palette():
    """A `page` group that declares no `background` key must not change the
    ground -- only a page.background OVERRIDE changes what gridlines render
    against."""
    seed = _seed(chrome={"gridline": "#767676"}, page={"wallpaper": "#F3F2F1"})
    check_non_text_contrast_or_raise(build_palette(seed), seed)


def _forbidden_dict_keys(node: dict, is_forbidden: Callable[[str], bool]) -> list[str]:
    """``_collect_forbidden_keys`` helper: check + recurse over one dict's items."""
    offenders: list[str] = []
    for key, value in node.items():
        if is_forbidden(key):
            offenders.append(key)
        offenders.extend(_collect_forbidden_keys(value, is_forbidden))
    return offenders


def _forbidden_list_keys(node: list, is_forbidden: Callable[[str], bool]) -> list[str]:
    """``_collect_forbidden_keys`` helper: recurse over one list's items."""
    offenders: list[str] = []
    for item in node:
        offenders.extend(_collect_forbidden_keys(item, is_forbidden))
    return offenders


def _collect_forbidden_keys(
    node: object, is_forbidden: Callable[[str], bool]
) -> list[str]:
    """Every dict key anywhere in ``node`` that ``is_forbidden`` flags."""
    if isinstance(node, dict):
        return _forbidden_dict_keys(node, is_forbidden)
    if isinstance(node, list):
        return _forbidden_list_keys(node, is_forbidden)
    return []


def test_no_emitted_key_name_trips_dl1():
    """DL1 substring-matches forbidden tokens in theme key NAMES at ERROR
    severity. All current section 5/6/7 names were verified clear; this test
    stops a future key addition from silently reintroducing a blocking rule
    failure on a theme the generator itself produced."""
    from seshat.rules.design_theme import _is_forbidden

    seed = _seed(
        chrome={
            "gridline": "#767676",
            "border": "#767676",
            "title_align": "left",
            "data_labels": False,
            # number_format intentionally omitted: finding 3 makes it a
            # refusal (StyleCardError), not an emitted card -- see
            # test_theme_style_cards.py's number-format refusal test.
        },
        page={
            "background": "#FFFFFF",
            "wallpaper": "#F3F2F1",
            "filter_pane_background": "#FFFFFF",
            "filter_card_applied": "#E1DFDD",
            "filter_card_available": "#FFFFFF",
        },
    )
    doc = json.loads(render_theme_json(build_palette(seed), seed))

    offenders = _collect_forbidden_keys(doc, _is_forbidden)
    assert offenders == [], f"emitted key names trip DL1: {offenders}"
