"""The deterministic workspace projection (T010, FR-007 through FR-010).

Studio is DOWNSTREAM of Core Authority. Readiness is derived by
:func:`seshat.status_surface.build_status_projection`, and this module adapts that
output into the shape ``studio-api.yaml`` declares. It never derives, upgrades, or
grants a stage, and it never emits a numeric score.

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

Standard library plus PyYAML only, and YAML is imported lazily: this module must be
importable without the ``studio`` extra.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from seshat.status_surface import _STAGE_ORDER, build_status_projection

#: The canonical status for a stage whose committed block could not be read. Chosen
#: rather than inventing a fifth status: FR-008 pins the vocabulary, and
#: `not_started` plus an explicit blocking reason is truthful -- nothing is known to
#: have advanced.
_UNKNOWN_STAGE_STATUS = "not_started"


@dataclass(frozen=True, slots=True)
class StageState:
    """One stage, projected verbatim from the committed source."""

    stage: str
    status: str
    evidence: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    required_authority: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "evidence": list(self.evidence),
            "blocking_reasons": list(self.blocking_reasons),
            "required_authority": list(self.required_authority),
        }


@dataclass(frozen=True, slots=True)
class TableJourney:
    """One table's seven-stage journey. Always seven, never a short array."""

    table_id: str
    display_name: str
    current_stage: str | None
    stages: tuple[StageState, ...]
    forbidden_scope: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "display_name": self.display_name,
            "current_stage": self.current_stage,
            "stages": [stage.as_dict() for stage in self.stages],
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
class WorkspaceSnapshot:
    """One deterministic read of one workspace."""

    revision: str
    tables: tuple[TableJourney, ...] = ()
    input_defects: tuple[InputDefect, ...] = ()
    pending_decision_count: int = 0

    def as_dict(self) -> dict:
        return {
            "revision": self.revision,
            "tables": [table.as_dict() for table in self.tables],
            "input_defects": [defect.as_dict() for defect in self.input_defects],
            "pending_decision_count": self.pending_decision_count,
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


def _stage_states(
    source_stages: dict, table_id: str
) -> tuple[tuple[StageState, ...], tuple[InputDefect, ...]]:
    """Build all seven stages, filling and REPORTING any the source omitted."""
    states: list[StageState] = []
    defects: list[InputDefect] = []

    for stage in _STAGE_ORDER:
        block = source_stages.get(stage)
        if isinstance(block, dict) and isinstance(block.get("status"), str):
            states.append(
                StageState(
                    stage=stage,
                    status=block["status"],
                    evidence=tuple(block.get("evidence", ())),
                    blocking_reasons=tuple(block.get("blocking_reasons", ())),
                )
            )
            continue

        # The contract fixes `stages` at exactly seven, so an omitted block cannot be
        # dropped. Filling it with `not_started` plus an explicit reason keeps the
        # array valid while making the gap visible; the defect below is what stops it
        # reading as a genuine "not started yet".
        states.append(
            StageState(
                stage=stage,
                status=_UNKNOWN_STAGE_STATUS,
                blocking_reasons=(
                    f"stage {stage} is absent from the committed readiness file, so "
                    "its state is unknown rather than not started",
                ),
            )
        )
        defects.append(
            InputDefect(
                code="incomplete_readiness_stages",
                message=(
                    f"the committed readiness file for {table_id} omits the {stage} "
                    "stage block"
                ),
                source_ref=f"mappings/{table_id}/readiness-status.yaml",
                recovery_action=(
                    "add the missing stage block, using "
                    "templates/readiness-status.yaml as the reference shape"
                ),
            )
        )

    return tuple(states), tuple(defects)


def _unreadable_defect(table_id: str) -> InputDefect:
    return InputDefect(
        code="unreadable_readiness_file",
        message=(
            f"the committed readiness file for {table_id} could not be parsed as a "
            "YAML mapping"
        ),
        source_ref=f"mappings/{table_id}/readiness-status.yaml",
        recovery_action=(
            "fix the YAML syntax so the readiness spine can be read; `seshat check` "
            "reports the same file under rule RS1"
        ),
    )


def _revision_digest(payload: object) -> str:
    """A stable content digest over the projected state.

    Content-addressed rather than time-based so two reads of the same committed state
    produce the same revision -- the property a browser needs to tell "nothing
    changed" from "changed back".
    """
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:16]


def build_workspace_snapshot(root: Path | str) -> WorkspaceSnapshot:
    """Project one workspace, reporting whatever the upstream projection dropped."""
    workspace_root = Path(root)

    upstream = build_status_projection(workspace_root)
    projected_by_table = {
        _table_name_from(workspace_root / entry["source_path"]): entry
        for entry in upstream["tables"]
    }

    journeys: list[TableJourney] = []
    defects: list[InputDefect] = []

    for path in _committed_readiness_files(workspace_root):
        table_id = _table_name_from(path)
        entry = projected_by_table.get(table_id)
        if entry is None:
            # Upstream skipped it. FR-010: name it rather than let it vanish.
            defects.append(_unreadable_defect(table_id))
            continue

        stages, stage_defects = _stage_states(entry.get("stages", {}), table_id)
        defects.extend(stage_defects)
        journeys.append(
            TableJourney(
                table_id=table_id,
                display_name=entry.get("table") or table_id,
                current_stage=entry.get("current_stage"),
                stages=stages,
            )
        )

    journeys.sort(key=lambda journey: journey.table_id)
    body = [journey.as_dict() for journey in journeys] + [
        defect.as_dict() for defect in defects
    ]
    return WorkspaceSnapshot(
        revision=_revision_digest(body),
        tables=tuple(journeys),
        input_defects=tuple(defects),
    )
