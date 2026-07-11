from __future__ import annotations

from pathlib import Path

import pytest

from seshat.demo.html_report import render_html
from seshat.demo.report import _load_snapshot

pytestmark = pytest.mark.integration
_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)])
def test_demo_html_is_visible_accessible_and_stable(
    tmp_path: Path, viewport: tuple[int, int]
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    output = tmp_path / "index.html"
    output.write_text(render_html(_load_snapshot(_REPO), repo=_REPO), encoding="utf-8")

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(output.as_uri())
        assert page.locator("h1").inner_text() == "Readiness proof"
        assert page.locator(".stage-tab").count() == 7
        assert page.locator(".stage-detail").count() == 7
        assert page.locator("body").bounding_box()["height"] > viewport[1]
        assert page.locator(".product-header img").evaluate("img => img.complete")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        header_box = page.locator(".product-header").bounding_box()
        summary_box = page.locator(".summary-band").bounding_box()
        assert header_box["y"] + header_box["height"] <= summary_box["y"]
        for pill in page.locator(".status-pill").all():
            assert pill.evaluate("node => node.scrollWidth <= node.clientWidth")
        page.locator(".stage-tab").nth(3).click()
        assert (
            page.locator('[data-stage="gold_ready"]')
            .get_attribute("class")
            .endswith("is-focused")
        )
        browser.close()
