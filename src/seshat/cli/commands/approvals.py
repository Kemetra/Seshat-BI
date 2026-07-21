"""`retail approvals` handler for the read-only approval inbox."""

from __future__ import annotations

import argparse
import json


def _render_text(inbox: dict, prog: str = "seshat") -> str:
    items = inbox.get("items", [])
    if not items:
        return f"{prog} approvals: no open approval issues found."

    lines: list[str] = []
    for item in items:
        lines.append(f"{item['table']} ({item['source_path']})")
        lines.append(f"  stage: {item['stage']}")
        lines.append(f"  status: {item['status']}")
        lines.append(f"  issue: {item['issue']}")
        lines.append(f"  required_authority: {item['required_authority']}")
        lines.append(f"  detail: {item['detail']}")
        for reason in item.get("blocking_reasons", []):
            lines.append(f"  blocking_reason: {reason}")
        for owner in item.get("invalid_approvals", []):
            lines.append(f"  invalid_approval_owner: {owner}")
        lines.append("")
    return "\n".join(lines).rstrip()


def approvals_main(args: argparse.Namespace) -> int:
    from seshat.approval_inbox import build_approval_inbox

    inbox = build_approval_inbox(args.repo)
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(inbox, indent=2))
    else:
        print(_render_text(inbox, getattr(args, "prog", "seshat")))
    return 0
