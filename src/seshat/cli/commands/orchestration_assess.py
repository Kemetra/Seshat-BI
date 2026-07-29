"""`seshat orchestration-assess` handler (issue #401).

Thin presentation over the pure ``seshat.orchestration_assess`` engine: a
recommend-then-decide surface for adopting the dbt / dagster orchestration
adapters. ``--format text`` (default) is human-readable; ``--format json`` emits
the stable machine document. Read-only; exit 0 in every case (a well-formed
"orchestration not required" is success, not an error). The engine is imported
LAZILY so ``seshat check`` / CI never load it just to build the dispatch table.
"""

from __future__ import annotations

import argparse
import json


def _render_list(label: str, items: list[str], indent: str = "    ") -> list[str]:
    lines = [f"{indent}{label}:"]
    if not items:
        lines.append(f"{indent}  (none)")
    for item in items:
        lines.append(f"{indent}  - {item}")
    return lines


def _render_adapter(name: str, block: dict) -> list[str]:
    lines = [
        f"  {name}: {block['recommendation']}"
        + ("  (already present)" if block.get("already_present") else "")
    ]
    lines += _render_list("for", block.get("for", []))
    lines += _render_list("against", block.get("against", []))
    lines += _render_list(
        "open questions (you answer)", block.get("open_questions", [])
    )
    # Rewrite the install head to the documented pipx form at THIS render boundary
    # too (#507). `seshat next`'s renderer already does this
    # (next_guidance_render._portable_quoting); this is the engine string's SECOND
    # consumer, and it was still emitting the bare `pip install` that fails in the
    # documented pipx lane. Reusing the one reviewed rewriter -- rather than editing
    # `orchestration_assess._DBT_OPT_IN` -- honors the deliberate decision recorded
    # in next_guidance_render.py that the engine owns its own wording.
    from .next_guidance_render import _portable_quoting

    lines.append(
        f"    opt-in (only if YOU decide): {_portable_quoting(block['opt_in_command'])}"
    )
    return lines


def _render_text(result: dict, prog: str = "seshat") -> str:
    lines = [
        f"{prog} orchestration-assess -- recommend-then-decide (read-only)",
        f"tables onboarded: {result['table_count']} "
        f"(gold-ready: {result['gold_ready_count']})",
        "",
        f"recommended action: {result['recommended_action']}",
        "",
        "adapters:",
    ]
    lines += _render_adapter("dbt", result["adapters"]["dbt"])
    lines += _render_adapter("dagster", result["adapters"]["dagster"])
    # The Power BI block and the derived core-only answer must appear on the
    # DEFAULT path too: a verdict visible only under --format json would never
    # reach the reader who just types the command.
    if "pbi_mcp" in result.get("adapters", {}):
        lines += _render_adapter("pbi_mcp", result["adapters"]["pbi_mcp"])
    if "core_only_sufficient" in result:
        lines.append(
            f"core-only sufficient: {str(result['core_only_sufficient']).lower()}"
        )
        lines.append("")
    lines.append("")
    lines.append(
        "The tool recommends; the human decides. It never installs, runs, or "
        "approves an adapter on your behalf."
    )
    return "\n".join(lines)


def orchestration_assess_main(args: argparse.Namespace) -> int:
    from seshat.orchestration_assess import build_orchestration_assessment

    result = build_orchestration_assessment(getattr(args, "repo", "."))
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_render_text(result, getattr(args, "prog", "seshat")))
    return 0
