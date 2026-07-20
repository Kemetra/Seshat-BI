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


_FIXTURE = {
    "tables": [
        {
            "table": "bronze.retail_store_sales",
            "source_path": "mappings/retail_store_sales/readiness-status.yaml",
            "current_stage": "publish_ready",
            "stages": {
                name: {"status": "pass", "evidence": [], "blocking_reasons": []}
                for name in _STAGE_ORDER
            },
            "blocking_reasons": [],
            "next_action": "All seven stages pass.",
        },
        {
            "table": "bronze.demo_sample_orders",
            "source_path": "mappings/demo_sample_orders/readiness-status.yaml",
            "current_stage": "gold_ready",
            "stages": {
                "source_ready": {
                    "status": "pass",
                    "evidence": ["50.37% known"],
                    "blocking_reasons": [],
                },
                "gold_ready": {
                    "status": "blocked",
                    "evidence": [],
                    "blocking_reasons": ["no DB offline"],
                },
            },
            "blocking_reasons": ["no DB offline"],
            "next_action": "Run the optional live leg.",
        },
    ]
}


def test_kpi_values_are_integer_counts_not_scores():
    html_out = render_page(_FIXTURE)
    # total tables = 2, publish-ready = 1, blocked = 1
    assert ">2<" in html_out  # total tables count
    assert ">1<" in html_out  # publish-ready / blocked counts
    # KPI region: after </head> (excludes inlined CSS's 100%/50%), before <table>
    kpi_region = html_out.split("</head>")[1].split("<table")[0]
    assert 'class="kpis"' in kpi_region
    assert "%" not in kpi_region  # KPI values are integer counts, never a score


def test_evidence_percent_passes_through_verbatim():
    html_out = render_page(_FIXTURE)
    assert "50.37%" in html_out  # evidence '%' is legitimate pass-through, not a score


def test_table_names_and_stage_labels_present():
    html_out = render_page(_FIXTURE)
    assert "bronze.retail_store_sales" in html_out
    assert "bronze.demo_sample_orders" in html_out
    for label in _STAGE_LABELS_AR.values():
        assert label in html_out


def test_blocked_stage_uses_blocked_color_and_shows_reason():
    html_out = render_page(_FIXTURE)
    assert "#C0392B" in html_out  # blocked fg color
    assert "no DB offline" in html_out  # blocking reason rendered


def test_injected_markup_is_escaped():
    evil = {
        "tables": [
            {
                "table": "<script>alert(1)</script>",
                "source_path": "mappings/x/readiness-status.yaml",
                "current_stage": "source_ready",
                "stages": {
                    "source_ready": {
                        "status": "pass",
                        "evidence": ["<b>x</b>"],
                        "blocking_reasons": [],
                    }
                },
                "blocking_reasons": [],
                "next_action": "<img src=x onerror=y>",
            }
        ]
    }
    html_out = render_page(evil)
    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;" in html_out
    assert "onerror=y" not in html_out or "&lt;img" in html_out


def test_table_has_anchor_id_for_in_page_nav():
    html_out = render_page(_FIXTURE)
    assert 'id="table-bronze.retail_store_sales"' in html_out


def test_meta_row_omitted_when_no_timestamp_injected():
    # default (generated_at=None) must stay deterministic: no meta row at all
    html_out = render_page(_FIXTURE)
    assert "آخر تحديث" not in html_out
    assert 'class="metarow"' not in html_out


def test_meta_row_shows_injected_render_timestamp():
    html_out = render_page(_FIXTURE, generated_at="2026-07-20 14:30")
    assert 'class="metarow"' in html_out
    assert "آخر تحديث: 2026-07-20 14:30" in html_out


def test_injected_timestamp_is_escaped():
    html_out = render_page(_FIXTURE, generated_at="<b>x</b>")
    assert "<b>x</b>" not in html_out
    assert "&lt;b&gt;x&lt;/b&gt;" in html_out


def test_governance_banner_is_present_and_read_only_reminder():
    html_out = render_page(_FIXTURE)
    assert 'class="banner"' in html_out
    assert "للقراءة فقط" in html_out  # read-only reminder copy
    assert "موافقة بشرية" in html_out  # human-approval gate reminder
    assert "%" not in html_out.split('class="banner"')[1].split("</div>")[0]


def test_inline_svg_icons_present_and_have_no_remote_refs():
    html_out = render_page(_FIXTURE)
    assert "<svg" in html_out
    # inline SVG must carry NO url-bearing attribute (self-contained gate)
    assert "xmlns" not in html_out  # http://www.w3.org/2000/svg would leak http://
    assert "xlink" not in html_out
    assert "<use" not in html_out


def test_stage_markers_keep_status_fill_color():
    # dot->SVG swap must preserve the per-status fill (blocked red still shows)
    html_out = render_page(_FIXTURE)
    assert 'fill="#C0392B"' in html_out  # blocked marker fill
    assert 'fill="#1F8A54"' in html_out  # pass marker fill


def test_render_page_tolerates_none_fields_without_crashing():
    projection = {
        "tables": [
            {
                "table": "t",
                "source_path": None,
                "current_stage": None,
                "stages": None,
                "blocking_reasons": None,
                "next_action": None,
            }
        ]
    }
    html_out = render_page(projection)
    assert isinstance(html_out, str)
    assert "t" in html_out
    assert '<div class="meta"></div>' in html_out  # None source_path -> "", not "None"
