"""The deterministic workspace projection (T010, FR-007 through FR-010).

Studio is DOWNSTREAM of Core Authority. Readiness is derived by
:func:`seshat.status_surface.build_status_projection`, and this module adapts that
output into the shape ``studio-api.yaml`` declares. It never derives, upgrades, or
grants a stage, and it never emits a numeric score.

**A non-canonical status is refused, not passed through.** The contract's
``StageState.status`` is a closed enum. An earlier revision guarded only on
string-ness, so a committed ``status: almost_done`` was projected verbatim into that
closed field -- a payload violating the very enum this feature exists to preserve. An
unrecognized status now becomes ``not_started`` plus a named input defect, matching
the "gate must be at least as strict as its reader" rule.

**Where it deliberately diverges from the upstream projection.**
``build_status_projection`` SKIPS a readiness file it cannot parse, and its docstring
states that as intentional: *"Failing loud on malformed readiness-status.yaml is RS1's
job; this projection's job is to report what it CAN read without crashing a downstream
host that polls it."* FR-010 obliges Studio to do the opposite -- *"MUST render
malformed or unreadable committed inputs as named input defects and MUST NOT skip them
silently"* -- so this module enumerates the committed files independently and reports
whatever the upstream dropped. Both behaviours are correct for their own consumer; the
divergence is the requirement, not a bug, and it is pinned by
``test_the_upstream_projection_skips_a_malformed_file``.

Standard library only at module scope (PyYAML arrives lazily inside
``status_surface``), so this module is importable without the ``studio`` extra.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from seshat.status_surface import _STAGE_ORDER, build_status_projection

#: The canonical status for a stage whose committed block could not be read, or whose
#: recorded status is not in the closed enum. Chosen rather than inventing a fifth
#: value: FR-008 pins the vocabulary, and `not_started` plus an explicit blocking
#: reason is truthful -- nothing is KNOWN to have advanced.
_UNKNOWN_STAGE_STATUS = "not_started"

#: The closed status vocabulary, owned by `templates/readiness-status.yaml` and
#: `schemas/agent-status.schema.json`. Duplicated here as a literal so the projection
#: can REFUSE an unknown value; a test pins it against the contract's own enum.
_CANONICAL_STATUSES: frozenset[str] = frozenset(
    {"not_started", "blocked", "warning", "pass"}
)

#: `live_state` values for an evidence reference. `pending_live_profile` is the
#: [PENDING LIVE PROFILE] signal this repo already uses for "not verified against a
#: live source yet" -- a plain string could not express it, which is why the contract
#: requires an object.
_LIVE_VERIFIED = "verified"
_LIVE_PENDING = "pending_live_profile"

#: The marker the rest of Seshat uses for evidence awaiting a live run.
_PENDING_LIVE_MARKER = "[PENDING LIVE PROFILE]"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """One evidence reference, as the contract's `EvidenceRef` object."""

    label: str
    source_ref: str
    kind: str
    live_state: str

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "source_ref": self.source_ref,
            "kind": self.kind,
            "live_state": self.live_state,
        }


@dataclass(frozen=True, slots=True)
class BlockingReason:
    """One blocking reason, as the contract's `BlockingReason` object."""

    message: str
    code: str | None = None
    source_ref: str | None = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True, slots=True)
class ActionSummary:
    """The single next allowed action, projected from the committed source."""

    id: str
    label: str
    explanation: str
    requires_agent: bool
    requires_named_human: bool

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "explanation": self.explanation,
            "requires_agent": self.requires_agent,
            "requires_named_human": self.requires_named_human,
        }


@dataclass(frozen=True, slots=True)
class StageState:
    """One stage, projected verbatim from the committed source."""

    stage: str
    status: str
    evidence: tuple[EvidenceRef, ...] = ()
    blocking_reasons: tuple[BlockingReason, ...] = ()
    required_authority: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "evidence": [item.as_dict() for item in self.evidence],
            "blocking_reasons": [item.as_dict() for item in self.blocking_reasons],
            "required_authority": list(self.required_authority),
        }


@dataclass(frozen=True, slots=True)
class TableJourney:
    """One table's seven-stage journey. Always seven, never a short array."""

    table_id: str
    display_name: str
    current_stage: str | None
    stages: tuple[StageState, ...]
    next_action: ActionSummary | None = None
    forbidden_scope: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "display_name": self.display_name,
            "current_stage": self.current_stage,
            "stages": [stage.as_dict() for stage in self.stages],
            "next_action": (
                self.next_action.as_dict() if self.next_action is not None else None
            ),
            "forbidden_scope": list(self.forbidden_scope),
        }


