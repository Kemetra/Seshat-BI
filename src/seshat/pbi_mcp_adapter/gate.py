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

from seshat.gitstate import committed_text, is_tracked_and_clean, run_git
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
BLOCKER_ALLOWLIST_UNCOMMITTED = "PBIMCP-GATE-10"
BLOCKER_GIT_UNPROBED = "PBIMCP-GATE-11"
BLOCKER_BACKUP_UNRESOLVABLE = "PBIMCP-GATE-12"
BLOCKER_TARGET_ESCAPES_REPO = "PBIMCP-GATE-13"
BLOCKER_BACKUP_MISSES_TARGET = "PBIMCP-GATE-14"
BLOCKER_APPROVAL_OPERATION = "PBIMCP-GATE-15"

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
    BLOCKER_ALLOWLIST_UNCOMMITTED: (
        f"{TARGET_ALLOWLIST_RELPATH} is untracked or differs from HEAD; an "
        "uncommitted allowlist widening never entered review"
    ),
    BLOCKER_GIT_UNPROBED: (
        "git working state was never probed; the caller must supply a probe "
        "result rather than let the precondition pass by omission"
    ),
    BLOCKER_BACKUP_UNRESOLVABLE: (
        "the declared backup ref does not resolve in this repository"
    ),
    BLOCKER_TARGET_ESCAPES_REPO: (
        "the allowlisted target path resolves outside the repository; a write "
        "target must be contained by the repo it is governed in"
    ),
    BLOCKER_BACKUP_MISSES_TARGET: (
        "the declared backup ref resolves but does not contain the target's "
        "current content, so it is not a backup of what is about to change"
    ),
    BLOCKER_APPROVAL_OPERATION: (
        "the publish_ready approval note does not name the requested operation; "
        "a target-naming approval does not authorize every operation on it"
    ),
}


def _contained_target(repo_root: Path, relative: str) -> Path | None:
    """Resolve ``relative`` under ``repo_root``, or None if it escapes.

    The allowlist is committed and reviewed, so a ``../`` entry would have to
    pass a human -- but "a reviewer would have noticed" is precisely the kind of
    vigilance assumption this gate exists to replace. Containment is enforced,
    not trusted.

    An absolute path, a ``..`` traversal, and a symlink pointing outside all
    resolve outside the root and are refused. ``resolve()`` is used on both sides
    so the comparison is not defeated by ``.``/``..`` segments or by a symlinked
    repo root.
    """
    root = Path(repo_root).resolve()
    try:
        candidate = (root / relative).resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    if candidate == root:
        return None
    return candidate if candidate.is_relative_to(root) else None


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
    approval_names_operation: bool
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
            and self.approval_names_operation
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


def _ref_resolves(repo_root: Path, ref: str) -> bool:
    """Whether ``ref`` names something that actually exists in this repository.

    Fails CLOSED: an empty ref, a git failure, or any exception reads as
    unresolvable. Uses the hardened :func:`seshat.gitstate.run_git`, so this is
    read-only and never touches the ref it verifies.
    """
    if not ref:
        return False
    try:
        probe = run_git(Path(repo_root), "rev-parse", "--verify", "--quiet", ref)
    except (OSError, RuntimeError):
        return False
    return probe.returncode == 0


def _ref_holds_target(repo_root: Path, ref: str, relative: str) -> bool:
    """Whether ``ref`` actually contains the target's CURRENT content.

    Resolution is the wrong property to verify. ``--backup-ref HEAD`` on a dirty
    tree resolves fine and backs up **nothing** -- HEAD is precisely where the
    uncommitted content is *not*. Worse, the rollback guidance then emits
    ``git restore --source=HEAD``, which destroys the operator's uncommitted work
    and presents that as the recovery path.

    Verifying *custody* rather than *resolution* is what makes the backup real.
    A boolean ``--backup-declared`` let the requesting party satisfy the
    precondition protecting it; verifying only that a ref exists reintroduced the
    same defect one level down.

    Fails CLOSED on any git failure.
    """
    if not _ref_resolves(repo_root, ref):
        return False
    try:
        diff = run_git(Path(repo_root), "diff", "--quiet", ref, "--", relative)
    except (OSError, RuntimeError):
        return False
    # returncode 0 == no difference: the ref holds exactly this content.
    return diff.returncode == 0


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


@dataclass(frozen=True)
class AllowlistEntry:
    """One committed, reviewed write target and the operations approved for it."""

    target_id: str
    path: str
    operations: tuple[str, ...]

    def permits(self, operation_id: str) -> bool:
        """Whether ``operation_id`` is one of this target's approved operations.

        Exact membership, never a prefix or substring: the operation set is a
        closed vocabulary, so an unlisted identifier is a refusal.
        """
        return operation_id in self.operations


def read_allowlist(repo_root: Path) -> tuple[dict[str, AllowlistEntry], bool]:
    """The COMMITTED target allowlist, keyed by ``target_id``.

    Returns ``({}, committed)``. ``committed`` is False when the file is absent,
    untracked, or differs from HEAD -- so an uncommitted widening is invisible to
    the gate, and a missing allowlist refuses everything rather than permitting
    everything. The two failures are reported through DISTINCT blockers, because
    "not allowlisted" and "your allowlist edit was never committed" are different
    problems with different fixes (FR-009).
    """
    data, committed = _load_committed_yaml(repo_root, TARGET_ALLOWLIST_RELPATH)
    if data is None:
        return {}, committed
    entries = data.get("targets")
    if not isinstance(entries, list):
        return {}, committed
    resolved: dict[str, AllowlistEntry] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        target_id = entry.get("target_id")
        path = entry.get("path")
        if not isinstance(target_id, str) or not isinstance(path, str):
            continue
        raw_operations = entry.get("operations")
        operations = (
            tuple(str(op) for op in raw_operations)
            if isinstance(raw_operations, list)
            else ()
        )
        resolved[target_id] = AllowlistEntry(
            target_id=target_id, path=path, operations=operations
        )
    return resolved, committed


