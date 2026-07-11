"""`retail blockers` handler for the read-only blocker explainer."""

from __future__ import annotations

import argparse
import json


def _render_text(result: dict) -> str:
    items = result.get("items", [])
    if not items:
        return "retail blockers: no readiness blockers found."

    lines: list[str] = []
    for item in items:
        lines.append(f"{item['table']} ({item['source_path']})")
        lines.append(f"  stage: {item['stage']}")
        lines.append(f"  category: {item['category']}")
        lines.append(f"  reason: {item['reason']}")
        lines.append(f"  explanation: {item['explanation']}")
        lines.append(f"  next_surface: {item['next_surface']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def blockers_main(args: argparse.Namespace) -> int:
    from seshat.blocker_explainer import build_blocker_explanations

    result = build_blocker_explanations(args.repo)
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_render_text(result))
    return 0