@dataclass(frozen=True, slots=True)
class InputDefect:
    """A committed input that is malformed, unreadable, or incomplete (FR-010)."""

    code: str
    message: str
    source_ref: str | None
    recovery_action: str

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "source_ref": self.source_ref,
            "recovery_action": self.recovery_action,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceIdentity:
    """Which workspace this snapshot describes, and at what revision.

    `revision` lives HERE, not on the snapshot: `WorkspaceSnapshot` is
    `additionalProperties: false` and declares no top-level `revision`, so hoisting it
    produced a payload that failed its own contract.
    """

    display_name: str
    root_fingerprint: str
    branch: str | None
    revision: str

    def as_dict(self) -> dict:
        return {
            "display_name": self.display_name,
            "root_fingerprint": self.root_fingerprint,
            "branch": self.branch,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class AgentHealth:
    """Agent bridge health. Phase 3 has no bridge, so this is `disabled`."""

    state: str
    summary: str
    recovery_action: str
    provider: str
    version: str | None

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "summary": self.summary,
            "recovery_action": self.recovery_action,
            "provider": self.provider,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    """One deterministic read of one workspace."""

    identity: WorkspaceIdentity
    generated_at: str
    agent_health: AgentHealth
    tables: tuple[TableJourney, ...] = ()
    input_defects: tuple[InputDefect, ...] = ()
    pending_decision_count: int = 0
    next_action: ActionSummary | None = None

    @property
    def revision(self) -> str:
        """Convenience accessor; the value itself lives on the identity."""
        return self.identity.revision

    def as_dict(self) -> dict:
        return {
            "identity": self.identity.as_dict(),
            "generated_at": self.generated_at,
            "tables": [table.as_dict() for table in self.tables],
            "next_action": (
                self.next_action.as_dict() if self.next_action is not None else None
            ),
            "pending_decision_count": self.pending_decision_count,
            "input_defects": [defect.as_dict() for defect in self.input_defects],
            "agent_health": self.agent_health.as_dict(),
        }


def _committed_readiness_files(root: Path) -> list[Path]:
    """Every committed readiness file, whether or not upstream could parse it.

    This independent enumeration is what makes FR-010 possible: the upstream
    projection returns only the files it succeeded on, so comparing against this list
    is how Studio learns what was dropped.
    """
    mappings = root / "mappings"
    if not mappings.is_dir():
        return []
    return sorted(mappings.glob("*/readiness-status.yaml"))


def _table_name_from(path: Path) -> str:
    """The directory name is the table id.

    Layout: ``mappings/<table>/readiness-status.yaml``.
    """
    return path.parent.name


def _evidence_ref(value: str, table_id: str) -> EvidenceRef:
    """Wrap a committed evidence string in the contract's object shape.

    `live_state` is derived from the [PENDING LIVE PROFILE] marker the rest of Seshat
    already uses, so evidence awaiting a live run cannot read as verified.
    """
    pending = _PENDING_LIVE_MARKER in value
    return EvidenceRef(
        label=value,
        source_ref=value,
        kind="committed_reference",
        live_state=_LIVE_PENDING if pending else _LIVE_VERIFIED,
    )


def _blocking_reason(value: str, table_id: str) -> BlockingReason:
    return BlockingReason(
        message=value,
        code=None,
        source_ref=f"mappings/{table_id}/readiness-status.yaml",
    )


def _unknown_status_defect(table_id: str, stage: str, status: str) -> InputDefect:
    return InputDefect(
        code="unrecognized_stage_status",
        message=(
            f"stage {stage} of {table_id} records status {status!r}, which is not one "
            "of the four canonical readiness statuses"
        ),
        source_ref=f"mappings/{table_id}/readiness-status.yaml",
        recovery_action=(
            "set the stage status to not_started, blocked, warning, or pass; see "
            "templates/readiness-status.yaml"
        ),
    )


def _missing_stage_defect(table_id: str, stage: str) -> InputDefect:
    return InputDefect(
        code="incomplete_readiness_stages",
        message=(
            f"the committed readiness file for {table_id} omits the {stage} stage block"
        ),
        source_ref=f"mappings/{table_id}/readiness-status.yaml",
        recovery_action=(
            "add the missing stage block, using "
            "templates/readiness-status.yaml as the reference shape"
        ),
    )


def _unknown_stage_state(stage: str, reason: str) -> StageState:
    """A stage whose real state could not be established.

    `not_started` plus an explicit reason, never a fabricated advance. The reason text
    matters: without it a filled block reads as a genuine "not started yet".
    """
    return StageState(
        stage=stage,
        status=_UNKNOWN_STAGE_STATUS,
        blocking_reasons=(BlockingReason(message=reason),),
    )


def _stage_states(
    source_stages: dict, table_id: str
) -> tuple[tuple[StageState, ...], tuple[InputDefect, ...]]:
    """Build all seven stages, filling and REPORTING anything unusable."""
    states: list[StageState] = []
    defects: list[InputDefect] = []

    for stage in _STAGE_ORDER:
        block = source_stages.get(stage)
        if not isinstance(block, dict) or not isinstance(block.get("status"), str):
            states.append(
                _unknown_stage_state(
                    stage,
                    f"stage {stage} is absent from the committed readiness file, so "
                    "its state is unknown rather than not started",
                )
            )
            defects.append(_missing_stage_defect(table_id, stage))
            continue

        status = block["status"]
        if status not in _CANONICAL_STATUSES:
            # Refused, not projected: the contract's enum is closed, so passing an
            # unrecognized value through would emit a payload violating it.
            states.append(
                _unknown_stage_state(
                    stage,
                    f"stage {stage} records the unrecognized status {status!r}, so its "
                    "state is unknown rather than not started",
                )
            )
            defects.append(_unknown_status_defect(table_id, stage, status))
            continue

        states.append(
            StageState(
                stage=stage,
                status=status,
                evidence=tuple(
                    _evidence_ref(item, table_id) for item in block.get("evidence", ())
                ),
                blocking_reasons=tuple(
                    _blocking_reason(item, table_id)
                    for item in block.get("blocking_reasons", ())
                ),
            )
        )

    return tuple(states), tuple(defects)


def _unreadable_defect(table_id: str) -> InputDefect:
    return InputDefect(
        code="unreadable_readiness_file",
        message=(
            f"the committed readiness file for {table_id} could not be read as a YAML "
            "mapping"
        ),
        source_ref=f"mappings/{table_id}/readiness-status.yaml",
        recovery_action=(
            "make the file a readable YAML mapping matching "
            "templates/readiness-status.yaml; `seshat check` reports a malformed "
            "readiness spine under rule RS1"
        ),
    )


def _next_action(entry: dict, table_id: str) -> ActionSummary | None:
    """Project the committed next action. FR-008 names it; it must not be dropped.

    ``requires_named_human`` is READ, never assumed. An earlier revision hardcoded it to
    ``True``, which fabricated a governance requirement: the committed readiness spine
    records no per-action authority (`templates/readiness-status.yaml` carries
    `approvals: []` at document level and no per-stage `required_authority`), so EVERY
    action claimed a named human must approve it -- including a mechanical live-run
    step, and including a table whose seven stages all pass and whose "action" is the
    message that nothing remains. Inventing an approval is the same class of error as
    inventing a pass, and this projection exists to do neither.
    """
    label = entry.get("next_action")
    if not isinstance(label, str) or not label:
        return None
    return ActionSummary(
        id=f"{table_id}:next",
        label=label,
        explanation=(
            "Projected verbatim from the committed readiness file; Studio does not "
            "derive the next action."
        ),
        requires_agent=False,
        # Always False, and NOT because approval never applies -- because this
        # projection
        # has no source for it. `status_surface._project_table`, the upstream this
        # reads,
        # projects `table`, `source_path`, `current_stage`, `stages`,
        # `blocking_reasons`,
        # and `next_action`, and nothing else. A previous revision "read"
        # `entry["required_authority"]`, which looked correct and was INERT: the key is
        # never present, so it always evaluated False while appearing to consult the
        # source.
        #
        # `agent_next.build_table_next_document` does expose an authority, as a
        # STRING rather than a list. Adopting it is new upstream integration with its
        # own contract questions, so it is deferred rather than half-wired here.
        # Until then Studio claims no approval requirement it cannot substantiate --
        # inventing one is the same class of error as inventing a pass.
        requires_named_human=False,
    )


def _revision_digest(payload: object) -> str:
    """A stable content digest over the whole projected body.

    Content-addressed rather than time-based so two reads of the same committed state
    produce the same revision -- the property a browser needs to tell "nothing
    changed" from "changed back". Verified path-independent: the body contains only
    workspace-relative references.
    """
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:16]


