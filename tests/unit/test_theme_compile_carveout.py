import pytest

from seshat.theme_compile import _human_owned_visual_styles

pytestmark = pytest.mark.unit


def test_generator_owned_page_cards_are_pruned():
    """A generator-emitted visualStyles["page"]["*"] is NOT human-owned."""
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
    assert _human_owned_visual_styles(vs) == {}


def test_human_added_page_card_survives_pruning():
    """A card the generator does NOT own stays visible as human-owned."""
    vs = {"page": {"*": {"pageRefresh": [{"show": True}]}}}
    assert _human_owned_visual_styles(vs) == {
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
    assert _human_owned_visual_styles(vs) == {}


def test_human_added_visual_type_survives():
    """Regression: an unrelated visual type is untouched."""
    vs = {"scatterChart": {"*": {"bubbles": [{"bubbleSize": -10}]}}}
    assert _human_owned_visual_styles(vs) == vs


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
    result = _human_owned_visual_styles(vs)
    assert result == {
        "page": {
            "My Preset": {"background": [{"color": {"solid": {"color": "#FFFFFF"}}}]}
        }
    }
