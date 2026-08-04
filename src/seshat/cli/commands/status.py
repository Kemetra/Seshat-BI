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


def _table_dir(source_path: object) -> str | None:
    """The ``mappings/<dir>/`` name from a projected ``source_path``.

    The provenance record is a SIBLING of the readiness file, so its directory is
    the projection's own path -- never re-derived from the table name, which may
    be schema-qualified and need not equal the directory.
    """
    if not isinstance(source_path, str) or not source_path:
        return None
    parts = source_path.replace("\\", "/").split("/")
    return parts[-2] if len(parts) >= 2 else None


def _render_text(
    projection: dict, prog: str = "seshat", repo_root: object = "."
) -> str:
    """Human-readable rendering: status/evidence/blockers/next_action per table,
    never a score. Mirrors ``demo/report.py``'s render_text posture.

    Also qualifies the live-DB provenance of any table whose silver/gold evidence
    is ``pass`` (#485). With an A2 record present the line states whether the
    recorded database identity MATCHES the configured connection, or names the
    ``stale_evidence_wrong_database`` disagreement; with none present it states
    the legacy limit -- that committed evidence carries no machine-checkable
    database identity, so a `pass` cannot be correlated with the current
    connection. Every wording is the SAME string `next` emits
    (``run_next.provenance_caveat_for_stages``), never a second sentence for one
    condition.

    Still no DB and no network: the comparison reads the committed record and the
    configured DSN string, exactly as `next` does.

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
        caveat = provenance_caveat_for_stages(
            table.get("stages"), repo_root, _table_dir(table.get("source_path"))
        )
        if caveat is not None:
            lines.append(f"  caveat: {caveat['kind']}: {caveat['detail']}")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def status_main(args: argparse.Namespace) -> int:
    """Handler for ``status``. Read-only projection; exit 0 in every case (a
    well-formed empty projection is success, not an error -- FR-004)."""
    from seshat.status_surface import build_status_projection

    projection = build_status_projection(
        getattr(args, "repo", "."),
        include_coverage=bool(getattr(args, "coverage", False)),
    )

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(projection, indent=2))
    else:
        print(
            _render_text(
                projection,
                getattr(args, "prog", "seshat"),
                getattr(args, "repo", "."),
            )
        )
    return 0