def _root_fingerprint(root: Path) -> str:
    """A stable, non-reversible identifier for the pinned root.

    Hashed rather than emitted: the absolute path is operator layout, which FR-026
    keeps out of browser payloads, but the browser still needs to tell one workspace
    from another.
    """
    return hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:16]


def _disabled_agent_health() -> AgentHealth:
    """Phase 3 ships no agent bridge, and says so rather than implying one works."""
    return AgentHealth(
        state="disabled",
        summary="The agent bridge is not part of this slice.",
        recovery_action=(
            "Deterministic workspace views are fully usable; agent turns arrive with "
            "the Codex bridge."
        ),
        provider="disabled",
        version=None,
    )


def _with_table_blockers(
    stages: tuple[StageState, ...], entry: dict, table_id: str
) -> tuple[StageState, ...]:
    """Attach the upstream TABLE-level blockers to the table's current stage.

    FR-008 names blocking reasons among the fields that must be preserved, and the
    upstream projection carries them at the table level as well as per stage. Dropping
    them was a silent loss; attaching them to the current stage is where a reader
    looks for "why is this table stuck".
    """
    table_blockers = tuple(
        _blocking_reason(item, table_id)
        for item in entry.get("blocking_reasons", ())
        if isinstance(item, str)
    )
    if not table_blockers:
        return stages

    current = entry.get("current_stage")
    return tuple(
        (
            StageState(
                stage=stage.stage,
                status=stage.status,
                evidence=stage.evidence,
                blocking_reasons=stage.blocking_reasons + table_blockers,
                required_authority=stage.required_authority,
            )
            if stage.stage == current
            else stage
        )
        for stage in stages
    )


