"""Rendering the plan or result -- text for humans, JSON for machines.

`--json` must emit JSON and nothing else: no text plan ahead of it, no prompt, no
stray log. A caller piping this into `json.loads` gets a parse error from a
single stray line, so the JSON path here returns one document and the CLI prints
exactly that. Diagnostics belong on stderr.

Preview and rolling components are labelled in BOTH renderings. A `preview`
component that renders indistinguishably from a `stable` one is the failure this
column exists to prevent.
"""

from __future__ import annotations

import json

from seshat.integrations.installer import SetupOutcome

# Channels that must be called out, not merely recorded.
_FLAGGED = {"preview", "rolling"}


def as_json(outcome: SetupOutcome) -> str:
    """The machine-readable document. The only thing printed in `--json` mode."""
    return json.dumps(
        {
            "profile": outcome.profile,
            "lock": outcome.lock_written.as_posix() if outcome.lock_written else None,
            "notes": list(outcome.notes),
            "needs_action": outcome.needs_action,
            "components": [
                {
                    "component": row.component,
                    "profile": row.profile,
                    "channel": row.channel,
                    "pinned": row.pinned,
                    "source": row.source,
                    "status": row.status,
                    "detail": row.detail,
                    # Explicit rather than inferred by the consumer: a client
                    # should not have to know which channel names are pre-GA.
                    "requires_attention": row.channel in _FLAGGED,
                }
                for row in outcome.rows
            ],
            "discovery": [
                {
                    "component": result.component,
                    "harness": result.harness,
                    "mechanism": result.mechanism,
                    "checked": result.checked,
                    "installed": result.installed,
                    "activated": result.activated,
                    "discoverable": result.discoverable,
                    "status": result.status,
                    "evidence": list(result.evidence),
                    "blockers": list(result.blockers),
                    "next_action": result.next_action,
                }
                for result in outcome.discovery
            ],
        },
        indent=2,
        sort_keys=True,
    )


def as_text(outcome: SetupOutcome) -> str:
    """The human-readable plan or result. ASCII only (a Windows console rule)."""
    lines = [f"seshat integrations setup -- profile {outcome.profile}"]
    for row in outcome.rows:
        flag = " [PREVIEW]" if row.channel == "preview" else ""
        if row.channel == "rolling":
            flag = " [ROLLING]"
        lines.append(
            f"[{row.status.upper()}] {row.component} ({row.channel}"
            f"{'' if row.pinned == '-' else ' ' + row.pinned}){flag}: {row.detail}"
        )
    for result in outcome.discovery:
        activated = _fact(result.activated)
        discoverable = _fact(result.discoverable)
        detail = "; ".join(result.blockers) or result.next_action
        lines.append(
            f"[{result.status.upper()}] {result.component}/{result.harness} "
            f"({result.mechanism}) installed={_fact(result.installed)} "
            f"activated={activated} discoverable={discoverable}: {detail}"
        )
    for note in outcome.notes:
        lines.append(f"note: {note}")
    if outcome.lock_written:
        lines.append(f"lock written: {outcome.lock_written.as_posix()}")
    lines.append(_summary(outcome))
    return "\n".join(lines)


def _fact(value: bool | None) -> str:
    if value is None:
        return "not-checked"
    return str(value).lower()


def _summary(outcome: SetupOutcome) -> str:
    if any(row.status == "planned" for row in outcome.rows):
        return (
            "Dry run only. Nothing was written. Approve explicitly "
            "(--refresh --apply) to install."
        )
    if outcome.needs_action:
        return "Some integrations need operator action; no readiness stage is changed."
    return "Integration runtimes and configuration are present."
