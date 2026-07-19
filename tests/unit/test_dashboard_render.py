import pytest

from seshat.dashboard.render import (
    _STAGE_LABELS_AR,
    _STAGE_ORDER,
    _STATUS_STYLE,
    render_page,
)
from seshat.dashboard.theme import DASHBOARD_CSS

pytestmark = pytest.mark.unit


def test_status_style_covers_all_four_statuses():
    assert set(_STATUS_STYLE) == {"not_started", "blocked", "warning", "pass"}
    for fg, bg in _STATUS_STYLE.values():
        assert fg.startswith("#") and bg.startswith("#")


def test_stage_order_is_the_canonical_seven():
    assert _STAGE_ORDER == (
        "source_ready",
        "mapping_ready",
        "silver_ready",
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    )
    assert set(_STAGE_LABELS_AR) == set(_STAGE_ORDER)


def test_render_page_empty_projection_shows_empty_state_not_crash():
    html = render_page({"tables": []})
    assert "<!DOCTYPE html>" in html
    assert 'dir="rtl"' in html
    assert "mappings/" in html  # the empty-state hint mentions where files go


def test_render_page_is_self_contained_no_remote_assets():
    html = render_page({"tables": []})
    assert "http://" not in html
    assert "https://" not in html


def test_theme_css_is_local_only():
    assert DASHBOARD_CSS.strip()
    assert "@import" not in DASHBOARD_CSS
    assert "http://" not in DASHBOARD_CSS and "https://" not in DASHBOARD_CSS


def test_render_page_inlines_the_theme_css():
    html_out = render_page({"tables": []})
    # a distinctive token from the brand palette must appear inline
    assert "#001E35" in html_out  # navy sidebar
    assert "<style>" in html_out
