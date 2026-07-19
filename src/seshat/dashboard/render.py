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
        body = "<div>tables placeholder</div>"  # replaced in Task 3
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ar" dir="rtl">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Seshat BI — لوحة الحالة</title>\n"
        f"<style>{DASHBOARD_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )
