"""`retail status` handler (spec 109, roadmap M4, under ratified Option B).

The ONE sanctioned CLI addition under Option B: a thin, READ-ONLY JSON
projection of already-committed readiness state (``mappings/*/readiness-
status.yaml``). Mirrors ``runner.run_json``'s style -- one structured document
on stdout for ``--format json``; ``--format text`` (the default) stays
human-readable and additive. No writes, no DB, no network (B1/B3, FR-004); no
numeric score is ever emitted (Principle V).
"""

from __future__ import annotations

import argparse
import json


def _render_text(projection: dict) -> str:
    """Human-readable rendering: status/evidence/blockers/next_action per table,
    never a score. Mirrors ``demo/report.py``'s render_text posture."""
    tables = projection.get("tables", [])
    if not tables:
        return "retail status: no readiness-status.yaml committed under mappings/."

    lines: list[str] = []
    for table in tables:
        lines.append(f"{table['table']} ({table['source_path']})")
        lines.append(f"  current_stage: {table['current_stage']}")
        for stage_name, stage in table.get("stages", {}).items():
            lines.append(f"  {stage_name}: {stage['status']}")
            for ev in stage.get("evidence", []):
                lines.append(f"    evidence: {ev}")
            for reason in stage.get("blocking_reasons", []):
                lines.append(f"    blocking_reason: {reason}")
        for reason in table.get("blocking_reasons", []):
            lines.append(f"  blocking_reason: {reason}")
        lines.append(f"  next_action: {table['next_action']}")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def status_main(args: argparse.Namespace) -> int:
    """Handler for ``status``. Read-only projection; exit 0 in every case (a
    well-formed empty projection is success, not an error -- FR-004)."""
    from seshat.status_surface import build_status_projection

    projection = build_status_projection(getattr(args, "repo", "."))

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(projection, indent=2))
    else:
        print(_render_text(projection))
    return 0
