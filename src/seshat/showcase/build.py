"""Read-only composition + rendering for the shareable showcase bundle.

Spec 127 (Shareable Seshat Proof). This module is a composition/rendering
layer over ALREADY-SHIPPED surfaces: it reads
``seshat.explorer.build.build_explorer_projection`` for stages, evidence
states, blockers, approvals, next actions, and metric lineage; it optionally
reads two Passport snapshots via ``seshat.showcase.compare`` (which reuses
``seshat.passport.verify_passport``); it derives a truthful badge
(``seshat.showcase.badge``) and a four-category disclosure manifest
(``seshat.showcase.manifest``); then it runs the shipped fail-closed
disclosure scan (``seshat.disclosure.scan_disclosure``) over the FULL
composed body -- tables, enriched lineage, approvals, badge, manifest, and
any comparison -- merged with the base projection's invariant findings
(pass-without-evidence / blocked-without-reason).

Pipeline order (FR-009/FR-010, INV-4): compose -> normalize/redact (portable
paths + private URLs) -> scan the full composed body -> fail-closed. Nothing
is recomputed: no readiness engine, no new evidence schema, no new Explorer,
no new Passport (FR-001/FR-002). This module and its render function are
read-only with respect to every source artifact (FR-004) and do not modify
the shipped Explorer assets (FR-025).
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

from ..disclosure import scan_disclosure
from ..explorer.build import build_explorer_projection
from .badge import STAGE_LABELS, STAGE_ORDER, build_badge
from .compare import build_comparison
from .manifest import (
    build_manifest,
    find_residual_absolute_paths,
    normalize_portability,
)

SCHEMA_VERSION = "1.0"

_INVARIANT_RULES = frozenset(
    {"projection_pass_without_evidence", "projection_blocked_without_reason"}
)


def _carry_invariant_findings(
    projection_disclosure: dict[str, Any],
) -> list[dict[str, str]]:
    """Reuse (never recompute) the base projection's invariant findings --
    these live only in ``build_readiness_projection`` and would be lost by a
    naive re-scan of the enriched showcase body (research.md R2)."""
    return [
        finding
        for finding in projection_disclosure.get("findings", [])
        if finding.get("rule") in _INVARIANT_RULES
    ]


def build_showcase_bundle(
    repo_root: Path | str = ".",
    *,
    snapshots: tuple[Any, Any] | None = None,
) -> dict[str, Any]:
    """Compose the showcase bundle document (see data-model.md ShowcaseBundle).

    Read-only: no source artifact, readiness status, database, or Power BI
    model is written or mutated. ``disclosure`` is the scan of the FULL
    composed body, never a carry-through of the Explorer projection's own
    (narrower) disclosure result.
    """
    root = Path(repo_root).resolve()
    projection = build_explorer_projection(root)

    comparison_raw = build_comparison(root, snapshots) if snapshots else None
    brand_asset_svg, brand_asset_ok = _load_brand_asset_text(root)

    normalized, redactions = normalize_portability(
        root,
        {
            "tables": projection["tables"],
            "lineage": projection["lineage"],
            "comparison": comparison_raw,
            # Routed through the SAME normalize_portability pass as
            # everything else (not scanned separately) so a private/
            # internal URL embedded in the brand SVG is stripped exactly
            # like one anywhere else in the composed body -- scan_disclosure
            # itself has no private-URL rule; that coverage lives only in
            # this normalization step.
            "brand_asset_svg": brand_asset_svg or "",
        },
    )
    tables = normalized["tables"]
    lineage = normalized["lineage"]
    comparison = normalized["comparison"]
    brand_asset_svg = normalized["brand_asset_svg"]

    badge = build_badge(tables)
    manifest = build_manifest(tables, lineage, redactions)

    composed_body = {
        "schema_version": SCHEMA_VERSION,
        "workspace": projection["workspace"],
        "tables": tables,
        "lineage": lineage,
        "badge": badge,
        "manifest": manifest,
        "comparison": comparison,
        # Scanned as TEXT here, before rendering, so the exact bytes the
        # rendered HTML embeds are the exact bytes the fail-closed scan
        # inspected -- render_showcase_html reads this field, never the
        # workspace file directly (closes the brand-asset disclosure gap).
        "brand_asset_svg": brand_asset_svg,
    }

    disclosure = scan_disclosure(composed_body)
    extra_findings = [
        *_carry_invariant_findings(projection["disclosure"]),
        *find_residual_absolute_paths(composed_body),
    ]
    if not brand_asset_ok:
        extra_findings.append(
            {
                "rule": "showcase_brand_asset_unreadable",
                "locator": "$.brand_asset_svg",
                "message": (
                    "the brand asset could not be read or parsed for the "
                    "disclosure scan"
                ),
            }
        )
    if extra_findings:
        disclosure = {
            **disclosure,
            "status": "blocked",
            "findings": [*disclosure["findings"], *extra_findings],
        }

    return {**composed_body, "disclosure": disclosure, "generated_at": None}


# --- rendering ---------------------------------------------------------------

_LABELS = {
    "en": {
        "product_name": "Seshat BI",
        "title": "Shareable readiness proof",
        "mode": "offline snapshot",
        "workspace": "Workspace",
        "revision": "Source revision",
        "tables": "Tables",
        "badge_caption": "Readiness badge",
        "next_action": "Next allowed action",
        "approvals": "Approvals",
        "evidence": "Evidence",
        "blocking_reasons": "Blocking reasons",
        "lineage": "Metric lineage",
        "no_lineage": "No metric lineage is recorded in committed artifacts.",
        "manifest": "Disclosure manifest",
        "included": "Included",
        "unavailable": "Unavailable",
        "omitted": "Omitted",
        "redacted": "Redacted",
        "comparison": "Before / after",
        "comparison_omitted": "Before/after is omitted:",
        "footer_local": (
            "Local offline snapshot of evidence files as on disk "
            "(may include uncommitted changes)."
        ),
        "footer_publish": (
            "Publishing this bundle is a separate, explicit human action."
        ),
        "no_evidence": "No evidence recorded",
        "no_blockers": "No blockers recorded",
        "no_approvals": "No approval receipts recorded",
        "no_manifest_entries": "None recorded",
        "input_defect": "Input defect",
    },
    "ar": {
        "product_name": "Seshat BI",
        "title": "دليل جاهزية قابل للمشاركة",
        "mode": "لقطة غير متصلة",
        "workspace": "بيئة العمل",
        "revision": "إصدار المصدر",
        "tables": "الجداول",
        "badge_caption": "شارة الجاهزية",
        "next_action": "الإجراء التالي المسموح به",
        "approvals": "الموافقات",
        "evidence": "الأدلة",
        "blocking_reasons": "أسباب الحظر",
        "lineage": "تتبع المقاييس",
        "no_lineage": "لا يوجد تتبع مقاييس مسجل في الملفات الموثقة.",
        "manifest": "بيان الإفصاح",
        "included": "مُدرَج",
        "unavailable": "غير متاح",
        "omitted": "محذوف",
        "redacted": "مُنقَّح",
        "comparison": "قبل / بعد",
        "comparison_omitted": "تم حذف قسم قبل/بعد:",
        "footer_local": (
            "لقطة محلية غير متصلة من ملفات الأدلة كما هي على القرص "
            "(قد تشمل تغييرات لم تُلتزم بعد)."
        ),
        "footer_publish": "نشر هذه الحزمة إجراء بشري صريح ومنفصل.",
        "no_evidence": "لا توجد أدلة مسجلة",
        "no_blockers": "لا توجد عوائق مسجلة",
        "no_approvals": "لا توجد إيصالات موافقة مسجلة",
        "no_manifest_entries": "لا شيء مسجل",
        "input_defect": "خلل في المدخلات",
    },
}


def _asset_text(name: str) -> str:
    return Path(__file__).with_name("assets").joinpath(name).read_text(encoding="utf-8")


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _load_brand_asset_text(root: Path) -> tuple[str | None, bool]:
    """Read the brand asset as TEXT so it can be included in the disclosure-
    scanned composed body, rather than re-reading raw bytes from the
    workspace at render time (which would bypass the fail-closed scan).
    Returns ``(text, ok)``; unreadable/non-UTF-8 content is ``(None, False)``
    -- a fail-closed finding, never a silent skip."""
    from ..demo.fixtures import packaged_brand_asset

    try:
        return packaged_brand_asset(root).read_text(encoding="utf-8"), True
    except (OSError, UnicodeDecodeError):
        return None, False


def _brand_img(bundle: dict[str, Any]) -> str:
    svg_text = bundle.get("brand_asset_svg")
    if not svg_text:
        return ""
    encoded = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    return (
        f'<img src="data:image/svg+xml;base64,{encoded}" '
        'alt="Seshat BI seven-point readiness star">'
    )


def _evidence_list(items: list[dict[str, Any]], labels: dict[str, str]) -> str:
    if not items:
        return f'<p class="empty">{_escape(labels["no_evidence"])}</p>'
    rows = []
    for item in items:
        state = _escape(item["state"])
        rows.append(
            f'<li class="evidence-{state}">{_escape(item["reference"])}'
            f'<span class="evidence-state">{state}</span></li>'
        )
    return f"<ul>{''.join(rows)}</ul>"


def _plain_list(items: list[object], empty: str) -> str:
    if not items:
        return f'<p class="empty">{_escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ul>"


def _table_nav(tables: list[dict[str, Any]]) -> str:
    buttons = []
    for table in tables:
        status = "defect" if "input_defect" in table else "table"
        buttons.append(
            f'<button class="table-tab status-{status}" type="button" '
            f'data-table-target="{_escape(table["table_id"])}">'
            f'<span class="table-name">{_escape(table["table_id"])}</span>'
            "<span class='table-stage'>"
            f"{_escape(table.get('current_stage') or 'input defect')}</span>"
            "</button>"
        )
    return "".join(buttons)


def _stage_matrix(table: dict[str, Any]) -> str:
    cells = []
    for stage in STAGE_ORDER:
        label = STAGE_LABELS[stage]
        block = table["stages"].get(stage)
        status = block["status"] if block else "not_started"
        cells.append(
            f'<button class="stage-cell status-{_escape(status)}" type="button" '
            f'data-stage-target="{_escape(table["table_id"])}:{_escape(stage)}">'
            f'<span class="stage-label">{_escape(label)}</span>'
            f'<span class="status-label">{_escape(status.replace("_", " "))}</span>'
            "</button>"
        )
    return f'<div class="stage-matrix">{"".join(cells)}</div>'


def _approvals_timeline(approvals: list[dict[str, Any]], labels: dict[str, str]) -> str:
    if not approvals:
        return f'<p class="empty">{_escape(labels["no_approvals"])}</p>'
    rows = []
    for receipt in approvals:
        shape = "" if receipt.get("valid_shape") else " (invalid shape)"
        rows.append(
            "<li>"
            f"<strong>{_escape(receipt.get('stage'))}</strong> "
            f"{_escape(receipt.get('owner'))} "
            f"<small>{_escape(receipt.get('at') or 'no date recorded')}{shape}</small>"
            "</li>"
        )
    return f'<ul class="approvals">{"".join(rows)}</ul>'


def _stage_details(table: dict[str, Any], labels: dict[str, str]) -> str:
    sections = []
    for stage in STAGE_ORDER:
        label = STAGE_LABELS[stage]
        block = table["stages"].get(stage)
        if block is None:
            continue
        status = _escape(block["status"])
        sections.append(
            f'<section class="stage-detail" '
            f'data-stage="{_escape(table["table_id"])}:{_escape(stage)}">'
            f"<h4>{_escape(label)} "
            f'<span class="status-pill status-{status}">'
            f"{_escape(block['status'].replace('_', ' '))}</span></h4>"
            '<div class="stage-columns">'
            f"<div><h5>{_escape(labels['evidence'])}</h5>"
            f"{_evidence_list(block['evidence'], labels)}</div>"
            f"<div><h5>{_escape(labels['blocking_reasons'])}</h5>"
            f"{_plain_list(block['blocking_reasons'], labels['no_blockers'])}</div>"
            "</div></section>"
        )
    return "".join(sections)


def _table_panels(tables: list[dict[str, Any]], labels: dict[str, str]) -> str:
    panels = []
    for table in tables:
        if "input_defect" in table:
            panels.append(
                f'<article class="table-card is-defect" '
                f'data-table="{_escape(table["table_id"])}">'
                f"<h2>{_escape(table['table_id'])}</h2>"
                f'<p class="defect">{_escape(labels["input_defect"])}: '
                f"{_escape(table['input_defect'])} "
                f"({_escape(table['source_path'])})</p></article>"
            )
            continue
        next_action = table.get("next_action") or "No next action recorded."
        panels.append(
            f'<article class="table-card" data-table="{_escape(table["table_id"])}">'
            f"<h2>{_escape(table['table_id'])}</h2>"
            f'<p class="source-path">{_escape(table["source_path"])}</p>'
            f"{_stage_matrix(table)}"
            '<div class="table-meta">'
            f"<div><h3>{_escape(labels['next_action'])}</h3>"
            f"<p>{_escape(next_action)}</p></div>"
            f"<div><h3>{_escape(labels['approvals'])}</h3>"
            f"{_approvals_timeline(table.get('approvals', []), labels)}</div>"
            "</div>"
            f"{_stage_details(table, labels)}"
            "</article>"
        )
    return "".join(panels)


def _lineage_section(lineage: dict[str, Any], labels: dict[str, str]) -> str:
    nodes = lineage.get("nodes", [])
    edges = lineage.get("edges", [])
    if not nodes:
        return (
            f'<section class="lineage"><h2>{_escape(labels["lineage"])}</h2>'
            f'<p class="empty">{_escape(labels["no_lineage"])}</p></section>'
        )
    node_labels = {node["node_id"]: node["label"] for node in nodes}
    rows = [
        "<li>"
        f"<strong>{_escape(node_labels.get(edge['from'], edge['from']))}</strong>"
        f" {_escape(edge['relation'])} "
        f"<strong>{_escape(node_labels.get(edge['to'], edge['to']))}</strong>"
        f'<small class="lineage-evidence">{_escape(edge["evidence"])}</small>'
        "</li>"
        for edge in edges
    ]
    defects = [
        f'<li class="defect">{_escape(node["label"])}</li>'
        for node in nodes
        if node["kind"] == "input_defect"
    ]
    return (
        f'<section class="lineage"><h2>{_escape(labels["lineage"])}</h2>'
        f'<ul class="lineage-edges">{"".join(rows + defects)}</ul></section>'
    )


def _manifest_column(
    heading: str, entries: list[dict[str, Any]], labels: dict[str, str]
) -> str:
    if not entries:
        body = f'<p class="empty">{_escape(labels["no_manifest_entries"])}</p>'
    else:
        rows = []
        for entry in entries:
            reason = _escape(entry.get("reason", ""))
            locator = _escape(entry.get("locator", ""))
            rows.append(f"<li><code>{locator}</code><span>{reason}</span></li>")
        body = f"<ul>{''.join(rows)}</ul>"
    return f'<div class="manifest-column"><h3>{_escape(heading)}</h3>{body}</div>'


def _manifest_section(manifest: dict[str, Any], labels: dict[str, str]) -> str:
    columns = "".join(
        [
            _manifest_column(labels["included"], manifest.get("included", []), labels),
            _manifest_column(
                labels["unavailable"], manifest.get("unavailable", []), labels
            ),
            _manifest_column(labels["omitted"], manifest.get("omitted", []), labels),
            _manifest_column(labels["redacted"], manifest.get("redacted", []), labels),
        ]
    )
    return (
        f'<section class="manifest"><h2>{_escape(labels["manifest"])}</h2>'
        f'<div class="manifest-grid">{columns}</div></section>'
    )


def _comparison_section(
    comparison: dict[str, Any] | None, labels: dict[str, str]
) -> str:
    if comparison is None:
        return ""
    if not comparison.get("comparable"):
        reason = comparison.get("omitted_reason") or "snapshots are not comparable"
        return (
            f'<section class="comparison"><h2>{_escape(labels["comparison"])}</h2>'
            f'<p class="empty">{_escape(labels["comparison_omitted"])} '
            f"{_escape(reason)}</p></section>"
        )
    transitions = comparison.get("stage_transitions", [])
    verdicts = comparison.get("evidence_verdicts", [])
    transition_rows = "".join(
        "<li>"
        f"<strong>{_escape(item['table_id'])}</strong> {_escape(item['stage'])}: "
        f"{_escape(item['before_status'])} -&gt; {_escape(item['after_status'])}"
        "</li>"
        for item in transitions
    )
    verdict_rows = "".join(
        f"<li><code>{_escape(item['path'])}</code>: {_escape(item['verdict'])}</li>"
        for item in verdicts
    )
    before_rev = comparison.get("before_revision") or "unrecorded"
    after_rev = comparison.get("after_revision") or "unrecorded"
    return (
        f'<section class="comparison"><h2>{_escape(labels["comparison"])}</h2>'
        f'<p class="revision">{_escape(before_rev)} -&gt; {_escape(after_rev)}</p>'
        f'<div class="comparison-columns">'
        f"<div><h5>Stage transitions</h5>"
        f"<ul>{transition_rows or '<li>No stage transitions observed.</li>'}</ul></div>"
        f"<div><h5>Evidence verdicts</h5>"
        f"<ul>{verdict_rows or '<li>No artifact identities recorded.</li>'}</ul></div>"
        "</div></section>"
    )


def render_showcase_html(
    bundle: dict[str, Any], *, repo: Path, rtl: bool = False
) -> str:
    """Render the self-contained offline showcase bundle HTML.

    Reads only ``bundle`` (the ``build_showcase_bundle`` output, which
    already carries the brand asset as already-disclosure-scanned text
    under ``bundle["brand_asset_svg"]``); it never opens the brand asset or
    any other repository file itself at render time. Inlines its OWN
    ``showcase.css`` / ``showcase.js`` -- it does not read or modify
    ``explorer.css`` / ``explorer.js`` (FR-025). ``repo`` is accepted for
    interface stability but is not read by this function.
    """
    labels = _LABELS["ar" if rtl else "en"]
    css = _asset_text("showcase.css")
    javascript = _asset_text("showcase.js")
    workspace = bundle["workspace"]
    revision = workspace.get("source_revision")
    revision_label = revision[:12] if isinstance(revision, str) else "unrecorded"
    tables = bundle["tables"]
    badge = bundle["badge"]
    dir_attr = "rtl" if rtl else "ltr"
    lang_attr = "ar" if rtl else "en"
    return f"""<!doctype html>
