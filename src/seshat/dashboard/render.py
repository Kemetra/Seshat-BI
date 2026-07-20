"""Pure renderer: readiness projection dict -> one self-contained HTML string.

Read-only VIEW. No I/O, no socket, no fabricated score (repo hard rule #9):
the only numbers this module emits are integer COUNTS over the projection;
evidence strings (which may contain a literal '%') pass through verbatim and
escaped. Mirrors the escaping posture of seshat.demo.html_report.
"""

from __future__ import annotations

import html

from seshat.dashboard.theme import DASHBOARD_CSS

_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)

_STAGE_LABELS_AR: dict[str, str] = {
    "source_ready": "المصدر",
    "mapping_ready": "التوصيف",
    "silver_ready": "الفضي",
    "gold_ready": "الذهبي",
    "semantic_model_ready": "النموذج الدلالي",
    "dashboard_ready": "لوحة المعلومات",
    "publish_ready": "النشر",
}

# The ONE place status -> (foreground, background tint) lives.
_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "pass": ("#1F8A54", "#E7F3EC"),
    "warning": ("#B5832A", "#FEF4E1"),
    "blocked": ("#C0392B", "#FDECEC"),
    "not_started": ("#6B7480", "#F1F5F9"),
}


# Feather-style inline SVG icons. Inline in the HTML namespace on purpose: NO
# `xmlns` (a URL that would trip the self-contained no-remote-asset gate), no
# `<use>`, no external href — pure path markup only. ``currentColor`` lets each
# icon inherit the colour of its context (nav text, KPI tile, stage status).
_ICON_PATHS: dict[str, str] = {
    # home / project-health
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    # stacked layers — the tables list
    "layers": '<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="M2 17l10 5 10-5"/>'
    '<path d="M2 12l10 5 10-5"/>',
    # totals / grid
    "grid": '<path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>',
    # publish-ready — check
    "check": '<path d="M20 6 9 17l-5-5"/>',
    # blocked — octagon slash
    "block": '<path d="M4.9 4.9 19 19"/>'
    '<path d="M7.9 2h8.2L22 7.9v8.2L16.1 22H7.9L2 16.1V7.9L7.9 2Z"/>',
    # needs attention — alert triangle
    "alert": '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 9v5"/><path d="M12 17h.01"/>',
}


def _icon(name: str) -> str:
    """One inline SVG glyph. Empty string for an unknown name (never raises)."""
    paths = _ICON_PATHS.get(name)
    if not paths:
        return ""
    return (
        '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
    )


def _esc(value: object) -> str:
    """HTML-escape any projection value (defense-in-depth; quote=True)."""
    return html.escape(str(value), quote=True)


def _chip(status: str) -> str:
    fg, bg = _STATUS_STYLE.get(status, _STATUS_STYLE["not_started"])
    return (
        f'<span class="chip" style="color:{fg};background:{bg};">{_esc(status)}</span>'
    )


def _count_blocked(tables: list[dict]) -> int:
    total = 0
    for t in tables:
        stages = t.get("stages") or {}
        any_blocked = any(
            isinstance(s, dict) and s.get("status") == "blocked"
            for s in stages.values()
        )
        if any_blocked or t.get("blocking_reasons"):
            total += 1
    return total


def _kpis(tables: list[dict]) -> str:
    total = len(tables)
    publish_ready = sum(1 for t in tables if t.get("current_stage") == "publish_ready")
    blocked = _count_blocked(tables)
    needs_attention = total - publish_ready
    cards = [
        ("إجمالي الجداول", total, "grid"),
        ("جاهز للنشر", publish_ready, "check"),
        ("محظور", blocked, "block"),
        ("يحتاج انتباه", needs_attention, "alert"),
    ]
    inner = "".join(
        f'<div class="card kpi"><div class="label">{_icon(icon)}{_esc(label)}</div>'
        f'<div class="value">{value}</div></div>'
        for label, value, icon in cards
    )
    return f'<div class="kpis">{inner}</div>'


def _stage_dots(t: dict) -> str:
    stages = t.get("stages") or {}
    dots = []
    for name in _STAGE_ORDER:
        block = stages.get(name) or {}
        status = block.get("status", "not_started")
        fg, _bg = _STATUS_STYLE.get(status, _STATUS_STYLE["not_started"])
        dots.append(
            f'<svg class="dotsvg" width="12" height="12" viewBox="0 0 12 12" '
            f'role="img" aria-label="{_esc(_STAGE_LABELS_AR[name])}">'
            f"<title>{_esc(_STAGE_LABELS_AR[name])}</title>"
            f'<circle cx="6" cy="6" r="6" fill="{fg}"/></svg>'
        )
    return "".join(dots)


