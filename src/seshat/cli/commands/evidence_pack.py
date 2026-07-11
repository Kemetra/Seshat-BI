"""`retail evidence-pack` handler for the read-only pack preview."""

from __future__ import annotations

import argparse
import json


def _render_text(pack: dict) -> str:
    lines = [
        f"table: {pack['table']}",
        f"outcome: {pack.get('outcome')}",
        f"current_stage: {pack.get('current_stage')}",
        f"source_path: {pack.get('source_path')}",
        f"publish_ready: {pack['publish_ready'].get('status')}",
    ]
    approval = pack["publish_ready"].get("approval")
    if approval:
        lines.append(f"publish_approval: {approval['owner']} at {approval['at']}")
    for section in pack.get("sections", []):
        lines.append(f"{section['id']} {section['name']}: {section['status']}")
        for reason in section.get("blocking_reasons", []):
            lines.append(f"  blocking_reason: {reason}")
    lines.append("read_only_proof: true")
    return "\n".join(lines)


def evidence_pack_main(args: argparse.Namespace) -> int:
    from seshat.evidence_pack import build_evidence_pack

    pack = build_evidence_pack(args.repo, args.table)
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(pack, indent=2))
    else:
        print(_render_text(pack))
    return 0
