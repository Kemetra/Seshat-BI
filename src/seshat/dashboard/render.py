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
        ("إجمالي الجداول", total),
        ("جاهز للنشر", publish_ready),
        ("محظور", blocked),
        ("يحتاج انتباه", needs_attention),
    ]
    inner = "".join(
        f'<div class="card kpi"><div class="label">{_esc(label)}</div>'
        f'<div class="value">{value}</div></div>'
        for label, value in cards
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
            f'<span class="dot" style="background:{fg};" '
            f'title="{_esc(_STAGE_LABELS_AR[name])}"></span>'
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


def _table_card(t: dict) -> str:
    name = t.get("table", t.get("source_path", ""))
    stages = t.get("stages") or {}
    stage_html = []
    for stage_name in _STAGE_ORDER:
        block = stages.get(stage_name) or {}
        status = block.get("status", "not_started")
        fg, bg = _STATUS_STYLE.get(status, _STATUS_STYLE["not_started"])
        evidence = block.get("evidence") or []
        reasons = block.get("blocking_reasons") or []
        ev = ""
        if evidence:
            ev = (
                '<ul class="evidence">'
                + "".join(f"<li>{_esc(e)}</li>" for e in evidence)
                + "</ul>"
            )
        rs = "".join(f'<div class="blocker">{_esc(r)}</div>' for r in reasons)
        stage_html.append(
            f'<div class="stage" style="color:{fg};background:{bg};">'
            f"{_esc(_STAGE_LABELS_AR[stage_name])}<br>{_esc(status)}{ev}{rs}</div>"
        )
    top_blockers = "".join(
        f'<div class="blocker">{_esc(r)}</div>'
        for r in (t.get("blocking_reasons") or [])
    )
    return (
        f'<div class="card" id="table-{_esc(name)}">'
        f"<h3>{_esc(name)} {_chip(t.get('current_stage') or 'not_started')}</h3>"
        f'<div class="meta">{_esc(t.get("source_path") or "")}</div>'
        f'<div class="stepper">{"".join(stage_html)}</div>'
        f"{top_blockers}"
        f'<div class="next">الإجراء التالي: {_esc(t.get("next_action") or "-")}</div>'
        "</div>"
    )


def render_page(projection: dict) -> str:
    """Render the full self-contained dashboard document for ``projection``.

    ``projection`` is the shape returned by
    ``seshat.status_surface.build_status_projection`` — ``{"tables": [...]}``.
    An empty table list renders a friendly empty state, never an error.
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
            f"{_kpis(tables)}"
            f"{_summary_table(tables)}"
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
        '<nav class="nav"><a href="#">الرئيسية</a>'
        '<a href="#tables">الجداول</a></nav></aside>\n'
        f"<main>{body}</main>\n"
        "</div>\n"
        "</body>\n</html>\n"
    )