def _journey_for(
    entry: dict, table_id: str
) -> tuple[TableJourney, tuple[InputDefect, ...]]:
    """Build one table's journey plus whatever defects its source produced."""
    stages, defects = _stage_states(entry.get("stages", {}), table_id)
    return (
        TableJourney(
            table_id=table_id,
            display_name=entry.get("table") or table_id,
            current_stage=entry.get("current_stage"),
            stages=_with_table_blockers(stages, entry, table_id),
            next_action=_next_action(entry, table_id),
        ),
        defects,
    )


def _upstream_by_table(root: Path) -> dict[str, dict]:
    """The upstream projection, keyed by table id rather than source path."""
    upstream = build_status_projection(root)
    return {
        _table_name_from(root / entry["source_path"]): entry
        for entry in upstream["tables"]
    }


def build_workspace_snapshot(
    root: Path | str, *, generated_at: str | None = None
) -> WorkspaceSnapshot:
    """Project one workspace, reporting whatever the upstream projection dropped.

    ``generated_at`` is injectable so a caller can pin it; the revision digest never
    includes it, which is what keeps the digest content-addressed rather than
    time-varying.
    """
    workspace_root = Path(root)
    projected_by_table = _upstream_by_table(workspace_root)

    journeys: list[TableJourney] = []
    defects: list[InputDefect] = []

    for path in _committed_readiness_files(workspace_root):
        table_id = _table_name_from(path)
        entry = projected_by_table.get(table_id)
        if entry is None:
            # Upstream skipped it. FR-010: name it rather than let it vanish.
            defects.append(_unreadable_defect(table_id))
            continue

        journey, journey_defects = _journey_for(entry, table_id)
        journeys.append(journey)
        defects.extend(journey_defects)

    journeys.sort(key=lambda journey: journey.table_id)
    body = [journey.as_dict() for journey in journeys] + [
        defect.as_dict() for defect in defects
    ]

    identity = WorkspaceIdentity(
        display_name=workspace_root.resolve().name,
        root_fingerprint=_root_fingerprint(workspace_root),
        branch=None,
        revision=_revision_digest(body),
    )
    return WorkspaceSnapshot(
        identity=identity,
        generated_at=generated_at
        or datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        agent_health=_disabled_agent_health(),
        tables=tuple(journeys),
        input_defects=tuple(defects),
    )