def _summary_table(tables: list[dict]) -> str:
    rows = []
    for t in tables:
        name = t.get("table", t.get("source_path", ""))
        rows.append(
            "<tr>"
            f'<td><a class="tealref" href="#table-{_esc(name)}">{_esc(name)}</a></td>'
            f"<td>{_chip(t.get('current_stage') or 'not_started')}</td>"
            f"<td>{_stage_dots(t)}</td>"
            f"<td>{len(t.get('blocking_reasons') or [])}</td>"
            f"<td>{_esc(t.get('next_action') or '')}</td>"
            "</tr>"
        )
    return (
        '<div class="card"><table><thead><tr>'
        "<th>الجدول</th><th>المرحلة الحالية</th><th>المراحل</th>"
        "<th>المعرقلات</th><th>الإجراء التالي</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _evidence_list(evidence: list) -> str:
    if not evidence:
        return ""
    items = "".join(f"<li>{_esc(e)}</li>" for e in evidence)
    return f'<ul class="evidence">{items}</ul>'


def _blockers(reasons: list) -> str:
    return "".join(f'<div class="blocker">{_esc(r)}</div>' for r in reasons)


def _stage_block(stage_name: str, block: dict) -> str:
    status = block.get("status", "not_started")
    fg, bg = _STATUS_STYLE.get(status, _STATUS_STYLE["not_started"])
    ev = _evidence_list(block.get("evidence") or [])
    rs = _blockers(block.get("blocking_reasons") or [])
    return (
        f'<div class="stage" style="color:{fg};background:{bg};">'
        f"{_esc(_STAGE_LABELS_AR[stage_name])}<br>{_esc(status)}{ev}{rs}</div>"
    )


def _table_card(t: dict) -> str:
    name = t.get("table", t.get("source_path", ""))
    stages = t.get("stages") or {}
    stepper = "".join(
        _stage_block(stage_name, stages.get(stage_name) or {})
        for stage_name in _STAGE_ORDER
    )
    top_blockers = _blockers(t.get("blocking_reasons") or [])
    return (
        f'<div class="card" id="table-{_esc(name)}">'
        f"<h3>{_esc(name)} {_chip(t.get('current_stage') or 'not_started')}</h3>"
        f'<div class="meta">{_esc(t.get("source_path") or "")}</div>'
        f'<div class="stepper">{stepper}</div>'
        f"{top_blockers}"
        f'<div class="next">الإجراء التالي: {_esc(t.get("next_action") or "-")}</div>'
        "</div>"
    )


# Fixed governance-reminder copy. The dashboard is a read-only VIEW: it never
# grants approval and never invents a health score — only the human gates do.
_GOVERNANCE_REMINDER: str = (
    "هذه اللوحة عرضٌ للقراءة فقط: الأرقام أعلاه عدٌّ للحقائق المُودعة، "
    "وليست درجات جاهزية مُختَلَقة. الانتقال بين المراحل يتطلّب موافقة بشرية "
    "عند بوابات الحوكمة — لا تمنح هذه الصفحة أي موافقة."
)


def _governance_banner() -> str:
    return f'<div class="banner">{_esc(_GOVERNANCE_REMINDER)}</div>'


def _meta_row(generated_at: str | None) -> str:
    """Render the 'آخر تحديث' row, or nothing when no timestamp is injected.

    ``generated_at`` is the honest process render time, supplied by the impure
    caller (``generate``); the renderer never reads the clock itself. Labeled as
    a render time, not data freshness. ``None`` omits the row entirely so a
    bare ``render_page(projection)`` stays deterministic.
    """
    if not generated_at:
        return ""
    return f'<div class="metarow">آخر تحديث: {_esc(generated_at)}</div>'


def render_page(projection: dict, generated_at: str | None = None) -> str:
    """Render the full self-contained dashboard document for ``projection``.

    ``projection`` is the shape returned by
    ``seshat.status_surface.build_status_projection`` — ``{"tables": [...]}``.
    An empty table list renders a friendly empty state, never an error.

    ``generated_at`` is an optional, caller-supplied render timestamp string.
    When given it is shown as an 'آخر تحديث' meta row (an honest render time,
    not data freshness); when ``None`` the row is omitted and output is
    deterministic. The renderer performs no I/O and never reads the clock.
    """
    tables = projection.get("tables", [])
    if not tables:
        body = (
            '<div class="empty">لا توجد ملفات readiness-status.yaml مُودعة تحت '
            "mappings/.</div>"
        )
    else:
        cards = "".join(
            f'<div style="margin-bottom:22px;">{_table_card(t)}</div>' for t in tables
        )
        body = (
            "<h1>صحة المشروع</h1>"
            '<p class="sub">حالة جاهزية كل جدول عبر مراحل الحوكمة السبع.</p>'
            f"{_meta_row(generated_at)}"
            f"{_kpis(tables)}"
            f"{_summary_table(tables)}"
            f"{_governance_banner()}"
            '<h1 id="tables" style="margin-top:32px;">تفاصيل الجداول</h1>'
            f"{cards}"
        )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ar" dir="rtl">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Seshat BI — لوحة الحالة</title>\n"
        f"<style>{DASHBOARD_CSS}</style>\n"
        "</head>\n<body>\n"
        '<div class="app">\n'
        '<aside class="sidebar"><div class="brand">Seshat<small>BI لوحة الحالة'
        "</small></div>"
        f'<nav class="nav"><a href="#">{_icon("home")}الرئيسية</a>'
        f'<a href="#tables">{_icon("layers")}الجداول</a></nav></aside>\n'
        f"<main>{body}</main>\n"
        "</div>\n"
        "</body>\n</html>\n"
    )
