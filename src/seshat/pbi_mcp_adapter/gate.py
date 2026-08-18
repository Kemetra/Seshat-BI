"""Spec 149 -- the write preconditions for the Power BI MCP adapter. Fail-closed.

Read-only by contract: this module exposes NO write path, never writes a
readiness ``status``, and never writes an ``approvals[]`` entry. It answers one
question -- *may a mutation proceed?* -- and every answer that is not an
unambiguous clearance is a refusal with a typed blocker.

Three defects this module is shaped to prevent, each found by review before any
code existed:

* **The agent must not be able to author its own approval.** The gate reads the
  **committed** (HEAD) readiness record via :mod:`seshat.gitstate`, never the
  working tree. ``dagster_adapter/gate.py`` guards only
  ``unresolved-questions.md`` with ``is_tracked_and_clean`` and reads
  ``readiness-status.yaml`` from the worktree, so mirroring it verbatim would let
  an uncommitted, agent-written ``status: pass`` clear the gate (#334).
* **The party requesting the write must not supply the list that permits it.**
  The target allowlist is a committed artifact at a fixed path, read from HEAD.
  There is deliberately no parameter by which a caller can widen it.
* **"Named human" has one definition.** Approval shape is delegated to
  :func:`seshat.rules.readiness_status.approval_is_shape_valid` -- the single
  predicate shared by every surface that decides whether a gate is satisfied
  (issue #487). A local re-implementation would be a fourth, weaker path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from seshat.gitstate import committed_text, is_tracked_and_clean
from seshat.rules.readiness_status import approval_is_shape_valid

# The committed target allowlist. A FIXED path, deliberately not a parameter:
# an allowlist the caller can point elsewhere is not an allowlist.
TARGET_ALLOWLIST_RELPATH = "contracts/pbi-mcp-write-targets.yaml"

# The stage that must pass, and the stage whose approval authorizes a write.
REQUIRED_STAGE = "semantic_model_ready"
APPROVAL_STAGE = "publish_ready"

# Typed blocker identifiers, following the shipped ``PBIMCP-*`` scheme used by
# the read-only family (preflight.py). One id per precondition, so a refusal
# names the specific missing authority rather than a generic failure (FR-009).
BLOCKER_STAGE_NOT_PASS = "PBIMCP-GATE-01"
BLOCKER_STAGE_UNREADABLE = "PBIMCP-GATE-02"
BLOCKER_STATE_UNCOMMITTED = "PBIMCP-GATE-03"
BLOCKER_APPROVAL_ABSENT = "PBIMCP-GATE-04"
BLOCKER_APPROVAL_TARGET = "PBIMCP-GATE-05"
BLOCKER_OPERATION_UNBOUND = "PBIMCP-GATE-06"
BLOCKER_TARGET_NOT_ALLOWLISTED = "PBIMCP-GATE-07"
BLOCKER_TARGET_ABSENT = "PBIMCP-GATE-08"
BLOCKER_GIT_UNSAFE = "PBIMCP-GATE-09"

#: Human-readable detail per blocker id. Categorical text only -- never a score.
BLOCKER_DETAIL: dict[str, str] = {
    BLOCKER_STAGE_NOT_PASS: f"{REQUIRED_STAGE} is not 'pass' for this target",
    BLOCKER_STAGE_UNREADABLE: "readiness state is absent, malformed, or unreadable",
    BLOCKER_STATE_UNCOMMITTED: (
        "readiness state is untracked or differs from HEAD; a worktree-only "
        "clearance never entered audit history and is never a GO signal"
    ),
    BLOCKER_APPROVAL_ABSENT: (
        f"no shape-valid named-human {APPROVAL_STAGE} approval "
        "(needs 'Name (authority_class)' and an ISO at: date)"
    ),
    BLOCKER_APPROVAL_TARGET: (
        f"the {APPROVAL_STAGE} approval note does not name this target as a whole token"
    ),
    BLOCKER_OPERATION_UNBOUND: (
        "the requested operation did not resolve to an approved definition for "
        "this target"
    ),
    BLOCKER_TARGET_NOT_ALLOWLISTED: (
        f"target is not in the committed allowlist ({TARGET_ALLOWLIST_RELPATH})"
    ),
    BLOCKER_TARGET_ABSENT: "target is allowlisted but its artifact is absent on disk",
    BLOCKER_GIT_UNSAFE: "working tree is dirty and no backup was declared",
}


@dataclass(frozen=True)
class Approval:
    """One named-human ``approvals[]`` row, read verbatim from the COMMITTED record.

    Unlike ``dagster_adapter.gate.Approval`` this carries ``note``, because the
    whole-token target match (FR-006) consumes it. Reusing the shipped dataclass
    would silently drop the field the precondition depends on.
    """

    stage: str
    owner: str
    at: str
    note: str


@dataclass(frozen=True)
class GateVerdict:
    """The write preconditions evaluated together. Immutable and fail-closed."""

    target_id: str
    stage_readable: bool
    state_committed: bool
    stage_pass: bool
    approval: Approval | None
    approval_names_target: bool
    operation_binds: bool
    target_allowlisted: bool
    target_exists: bool
    git_safe: bool
    blockers: tuple[str, ...]

    @property
    def cleared(self) -> bool:
        """The ONLY GO signal. Every component must hold; never inferred."""
        return (
            self.stage_readable
            and self.state_committed
            and self.stage_pass
            and self.approval is not None
            and self.approval_names_target
            and self.operation_binds
            and self.target_allowlisted
            and self.target_exists
            and self.git_safe
            and not self.blockers
        )

    @property
    def blocking(self) -> bool:
        """Non-empty blockers is ALWAYS blocking.

        There is deliberately no warning-level representation: a precondition
        failure a script could ignore is not a gate (FR-009).
        """
        return bool(self.blockers)

    def detail_for(self, blocker: str) -> str:
        return BLOCKER_DETAIL.get(blocker, blocker)


def _readiness_relpath(target_id: str) -> str:
    return f"mappings/{target_id}/readiness-status.yaml"


def _load_committed_yaml(repo_root: Path, relpath: str) -> tuple[dict | None, bool]:
    """Parse ``relpath`` as it exists at HEAD.

    Returns ``(data, committed)``. ``data`` is None when the file is absent,
    unparseable, or unreadable -- all three fail closed, and none is
    distinguished from the others in a way that could be mistaken for a pass.

    ``yaml.safe_load`` is wrapped deliberately: ``dagster_adapter/gate.py`` calls
    it unguarded, so a malformed record raises out of the reader instead of
    becoming a typed refusal.
    """
    if not is_tracked_and_clean(repo_root, relpath):
        return None, False
    text = committed_text(repo_root, relpath)
    if text is None:
        return None, False
    import yaml  # lazy: keeps module import dependency-light

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, True
    return (data if isinstance(data, dict) else None), True


def _stage_status(data: dict, stage: str) -> str:
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return "missing"
    block = stages.get(stage)
    if not isinstance(block, dict):
        return "missing"
    return str(block.get("status", "missing"))


def _shape_valid_approval(data: dict, stage: str) -> Approval | None:
    """The first shape-valid approval for ``stage``, or None.

    Shape validity is delegated, not re-implemented: one definition of
    "named human" across every gate-deciding surface (issue #487).
    """
    rows = data.get("approvals")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict) or row.get("stage") != stage:
            continue
        if not approval_is_shape_valid(row):
            continue
        return Approval(
            stage=str(row.get("stage", "")),
            owner=str(row.get("owner", "")),
            at=str(row.get("at", "")),
            note=str(row.get("note", "")),
        )
    return None


def note_names_target(note: str, target_id: str) -> bool:
    """Whether ``note`` names ``target_id`` as a WHOLE TOKEN.

    Not a substring test. ``sales_model`` must not authorize ``sales_model_v2``,
    or a loosely-worded note silently widens its own scope -- the self-granted
    authority Principle V forbids. Delimiters are start/end of string, whitespace
    or punctuation; ``\\b`` alone is insufficient because ``_`` is a word
    character in ``re``, so ``sales_model_v2`` would match ``sales_model``.
    """
    if not note or not target_id:
        return False
    pattern = rf"(?<![0-9A-Za-z_]){re.escape(target_id)}(?![0-9A-Za-z_])"
    return re.search(pattern, note) is not None


def read_allowlist(repo_root: Path) -> tuple[dict[str, str], bool]:
    """The COMMITTED target allowlist as ``{target_id: relative_path}``.

    Returns ``({}, False)`` when the allowlist is absent, uncommitted, or
    unparseable -- so an uncommitted widening is invisible to the gate and a
    missing allowlist refuses everything rather than permitting everything.
    """
    data, committed = _load_committed_yaml(repo_root, TARGET_ALLOWLIST_RELPATH)
    if data is None:
        return {}, committed
    entries = data.get("targets")
    if not isinstance(entries, list):
        return {}, committed
    resolved: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        target_id = entry.get("target_id")
        path = entry.get("path")
        if isinstance(target_id, str) and isinstance(path, str):
            resolved[target_id] = path
    return resolved, committed


def evaluate(
    repo_root: Path,
    target_id: str,
    *,
    operation_binds: bool = False,
    backup_declared: bool = False,
    tree_clean: bool = True,
) -> GateVerdict:
    """Evaluate every write precondition for ``target_id``. Fail-closed.

    ``operation_binds`` is supplied by the caller's operation-resolution step
    (FR-011a/FR-011c) and defaults to ``False``: an unbound operation refuses,
    so forgetting to resolve one cannot clear the gate by omission.

    ``tree_clean`` and ``backup_declared`` are passed in rather than probed here
    so the git-safety leg stays independently testable; the production caller
    sources ``tree_clean`` from :mod:`seshat.gitstate`, which fails closed on a
    git error. ``dagster_adapter/evidence._is_workspace_dirty`` must NOT be used
    -- it returns ``False`` (clean) on an exception, turning a git failure into a
    cleared precondition.
    """
    root = Path(repo_root)
    blockers: list[str] = []

    data, committed = _load_committed_yaml(root, _readiness_relpath(target_id))
    stage_readable = data is not None
    if not committed:
        blockers.append(BLOCKER_STATE_UNCOMMITTED)
    if not stage_readable:
        blockers.append(BLOCKER_STAGE_UNREADABLE)

    stage_pass = stage_readable and _stage_status(data or {}, REQUIRED_STAGE) == "pass"
    if stage_readable and not stage_pass:
        blockers.append(BLOCKER_STAGE_NOT_PASS)

    approval = _shape_valid_approval(data, APPROVAL_STAGE) if data else None
    if stage_readable and approval is None:
        blockers.append(BLOCKER_APPROVAL_ABSENT)

    names_target = approval is not None and note_names_target(approval.note, target_id)
    if approval is not None and not names_target:
        blockers.append(BLOCKER_APPROVAL_TARGET)

    if not operation_binds:
        blockers.append(BLOCKER_OPERATION_UNBOUND)

    allowlist, _ = read_allowlist(root)
    allowlisted = target_id in allowlist
    target_exists = False
    if not allowlisted:
        blockers.append(BLOCKER_TARGET_NOT_ALLOWLISTED)
    else:
        target_exists = (root / allowlist[target_id]).is_file()
        if not target_exists:
            blockers.append(BLOCKER_TARGET_ABSENT)

    git_safe = bool(tree_clean or backup_declared)
    if not git_safe:
        blockers.append(BLOCKER_GIT_UNSAFE)

    return GateVerdict(
        target_id=target_id,
        stage_readable=stage_readable,
        state_committed=committed,
        stage_pass=stage_pass,
        approval=approval,
        approval_names_target=names_target,
        operation_binds=operation_binds,
        target_allowlisted=allowlisted,
        target_exists=target_exists,
        git_safe=git_safe,
        blockers=tuple(blockers),
    )
