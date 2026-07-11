"""Portfolio aggregation + deterministic explorer HTML (spec 120, US8).

:func:`build_explorer_projection` extends the shared readiness projection
with navigation-ready evidence states, approval receipts, explicit
input-defect entries for malformed readiness files, and the available metric
lineage read from committed metric contracts. Nothing is inferred: a missing
file renders as missing, a deferred live check as deferred, a malformed file
as an input defect -- never as a pass (FR-045).

:func:`render_explorer_html` renders ONLY that projection document (plus the
packaged CSS/JS/brand assets); it cannot open arbitrary repository files.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

from ..artifact_identity import resolve_within
from ..passport import _approval_receipts
from ..readiness_projection import build_readiness_projection

SCHEMA_VERSION = "1.0"

_STAGE_LABELS = {
    "source_ready": "Source",
    "mapping_ready": "Mapping",
    "silver_ready": "Silver",
    "gold_ready": "Gold",
    "semantic_model_ready": "Semantic Model",
    "dashboard_ready": "Dashboard",
    "publish_ready": "Publish",
}


def _evidence_state(root: Path, reference: str) -> str:
    if reference.startswith("["):
        return "deferred"
    try:
        resolved = resolve_within(root, reference)
    except (ValueError, OSError):
        return "missing"
    return "available" if resolved.is_file() else "missing"


def _defect_entries(root: Path, known_paths: set[str]) -> list[dict[str, Any]]:
    """Malformed readiness files are reported explicitly, never skipped."""
    import yaml  # lazy: keep module import stdlib-light (B1/B3)

    entries: list[dict[str, Any]] = []
    mappings = root / "mappings"
    if not mappings.is_dir():
        return entries
    for status_path in sorted(mappings.glob("*/readiness-status.yaml")):
        relative = status_path.relative_to(root).as_posix()
        if relative in known_paths:
            continue
        message = "readiness-status.yaml is not an interpretable mapping"
        try:
            parsed = yaml.safe_load(status_path.read_text(encoding="utf-8-sig"))
            if isinstance(parsed, dict):
                continue  # readable but skipped upstream for another reason
        except (OSError, UnicodeDecodeError):
            message = "readiness-status.yaml is unreadable"
        except yaml.YAMLError:
            message = "readiness-status.yaml is not valid YAML"
        entries.append(
            {
                "table_id": status_path.parent.name,
                "source_path": relative,
                "input_defect": message,
                "stages": {},
            }
        )
    return entries


def _lineage(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Available metric lineage from committed contracts; never inferred."""
    import yaml  # lazy: keep module import stdlib-light (B1/B3)

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    mappings = root / "mappings"
    if not mappings.is_dir():
        return {"nodes": [], "edges": []}
    for contract_path in sorted(mappings.glob("*/metrics/*.yaml")):
        relative = contract_path.relative_to(root).as_posix()
        table = contract_path.parents[1].name
        try:
            document = yaml.safe_load(contract_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            document = None
        if not isinstance(document, dict):
            nodes.setdefault(
                f"defect:{relative}",
                {
                    "node_id": f"defect:{relative}",
                    "kind": "input_defect",
                    "label": f"unreadable metric contract: {relative}",
                    "evidence": relative,
                },
            )
            continue
        name = str(document.get("name") or contract_path.stem)
        metric_id = f"metric:{table}:{name}"
        nodes.setdefault(
            metric_id,
            {
                "node_id": metric_id,
                "kind": "metric_contract",
                "label": name,
                "evidence": relative,
            },
        )
        binds_to = document.get("binds_to")
        if isinstance(binds_to, dict) and binds_to.get("gold_table"):
            gold_table = str(binds_to["gold_table"])
            gold_id = f"warehouse:{gold_table}"
            nodes.setdefault(
                gold_id,
                {
                    "node_id": gold_id,
                    "kind": "warehouse_table",
                    "label": gold_table,
                    "evidence": relative,
                },
            )
            edges.append(
                {
                    "from": metric_id,
                    "to": gold_id,
                    "relation": "binds_to",
                    "evidence": relative,
                }
            )
    return {"nodes": sorted(nodes.values(), key=lambda n: n["node_id"]), "edges": edges}


def build_explorer_projection(repo_root: Path | str = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    base = build_readiness_projection(root)
    tables: list[dict[str, Any]] = []
    known_paths: set[str] = set()
    for table in base["tables"]:
        known_paths.add(table["source_path"])
        stages = {
            stage: {
                "status": block["status"],
                "evidence": [
                    {
                        "reference": str(reference),
                        "state": _evidence_state(root, str(reference)),
                    }
                    for reference in block["evidence"]
                ],
                "blocking_reasons": block["blocking_reasons"],
            }
            for stage, block in table["stages"].items()
        }
        tables.append(
            {
                "table_id": table["table_id"],
                "source_path": table["source_path"],
                "current_stage": table["current_stage"],
                "stages": stages,
                "blocking_reasons": table["blocking_reasons"],
                "next_action": table["next_action"],
                "forbidden_scope": table["forbidden_scope"],
                "approvals": _approval_receipts(root, table["source_path"]),
            }
        )
    tables.extend(_defect_entries(root, known_paths))
    tables.sort(key=lambda entry: entry["table_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": base["workspace"],
        "tables": tables,
        "lineage": _lineage(root),
        "generated_at": None,
        "disclosure": base["disclosure"],
    }


# --- rendering ---------------------------------------------------------------


def _asset_text(name: str) -> str:
    return Path(__file__).with_name("assets").joinpath(name).read_text(encoding="utf-8")


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _brand_img(repo: Path) -> str:
    from ..demo.fixtures import packaged_brand_asset

    try:
        encoded = base64.b64encode(packaged_brand_asset(repo).read_bytes()).decode(
            "ascii"
        )
    except OSError:
        return ""
    return (
        f'<img src="data:image/svg+xml;base64,{encoded}" '
        'alt="Seshat BI seven-point readiness star">'
    )


def _evidence_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">No evidence recorded</p>'
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
        defect = "input_defect" in table
        status = "defect" if defect else "table"
        buttons.append(
            f'<button class="table-tab status-{status}" type="button" '
            f'data-table-target="{_escape(table["table_id"])}">'
            f'<span class="table-name">{_escape(table["table_id"])}</span>'
            f"<span class='table-stage'>"
            f"{_escape(table.get('current_stage') or 'input defect')}</span>"
            "</button>"
        )
    return "".join(buttons)


def _stage_matrix(table: dict[str, Any]) -> str:
    cells = []
    for stage, label in _STAGE_LABELS.items():
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


def _approvals_timeline(approvals: list[dict[str, Any]]) -> str:
    if not approvals:
        return '<p class="empty">No approval receipts recorded</p>'
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


def _stage_details(table: dict[str, Any]) -> str:
    sections = []
    for stage, label in _STAGE_LABELS.items():
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
            f"<div><h5>Evidence</h5>{_evidence_list(block['evidence'])}</div>"
            "<div><h5>Blocking reasons</h5>"
            f"{_plain_list(block['blocking_reasons'], 'No blockers recorded')}</div>"
            "</div></section>"
        )
    return "".join(sections)


def _table_panels(tables: list[dict[str, Any]]) -> str:
    panels = []
    for table in tables:
        if "input_defect" in table:
            panels.append(
                f'<article class="table-card is-defect" '
                f'data-table="{_escape(table["table_id"])}">'
                f"<h2>{_escape(table['table_id'])}</h2>"
                f'<p class="defect">Input defect: {_escape(table["input_defect"])} '
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
            f"<div><h3>Next allowed action</h3><p>{_escape(next_action)}</p></div>"
            "<div><h3>Approvals</h3>"
            f"{_approvals_timeline(table.get('approvals', []))}</div>"
            "</div>"
            f"{_stage_details(table)}"
            "</article>"
        )
    return "".join(panels)


def _lineage_section(lineage: dict[str, Any]) -> str:
    nodes = lineage.get("nodes", [])
    edges = lineage.get("edges", [])
    if not nodes:
        return (
            '<section class="lineage"><h2>Metric lineage</h2>'
            '<p class="empty">No metric lineage is recorded in committed '
            "artifacts.</p></section>"
        )
    labels = {node["node_id"]: node["label"] for node in nodes}
    rows = [
        "<li>"
        f"<strong>{_escape(labels.get(edge['from'], edge['from']))}</strong>"
        f" {_escape(edge['relation'])} "
        f"<strong>{_escape(labels.get(edge['to'], edge['to']))}</strong>"
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
        '<section class="lineage"><h2>Metric lineage</h2>'
        f'<ul class="lineage-edges">{"".join(rows + defects)}</ul></section>'
    )


def render_explorer_html(projection: dict[str, Any], *, repo: Path) -> str:
    css = _asset_text("explorer.css")
    javascript = _asset_text("explorer.js")
    workspace = projection["workspace"]
    revision = workspace.get("source_revision")
    revision_label = revision[:12] if isinstance(revision, str) else "unrecorded"
    tables = projection["tables"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Seshat BI - Readiness explorer</title>
  <style>{css}</style>
</head>
<body>
  <header class="product-header">
    {_brand_img(repo)}
    <div><p class="product-name">Seshat BI</p><h1>Readiness explorer</h1></div>
    <span class="mode-badge">offline snapshot</span>
  </header>
  <main>
    <section class="summary-band">
      <div>
        <p class="eyebrow">Workspace</p>
        <h2>{_escape(workspace.get("label"))}</h2>
      </div>
      <div>
        <p class="eyebrow">Source revision</p>
        <p class="revision">{_escape(revision_label)}</p>
      </div>
      <div>
        <p class="eyebrow">Tables</p>
        <p class="revision">{len(tables)}</p>
      </div>
    </section>
    <nav class="table-rail" aria-label="Tables">{_table_nav(tables)}</nav>
    <div class="table-list">{_table_panels(tables)}</div>
    {_lineage_section(projection["lineage"])}
  </main>
  <footer>
    <span>Generated from committed evidence only</span>
    <span>No readiness score; no inferred pass</span>
  </footer>
  <script>{javascript}</script>
</body>
</html>
"""