<html lang="{lang_attr}" dir="{dir_attr}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(labels["product_name"])} - {_escape(labels["title"])}</title>
  <style>{css}</style>
</head>
<body>
  <header class="product-header">
    {_brand_img(bundle)}
    <div><p class="product-name">{_escape(labels["product_name"])}</p>
    <h1>{_escape(labels["title"])}</h1></div>
    <span class="mode-badge">{_escape(labels["mode"])}</span>
  </header>
  <main>
    <section class="summary-band">
      <div>
        <p class="eyebrow">{_escape(labels["workspace"])}</p>
        <h2>{_escape(workspace.get("label"))}</h2>
      </div>
      <div>
        <p class="eyebrow">{_escape(labels["revision"])}</p>
        <p class="revision">{_escape(revision_label)}</p>
      </div>
      <div>
        <p class="eyebrow">{_escape(labels["tables"])}</p>
        <p class="revision">{len(tables)}</p>
      </div>
    </section>
    <section class="badge-card">
      <p class="eyebrow">{_escape(labels["badge_caption"])}</p>
      {badge["svg"]}
      <p class="badge-label">{_escape(badge["label"])}</p>
    </section>
    <nav class="table-rail" aria-label="{_escape(labels["tables"])}">
      {_table_nav(tables)}
    </nav>
    <div class="table-list">{_table_panels(tables, labels)}</div>
    {_lineage_section(bundle["lineage"], labels)}
    {_manifest_section(bundle["manifest"], labels)}
    {_comparison_section(bundle.get("comparison"), labels)}
  </main>
  <footer>
    <span>{_escape(labels["footer_local"])}</span>
    <span>{_escape(labels["footer_publish"])}</span>
  </footer>
  <script>{javascript}</script>
</body>
</html>
"""
