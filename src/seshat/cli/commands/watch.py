"""`retail watch` handler (spec 131): the ONE narrow read-only CLI addition for
Portfolio Watch, mirroring the ratified ``status --format json`` precedent
(FR-023, research D7). Read-only: runs the recurring summary + baseline diff
and prints it -- no DB, no writes beyond the local ``.seshat/watch/``
snapshot, no numeric score.
"""

from __future__ import annotations

import argparse
import json


def _dimension_line(dim: dict) -> str:
    cls = f" [{dim['class']}]" if dim.get("class") else ""
    return f"  {dim['dimension']}: {dim['state']}{cls}"


def _change_line(change: dict) -> str:
    return (
        f"  change: {change['dimension']}/{change['subject_locator']} "
        f"-> {change['label']}"
    )


def _attention_lines(scope: dict) -> list[str]:
    attention = scope.get("requires_human_attention")
    lines = [f"  requires_human_attention: {attention}"]
    if attention:
        lines.append(f"    owner: {scope.get('owner')}")
    return lines


def _scope_lines(scope: dict) -> list[str]:
    lines = [
        f"{scope['scope_id']} ({scope['source_path']})",
        f"  current_stage: {scope['current_stage']}",
    ]
    lines.extend(_dimension_line(dim) for dim in scope.get("dimensions", []))
    lines.extend(
        f"  open_blocker: {reason}" for reason in scope.get("open_blockers", [])
    )
    lines.extend(_attention_lines(scope))
    action = scope["prioritized_next_action"]
    lines.append(f"  next_action [{action['category']}]: {action['action']}")
    lines.extend(_change_line(change) for change in scope.get("change_labels", []))
    lines.append("")
    return lines


def _portfolio_lines(summary: dict) -> list[str]:
    portfolio = summary.get("portfolio", {})
    lines = [
        f"portfolio: {portfolio.get('scope_count', 0)} scope(s), "
        f"{portfolio.get('scopes_requiring_attention_count', 0)} requiring attention"
    ]
    baseline = summary.get("baseline")
    if baseline is not None and not baseline.get("used", True):
        lines.append(f"baseline: {baseline.get('note', 'no prior snapshot available')}")
    return lines


def _render_text(summary: dict, prog: str = "seshat") -> str:
    """Human-readable rendering: stage/blockers/attention/next-action per
    scope, plus the change labels -- never a score. Mirrors ``status``'s
    ``_render_text`` posture."""
    scopes = summary.get("scopes", [])
    if not scopes:
        lines = [f"{prog} watch: no governed scopes found under mappings/."]
    else:
        lines = [line for scope in scopes for line in _scope_lines(scope)]
    lines.extend(_portfolio_lines(summary))
    return "\n".join(lines).rstrip("\n")


def watch_main(args: argparse.Namespace) -> int:
    """Handler for ``watch``. Read-only; exit 0 in every case (an empty
    portfolio is success, not an error, mirroring ``status``)."""
    from seshat.portfolio_watch import run_portfolio_watch

    summary = run_portfolio_watch(getattr(args, "repo", "."))

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(summary, indent=2))
    else:
        print(_render_text(summary, getattr(args, "prog", "seshat")))
    return 0