def evaluate(
    repo_root: Path,
    target_id: str,
    operation_id: str = "",
    *,
    tree_clean: bool | None = None,
    backup_ref: str | None = None,
) -> GateVerdict:
    """Evaluate every write precondition for ``target_id``. Fail-closed.

    Every precondition is **derived**, never accepted as a caller assertion. That
    is the whole design: a parameter a caller can set to ``True`` is not a gate,
    it is a request. So there is no ``operation_binds``, no ``backup_declared``,
    and no caller-supplied allowlist -- the earlier drafts of all three were the
    same defect as the worktree read, and "the already-approved X" arriving as
    free-form input is a fail-open (ask: checked against *what*?).

    ``operation_id`` is **resolved** against the committed allowlist entry for
    this target (FR-011a), and that entry's own ``target_id`` must match the
    requested one (FR-011c). An empty or unlisted identifier refuses. Only the
    approval-time content hash (FR-011b) remains out of scope -- externally
    blocked for want of a producer this spec may not build.

    ``tree_clean`` has **no default**: ``None`` means "never probed" and refuses.
    A ``True`` default would let a caller that forgot to probe git pass the
    git-safety leg by omission. Callers source it from :mod:`seshat.gitstate`,
    which fails closed on a git error;
    ``dagster_adapter/evidence._is_workspace_dirty`` must NOT be used -- it
    returns ``False`` (clean) on an exception, turning a git failure into a
    cleared precondition.

    ``backup_ref`` is a git ref, not a boolean attestation. It must actually
    resolve in this repository (``git rev-parse --verify``), so the operator
    cannot satisfy the precondition by asserting a backup exists.
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

    # The named human must approve the OPERATION, not merely the target. Without
    # this, one approval reading "approved for sales_model" authorizes every
    # operation the allowlist lists for that target, indefinitely -- and
    # "approved" would mean "committed to a YAML file", not "a human ruled on
    # this change". FR-011c requires both checks; this is the second one, and it
    # needs no external producer (unlike FR-011b's content hash).
    names_operation = (
        approval is not None
        and bool(operation_id)
        and note_names_target(approval.note, operation_id)
    )
    if approval is not None and not names_operation:
        blockers.append(BLOCKER_APPROVAL_OPERATION)

    allowlist, allowlist_committed = read_allowlist(root)
    if not allowlist_committed:
        blockers.append(BLOCKER_ALLOWLIST_UNCOMMITTED)

    entry = allowlist.get(target_id)
    allowlisted = entry is not None
    target_exists = False
    if entry is None:
        blockers.append(BLOCKER_TARGET_NOT_ALLOWLISTED)
    else:
        contained = _contained_target(root, entry.path)
        if contained is None:
            # Checked BEFORE existence: an escaping path must be refused for
            # escaping, not incidentally because the file happened to be absent.
            blockers.append(BLOCKER_TARGET_ESCAPES_REPO)
        else:
            target_exists = contained.is_file()
            if not target_exists:
                blockers.append(BLOCKER_TARGET_ABSENT)

    # Operation binding is RESOLVED, not asserted: the identifier must appear in
    # the committed entry's approved set, and that entry must be for this target.
    # Operation binding is RESOLVED, not asserted: the identifier must appear in
    # the committed entry's approved set, and that entry must be for this target.
    # `bool(operation_id)` ALONE is a fail-open -- any non-empty string would
    # clear -- and reverting to it silently undoes FR-011a and FR-011c.
    operation_binds = (
        entry is not None
        and bool(operation_id)
        and entry.target_id == target_id
        and entry.permits(operation_id)
    )
    if not operation_binds:
        blockers.append(BLOCKER_OPERATION_UNBOUND)

    if tree_clean is None:
        git_safe = False
        blockers.append(BLOCKER_GIT_UNPROBED)
    elif tree_clean:
        git_safe = True
    elif backup_ref is None:
        git_safe = False
        blockers.append(BLOCKER_GIT_UNSAFE)
    elif not _ref_resolves(root, backup_ref):
        git_safe = False
        blockers.append(BLOCKER_BACKUP_UNRESOLVABLE)
    elif entry is not None and not _ref_holds_target(root, backup_ref, entry.path):
        # Resolution is not custody: `--backup-ref HEAD` on a dirty tree resolves
        # but backs up nothing, and its rollback would destroy the very work it
        # claimed to protect.
        git_safe = False
        blockers.append(BLOCKER_BACKUP_MISSES_TARGET)
    else:
        git_safe = True

    return GateVerdict(
        target_id=target_id,
        stage_readable=stage_readable,
        state_committed=committed,
        stage_pass=stage_pass,
        approval=approval,
        approval_names_target=names_target,
        approval_names_operation=names_operation,
        operation_binds=operation_binds,
        target_allowlisted=allowlisted,
        target_exists=target_exists,
        git_safe=git_safe,
        blockers=tuple(blockers),
    )
