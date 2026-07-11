"""Deterministic static HTML renderer for the truthful offline demo proof."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

from .fixtures import packaged_brand_asset
from .report import _STAGE_ORDER, _approval_for, _is_illustrative

_STAGE_LABELS = {
    "source_ready": "Source",
    "mapping_ready": "Mapping",
    "silver_ready": "Silver",
    "gold_ready": "Gold",
    "semantic_model_ready": "Semantic Model",
    "dashboard_ready": "Dashboard",
    "publish_ready": "Publish",
}


def _asset_text(name: str) -> str:
    return Path(__file__).with_name("assets").joinpath(name).read_text(encoding="utf-8")


def _brand_data_uri(repo: Path) -> str:
    encoded = base64.b64encode(packaged_brand_asset(repo).read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _list(items: list[object], empty: str) -> str:
    if not items:
        return f'<p class="empty">{_escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ul>"


def _stage_nav(snapshot: dict[str, Any]) -> str:
    stages = snapshot.get("stages", {})
    items: list[str] = []
    for index, name in enumerate(_STAGE_ORDER, start=1):
        block = stages.get(name, {})
        status = block.get("status", "not_started")
        items.append(
            f'<button class="stage-tab status-{_escape(status)}" '
            f'data-stage-target="{_escape(name)}" type="button">'
            f'<span class="stage-number">{index}</span>'
            f'<span class="stage-label">{_escape(_STAGE_LABELS[name])}</span>'
            f'<span class="status-label">{_escape(status.replace("_", " "))}</span>'
            "</button>"
        )
    return "".join(items)


def _stage_sections(snapshot: dict[str, Any]) -> str:
    stages = snapshot.get("stages", {})
    sections: list[str] = []
    for index, name in enumerate(_STAGE_ORDER, start=1):
        block = stages.get(name, {})
        status = str(block.get("status", "not_started"))
        approval = _approval_for(snapshot, name)
        approval_html = ""
        if approval is not None:
            note = (
                "Illustrative fixture, not produced by this run"
                if _is_illustrative(approval)
                else "Recorded approval receipt"
            )
            approval_html = (
                '<div class="approval-row"><span>Approval</span>'
                f"<strong>{_escape(approval.get('owner', 'unknown'))}</strong>"
                f"<small>{_escape(note)}</small></div>"
            )
        stage_label = _escape(_STAGE_LABELS[name])
        status_label = _escape(status.replace("_", " "))
        blocker_list = _list(
            list(block.get("blocking_reasons") or []), "No blockers recorded"
        )
        sections.append(
            f'<section class="stage-detail" data-stage="{_escape(name)}">'
            '<div class="stage-heading">'
            f'<span class="stage-index">{index:02d}</span>'
            "<div>"
            f'<p class="stage-kicker">Readiness stage</p><h2>{stage_label}</h2>'
            "</div>"
            f'<span class="status-pill status-{_escape(status)}">{status_label}</span>'
            "</div>"
            '<div class="stage-columns">'
            "<div><h3>Evidence</h3>"
            f"{_list(list(block.get('evidence') or []), 'No evidence recorded')}</div>"
            "<div><h3>Blocking reasons</h3>"
            f"{blocker_list}</div>"
            "</div>"
            f"{approval_html}</section>"
        )
    return "".join(sections)


def render_html(snapshot: dict[str, Any], *, repo: Path) -> str:
    mode = "live" if snapshot.get("live_reachable") else "offline"
    table = snapshot.get("table") or "demo_sample_orders"
    next_action = snapshot.get("next_action") or "No next action recorded."
    css = _asset_text("demo.css")
    javascript = _asset_text("demo.js")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Seshat BI - Readiness proof</title>
  <style>{css}</style>
</head>
<body>
  <header class="product-header">
    <img src="{_brand_data_uri(repo)}" alt="Seshat BI seven-point readiness star">
    <div><p class="product-name">Seshat BI</p><h1>Readiness proof</h1></div>
    <span class="mode-badge">{_escape(mode)} mode</span>
  </header>
  <main>
    <section class="summary-band" aria-labelledby="summary-title">
      <div>
        <p class="eyebrow">Table</p>
        <h2 id="summary-title">{_escape(table)}</h2>
      </div>
      <div class="next-action">
        <p class="eyebrow">Next allowed action</p>
        <p>{_escape(next_action)}</p>
      </div>
    </section>
    <nav class="stage-rail" aria-label="Readiness stages">{_stage_nav(snapshot)}</nav>
    <div class="stage-list">{_stage_sections(snapshot)}</div>
  </main>
  <footer>
    <span>Generated from committed evidence</span><span>No readiness score</span>
  </footer>
  <script>{javascript}</script>
</body>
</html>
"""
