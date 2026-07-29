"""`retail blockers` handler for the read-only blocker explainer."""

from __future__ import annotations

import argparse
import json


def _render_text(result: dict, prog: str = "seshat") -> str:
    items = result.get("items", [])
    if not items:
        return f"{prog} blockers: no readiness blockers found."

    lines: list[str] = []
    for item in items:
        lines.append(f"{item['table']} ({item['source_path']})")
        lines.append(f"  stage: {item['stage']}")
        lines.append(f"  category: {item['category']}")
        lines.append(f"  reason: {item['reason']}")
        lines.append(f"  explanation: {item['explanation']}")
        lines.append(f"  next_surface: {item['next_surface']}")
        # Who acts, from the committed allowlist. Rendered in TEXT too, not only
        # in --format json: a reader scanning this output needs to see at a glance
        # which blockers are theirs to rule on.
        if "remediation" in item:
            lines.append(f"  remediation: {item['remediation']}")
            lines.append(f"  doc: {item['doc']}")
            lines.append(f"  stop_condition: {item['stop_condition']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def blockers_main(args: argparse.Namespace) -> int:
    from seshat.blocker_explainer import build_blocker_explanations

    result = build_blocker_explanations(args.repo)
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_render_text(result, getattr(args, "prog", "seshat")))
    return 0
