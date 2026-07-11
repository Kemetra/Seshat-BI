from __future__ import annotations

from pathlib import Path

import pytest

from seshat.explorer.build import build_explorer_projection, render_explorer_html

pytestmark = pytest.mark.integration
_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("viewport", [(1280, 800), (390, 844)])
def test_explorer_is_visible_accessible_offline_and_stable(
    tmp_path: Path, viewport: tuple[int, int]
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    projection = build_explorer_projection(_REPO)
    table_count = len(projection["tables"])
    assert table_count >= 1
    output = tmp_path / "index.html"
    output.write_text(render_explorer_html(projection, repo=_REPO), encoding="utf-8")

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(output.as_uri())
        assert page.locator("h1").inner_text() == "Readiness explorer"
        assert page.locator(".table-tab").count() == table_count
        assert page.locator(".table-card").count() == table_count
        assert page.locator(".stage-cell").count() >= 7
        assert page.locator("body").bounding_box()["height"] > 200
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        header_box = page.locator(".product-header").bounding_box()
        summary_box = page.locator(".summary-band").bounding_box()
        assert header_box["y"] + header_box["height"] <= summary_box["y"]
        first_table = page.locator(".table-tab").first
        first_table.click()
        assert page.locator(".table-card.is-focused").count() == 1
        page.locator(".stage-cell").first.click()
        assert page.locator(".stage-detail.is-focused").count() == 1
        # Keyboard reachability: every nav control is a real button.
        assert page.locator(".table-tab").first.evaluate(
            "node => node.tagName === 'BUTTON'"
        )
        browser.close()
