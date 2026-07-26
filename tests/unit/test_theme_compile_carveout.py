import pytest

from seshat.theme_compile import _human_owned_visual_styles

pytestmark = pytest.mark.unit


def test_generator_owned_page_cards_are_pruned():
    """A generator-emitted visualStyles["page"]["*"] is NOT human-owned, when
    the rendered theme actually emits that same page card set."""
    vs = {
        "page": {
            "*": {
                "background": [{"color": {"solid": {"color": "#FFFFFF"}}}],
                "outspace": [{"color": {"solid": {"color": "#F3F2F1"}}}],
                "outspacePane": [{"backgroundColor": {"solid": {"color": "#FFF"}}}],
                "filterCard": [{"$id": "Applied"}, {"$id": "Available"}],
            }
        }
    }
    assert _human_owned_visual_styles(vs, vs) == {}


def test_human_added_page_card_survives_pruning():
    """A card the generator does NOT own stays visible as human-owned."""
    vs = {"page": {"*": {"pageRefresh": [{"show": True}]}}}
    assert _human_owned_visual_styles(vs, vs) == {
        "page": {"*": {"pageRefresh": [{"show": True}]}}
    }


def test_generator_owned_star_cards_still_pruned():
    """Regression: the original *//* carve-out must keep working."""
    vs = {
        "*": {
            "*": {
                "title": [{"fontSize": 12}],
                "labels": [{"fontSize": 9}],
                "categoryAxis": [{"gridlineStyle": "dotted"}],
            }
        }
    }
    assert _human_owned_visual_styles(vs, vs) == {}


def test_human_added_visual_type_survives():
    """Regression: an unrelated visual type is untouched."""
    vs = {"scatterChart": {"*": {"bubbles": [{"bubbleSize": -10}]}}}
    assert _human_owned_visual_styles(vs, vs) == vs


def test_named_style_preset_is_human_owned_and_survives_pruning():
    """A NAMED style preset (anything other than "*") is human-authored by
    definition and must survive pruning intact, while the "*" preset's
    generator-owned cards are still pruned (F7)."""
    vs = {
        "page": {
            "My Preset": {"background": [{"color": {"solid": {"color": "#FFFFFF"}}}]},
            "*": {"background": [{"color": {"solid": {"color": "#F3F2F1"}}}]},
        }
    }
    result = _human_owned_visual_styles(vs, vs)
    assert result == {
        "page": {
            "My Preset": {"background": [{"color": {"solid": {"color": "#FFFFFF"}}}]}
        }
    }


# --- Finding 1 (P1): a card is generator-owned only when RENDERED emits it ----


def test_hand_tuned_star_border_surfaces_when_rendered_has_no_chrome():
    """A tokens file with no chrome: group renders no */*'border' card at all.
    A hand-tuned border in the EXISTING theme must therefore surface as
    human-owned -- not be pruned from both sides and silently deleted."""
    existing = {"*": {"*": {"border": [{"color": {"solid": {"color": "#123456"}}}]}}}
    rendered = {"*": {"*": {"title": [{"fontSize": 12}], "labels": [{"fontSize": 9}]}}}
    assert _human_owned_visual_styles(existing, rendered) == existing


def test_hand_tuned_page_background_surfaces_when_rendered_has_no_page_group():
    """Same shape, for visualStyles["page"] -- a hand-tuned page background must
    surface as a conflict when the rendered theme emits no page group at all
    (a tokens file predating `page:`)."""
    existing = {
        "page": {"*": {"background": [{"color": {"solid": {"color": "#ABCDEF"}}}]}}
    }
    rendered: dict = {"*": {"*": {"title": [{"fontSize": 12}]}}}
    assert _human_owned_visual_styles(existing, rendered) == existing


def test_generator_cards_still_pruned_when_tokens_declare_chrome_and_page():
    """Regression (finding 1 must not break the happy path): when the tokens
    DO declare chrome+page, the generator's own cards are still pruned and a
    clean recompile reports no conflict."""
    rendered = {
        "*": {
            "*": {
                "title": [{"fontSize": 12}],
                "labels": [{"fontSize": 9}],
                "categoryAxis": [{"gridlineShow": True}],
                "valueAxis": [{"gridlineShow": True}],
                "border": [{"show": True}],
            }
        },
        "page": {
            "*": {
                "background": [{"color": {"solid": {"color": "#FFFFFF"}}}],
                "outspace": [{"color": {"solid": {"color": "#F3F2F1"}}}],
            }
        },
    }
    # existing == rendered (a clean, unmodified recompile) -> no conflict.
    assert _human_owned_visual_styles(rendered, rendered) == {}
