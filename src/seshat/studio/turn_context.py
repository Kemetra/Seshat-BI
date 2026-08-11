"""Turn context construction for the production bridge (T022).

What Studio tells the agent about the workspace before a turn. The Turn Context
Contract fixes both halves of this: the facts every request carries, and the values
it must never embed.

**Redaction happens on the way IN, not at the boundary.** Everything here is built
from `WorkspaceSnapshot`, which is projected from committed files -- and a committed
file can perfectly well contain a DSN in a blocker message. Scrubbing when the
context is CONSTRUCTED means the credential never enters the string that gets sent to
a provider; scrubbing at render time would leave a window where an intermediate
caller could log the raw value. This mirrors the event store's decision to redact
into the buffer rather than out of it.

**The context is a value, not a prompt string.** `build_turn_context` returns a
frozen dataclass and `render_turn_context` turns it into text. Keeping them apart
means the exclusion tests can assert on structure, and a future provider that wants
structured context does not have to re-parse prose.

**The business-approval reminder is unconditional.** It is present in read-only turns
too, because the danger is not that the agent writes a file -- it is that a technical
permission is mistaken for a governance ruling, and that misreading is available in
either mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from seshat.studio.projection import TableJourney, WorkspaceSnapshot
from seshat.studio.redaction import redact_for_boundary

__all__ = [
    "BUSINESS_APPROVAL_REMINDER",
    "TurnContext",
    "build_turn_context",
    "render_turn_context",
]

#: Stated verbatim in every context. Studio's whole governance posture is that a
#: technical allow is not a business approval, and the agent must not conflate them.
BUSINESS_APPROVAL_REMINDER = (
    "Technical permission to run a command is NOT a business approval. You cannot "
    "grant, imply, or record a governance decision; a named human does that at a "
    "separate seam."
)


@dataclass(frozen=True, slots=True)
class TurnContext:
    """One turn's workspace context. Every string here is already redacted."""

    requested_mode: str
    workspace_name: str
    table_id: str | None
    current_stage: str | None
    stage_lines: tuple[str, ...]
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]
    next_action: str | None
    forbidden_scope: tuple[str, ...]


def build_turn_context(
    snapshot: WorkspaceSnapshot,
    *,
    table_id: str | None,
    requested_mode: str,
    workspace_root: Path | None = None,
    secrets: Sequence[str | None] = (),
) -> TurnContext:
    """Assemble the context for one turn, redacting as each field is read.

    Raises `KeyError` for a table that is not in the snapshot: silently building an
    empty context would ask the agent to reason about a workspace it cannot see, and
    a confident answer about a table that was never loaded is worse than a refusal.
    """

    def clean(text: str) -> str:
        return redact_for_boundary(text, secrets=secrets, workspace_root=workspace_root)

    table = _selected_table(snapshot, table_id)

    if table is None:
        return TurnContext(
            requested_mode=requested_mode,
            workspace_name=clean(snapshot.identity.display_name),
            table_id=None,
            current_stage=None,
            stage_lines=(),
            blockers=(),
            evidence=(),
            next_action=None,
            forbidden_scope=(),
        )

    stage_lines: list[str] = []
    blockers: list[str] = []
    evidence: list[str] = []
    for stage in table.stages:
        stage_lines.append(f"{stage.stage}: {stage.status}")
        for reason in stage.blocking_reasons:
            code = f"[{reason.code}] " if reason.code else ""
            blockers.append(clean(f"{code}{reason.message}"))
        for item in stage.evidence:
            evidence.append(clean(f"{item.kind}: {item.source_ref}"))

    next_action = None
    if table.next_action is not None:
        next_action = clean(
            f"{table.next_action.label} -- {table.next_action.explanation}"
        )

    return TurnContext(
        requested_mode=requested_mode,
        workspace_name=clean(snapshot.identity.display_name),
        table_id=table.table_id,
        current_stage=table.current_stage,
        stage_lines=tuple(stage_lines),
        blockers=tuple(blockers),
        evidence=tuple(evidence),
        next_action=next_action,
        forbidden_scope=tuple(clean(item) for item in table.forbidden_scope),
    )


def _selected_table(
    snapshot: WorkspaceSnapshot, table_id: str | None
) -> TableJourney | None:
    if table_id is None:
        return None
    for table in snapshot.tables:
        if table.table_id == table_id:
            return table
    raise KeyError(f"table {table_id!r} is not in this workspace snapshot")


def render_turn_context(context: TurnContext) -> str:
    """Render the context as the text a provider receives.

    Deliberately plain: a provider-specific format belongs in that provider's adapter,
    and this text is also what a reviewer reads when auditing what was sent.
    """
    lines = [
        f"Workspace: {context.workspace_name}",
        f"Requested mode: {context.requested_mode}",
    ]
    if context.table_id is not None:
        lines.append(f"Selected table: {context.table_id}")
    if context.current_stage is not None:
        lines.append(f"Current readiness stage: {context.current_stage}")

    lines.extend(_section("Stage statuses", context.stage_lines))
    lines.extend(_section("Evidence", context.evidence))
    lines.extend(_section("Concrete blockers", context.blockers))

    if context.next_action is not None:
        lines.append(f"Next allowed action: {context.next_action}")
    lines.extend(_section("Forbidden scope", context.forbidden_scope))

    lines.append(BUSINESS_APPROVAL_REMINDER)
    return "\n".join(lines)


def _section(title: str, items: Sequence[str]) -> list[str]:
    if not items:
        return []
    return [f"{title}:", *(f"  - {item}" for item in items)]
