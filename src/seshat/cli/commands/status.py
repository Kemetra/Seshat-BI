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


def _render_text(projection: dict, prog: str = "seshat") -> str:
    """Human-readable rendering: status/evidence/blockers/next_action per table,
    never a score. Mirrors ``demo/report.py``'s render_text posture.

    Also states the #485 live-DB provenance limit for any table whose
    silver/gold evidence is ``pass``: this surface reads committed YAML only and
    that evidence carries no machine-checkable database identity, so a `pass`
    cannot be correlated with the currently configured connection. The wording
    is the SAME string `next` emits (``run_next.provenance_caveat_for_stages``),
    never a second sentence for one condition.

    This is the RENDER layer, so it adds no field to the closed
    ``schemas/agent-status.schema.json`` contract and no derived value to
    ``status_surface``'s verbatim projection -- both stay untouched.
    """
    from seshat.run_next import provenance_caveat_for_stages

    tables = projection.get("tables", [])
    if not tables:
        return f"{prog} status: no readiness-status.yaml committed under mappings/."

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
        caveat = provenance_caveat_for_stages(table.get("stages"))
        if caveat is not None:
            lines.append(f"  caveat: {caveat['kind']}: {caveat['detail']}")
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
        print(_render_text(projection, getattr(args, "prog", "seshat")))
    return 0
