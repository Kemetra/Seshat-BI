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
    #: What this verdict AUTHORIZED. The runner must execute these and nothing
    #: else. Carrying them here is what makes a verdict unreplayable: previously
    #: the runner checked `cleared` and then independently accepted whatever
    #: target_path and operation_id a caller handed it, so a verdict cleared for
    #: sales_model/update_measure could launch drop_all_tables on ../outside.tmdl.
    authorized_operation: str
    authorized_path: str | None
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
        """The ONLY GO signal. Every component must hold; never inferred.

        ``all()`` over an explicit tuple rather than a 13-term ``and``-chain: one
        precondition per line either way, so nothing is hidden behind a helper,
        but the reader sees a single conjunction instead of thirteen branches.
        Equivalent because every element is a plain field read on a frozen
        dataclass -- no side effects and no exceptions, so losing short-circuit
        evaluation changes nothing. Verified exhaustively over all 8192 field
        combinations against the previous chain.

        Adding a precondition means adding a LINE here. It must never become a
        call to a helper that groups several: the point of this list is that a
        reviewer can answer "what clears this gate?" without leaving the function.
        """
        return all(
            (
                self.stage_readable,
                self.state_committed,
                self.stage_pass,
                self.approval is not None,
                self.approval_names_target,
                self.approval_names_operation,
                self.operation_binds,
                self.target_allowlisted,
                self.target_exists,
                self.git_safe,
                self.authorized_path is not None,
                bool(self.authorized_operation),
                not self.blockers,
            )
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
    root = Path(repo_root)
    try:
        # RESTORE-CAPABLE, not merely resolvable. `rev-parse --verify` accepts a
        # BLOB sha, and `git diff <blob> -- <path>` reports no difference for it --
        # but `git restore --source=<blob>` exits 128, so the emitted rollback
        # guidance would fail exactly when the operator needs it. A backup must be
        # a commit-ish, which is what `<ref>^{commit}` asserts.
        commitish = run_git(
            root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
        )
        if commitish.returncode != 0:
            return False
        # The ref must actually CONTAIN the target, not merely differ from nothing:
        # `git diff` against a tree that lacks the path reports no difference.
        listed = run_git(root, "cat-file", "-e", f"{ref}:{relative}")
        if listed.returncode != 0:
            return False
        diff = run_git(root, "diff", "--quiet", ref, "--", relative)
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


def _shape_valid_approvals(data: dict, stage: str) -> tuple[Approval, ...]:
    """EVERY shape-valid approval for ``stage``, in recorded order.

    Shape validity is delegated, not re-implemented: one definition of
    "named human" across every gate-deciding surface (issue #487).

    All of them, not the first: an audit trail GROWS, so a target may carry an
    older approval for one operation and a newer one for another. Returning only
    the first made the second unauthorizable unless the older row were rewritten
    -- and rewriting a recorded human approval to authorize new work is what an
    append-only trail exists to prevent (Codex review, PR #659).
    """
    rows = data.get("approvals")
    if not isinstance(rows, list):
        return ()
    found: list[Approval] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("stage") != stage:
            continue
        if not approval_is_shape_valid(row):
            continue
        found.append(
            Approval(
                stage=str(row.get("stage", "")),
                owner=str(row.get("owner", "")),
                at=str(row.get("at", "")),
                note=str(row.get("note", "")),
            )
        )
    return tuple(found)


def _authorizing_approval(
    approvals: tuple[Approval, ...], target_id: str, operation_id: str
) -> Approval | None:
    """The first approval naming BOTH the target and the operation.

    Both token checks on the SAME row. They must not be satisfiable by different
    rows: two narrow approvals would otherwise combine into one wider authority
    no human granted, and an approval naming the target still does not authorize
    an arbitrary operation on it (FR-011c).
    """
    for approval in approvals:
        names_operation = bool(operation_id) and note_names_target(
            approval.note, operation_id
        )
        if names_operation and note_names_target(approval.note, target_id):
            return approval
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


@dataclass(frozen=True)
class _ReadinessFacts:
    """What the COMMITTED readiness record says. One cohesive read."""

    stage_readable: bool
    state_committed: bool
    stage_pass: bool
    approval: Approval | None
    names_target: bool
    names_operation: bool
    blockers: tuple[str, ...]


def _stage_blockers(data: dict | None, committed: bool) -> tuple[bool, tuple[str, ...]]:
    """Whether the required stage passes, and what blocks it."""
    blockers: list[str] = []
    if not committed:
        blockers.append(BLOCKER_STATE_UNCOMMITTED)
    if data is None:
        blockers.append(BLOCKER_STAGE_UNREADABLE)
        return False, tuple(blockers)
    stage_pass = _stage_status(data, REQUIRED_STAGE) == "pass"
    if not stage_pass:
        blockers.append(BLOCKER_STAGE_NOT_PASS)
    return stage_pass, tuple(blockers)


def _approval_blockers(
    data: dict | None, target_id: str, operation_id: str
) -> tuple[Approval | None, bool, bool, tuple[str, ...]]:
    """The authorizing approval, what it names, and what blocks it.

    Both names must match: a target-naming approval does not authorize every
    operation on that target (FR-011c).
    """
    if data is None:
        return None, False, False, ()
    approvals = _shape_valid_approvals(data, APPROVAL_STAGE)
    if not approvals:
        return None, False, False, (BLOCKER_APPROVAL_ABSENT,)

    authorizing = _authorizing_approval(approvals, target_id, operation_id)
    if authorizing is not None:
        return authorizing, True, True, ()

    # Nothing authorizes this pair. Report against the row that came CLOSEST --
    # one naming the target -- so the blocker names the missing OPERATION when a
    # human approved this target for something else.
    approval = next(
        (a for a in approvals if note_names_target(a.note, target_id)),
        approvals[0],
    )
    blockers: list[str] = []
    names_target = note_names_target(approval.note, target_id)
    if not names_target:
        blockers.append(BLOCKER_APPROVAL_TARGET)
    names_operation = bool(operation_id) and note_names_target(
        approval.note, operation_id
    )
    if not names_operation:
        blockers.append(BLOCKER_APPROVAL_OPERATION)
    return approval, names_target, names_operation, tuple(blockers)


def _read_readiness_facts(
    repo_root: Path, target_id: str, operation_id: str
) -> _ReadinessFacts:
    """Read the stage and approval preconditions from HEAD. Fail-closed."""
    data, committed = _load_committed_yaml(repo_root, _readiness_relpath(target_id))
    stage_pass, stage_blockers = _stage_blockers(data, committed)
    approval, names_target, names_operation, approval_blockers = _approval_blockers(
        data, target_id, operation_id
    )
    return _ReadinessFacts(
        stage_readable=data is not None,
        state_committed=committed,
        stage_pass=stage_pass,
        approval=approval,
        names_target=names_target,
        names_operation=names_operation,
        blockers=(*stage_blockers, *approval_blockers),
    )


@dataclass(frozen=True)
class _TargetFacts:
    """What the COMMITTED allowlist authorizes for this target and operation."""

    entry: AllowlistEntry | None
    allowlisted: bool
    target_exists: bool
    operation_binds: bool
    blockers: tuple[str, ...]


def _path_blockers(
    repo_root: Path, entry: AllowlistEntry | None
) -> tuple[bool, tuple[str, ...]]:
    """Whether the target artifact is present and contained, and what blocks it."""
    if entry is None:
        return False, (BLOCKER_TARGET_NOT_ALLOWLISTED,)
    contained = _contained_target(repo_root, entry.path)
    if contained is None:
        # Checked BEFORE existence: an escaping path must be refused for escaping,
        # not incidentally because the file happened to be absent.
        return False, (BLOCKER_TARGET_ESCAPES_REPO,)
    # A file OR a directory. The vendor runtime binds a TMDL *folder*
    # (`connection_operations/ConnectFolder`) and flushes the whole folder back
    # (`database_operations/ExportToTmdlFolder`), so a write target is legitimately
    # a `*.SemanticModel` directory -- verified against the real binary
    # (research.md R8). Requiring `is_file()` made the two branches mutually
    # exclusive: a file target cleared the gate and could not be connected, while
    # a folder target could be connected and never cleared (issue #660 review C1).
    #
    # Containment is unchanged and still enforced above: widening what KIND of
    # path may be named does not widen WHERE it may point.
    if not contained.exists():
        return False, (BLOCKER_TARGET_ABSENT,)
    return True, ()


def _operation_binds(
    entry: AllowlistEntry | None, target_id: str, operation_id: str
) -> bool:
    """Whether the operation RESOLVES against this target's approved set.

    A bare truthiness check on ``operation_id`` alone is a fail-open -- any
    non-empty string would clear -- and reverting to it undoes FR-011a/FR-011c.
    """
    return (
        entry is not None
        and bool(operation_id)
        and entry.target_id == target_id
        and entry.permits(operation_id)
    )


def _resolve_target_facts(
    repo_root: Path, target_id: str, operation_id: str
) -> _TargetFacts:
    """Resolve the target and operation against the committed allowlist."""
    allowlist, allowlist_committed = read_allowlist(repo_root)
    entry = allowlist.get(target_id)
    target_exists, path_blockers = _path_blockers(repo_root, entry)
    binds = _operation_binds(entry, target_id, operation_id)
    blockers = (
        *((BLOCKER_ALLOWLIST_UNCOMMITTED,) if not allowlist_committed else ()),
        *path_blockers,
        *((BLOCKER_OPERATION_UNBOUND,) if not binds else ()),
    )
    return _TargetFacts(
        entry=entry,
        allowlisted=entry is not None,
        target_exists=target_exists,
        operation_binds=binds,
        blockers=blockers,
    )


def _git_safety(
    repo_root: Path,
    *,
    tree_clean: bool | None,
    backup_ref: str | None,
    target_path: str | None,
) -> tuple[bool, tuple[str, ...]]:
    """Whether it is safe to mutate, and why not when it is not.

    ``tree_clean is None`` means never probed, which refuses: a permissive
    default would clear this leg by omission.
    """
    if tree_clean is None:
        return False, (BLOCKER_GIT_UNPROBED,)
    if tree_clean and backup_ref is None:
        # Cleanliness alone satisfies the gate: `git restore` recovers the target.
        return True, ()
    if backup_ref is None:
        return False, (BLOCKER_GIT_UNSAFE,)
    # A SUPPLIED ref is validated whether or not the tree is clean. Returning
    # early on cleanliness left it unchecked while `rollback_guidance_for` still
    # PREFERRED it -- so an unresolvable ref made the promised rollback fail, and a
    # stale one would restore an OLDER model instead of the pre-write state,
    # exactly when the operator is relying on the guidance (Codex, PR #659).
    if not _ref_resolves(repo_root, backup_ref):
        return False, (BLOCKER_BACKUP_UNRESOLVABLE,)
    if target_path is not None and not _ref_holds_target(
        repo_root, backup_ref, target_path
    ):
        # Resolution is not custody: a backup ref that merely resolves can hold
        # none of the target's current bytes, and its rollback would then destroy
        # the very work it claimed to protect.
        return False, (BLOCKER_BACKUP_MISSES_TARGET,)
    return True, ()


@dataclass(frozen=True)
class GitState:
    """The PROBED git facts, bundled so they travel as one value.

    ``tree_clean`` keeps its fail-closed default: ``None`` means "never probed"
    and :func:`_git_safety` refuses on it. Bundling changes only how the pair is
    passed -- the refusal reads the FIELD, so an omitted probe still refuses and
    a caller gains no way to assert its way past the check.

    ``backup_ref`` is a git ref, not a boolean attestation: see
    :func:`_ref_holds_target`.
    """

    tree_clean: bool | None = None
    backup_ref: str | None = None


def evaluate(
    repo_root: Path,
    target_id: str,
    operation_id: str = "",
    git_state: GitState | None = None,
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
    requested one (FR-011c). Only the approval-time content hash (FR-011b) is out
    of scope -- externally blocked for want of a producer this spec may not build.

    ``git_state`` carries the probed facts. ``tree_clean`` keeps **no permissive
    default**: ``None`` -- including an omitted ``git_state`` -- means "never
    probed" and refuses.
    Callers source it from :mod:`seshat.gitstate`, which fails closed on a git
    error; ``dagster_adapter/evidence._is_workspace_dirty`` must NOT be used -- it
    returns ``False`` (clean) on an exception, turning a git failure into a
    cleared precondition.

    ``backup_ref`` is a git ref, not a boolean attestation, and must hold the
    target's current content -- see :func:`_ref_holds_target`.
    """
    root = Path(repo_root)
    readiness = _read_readiness_facts(root, target_id, operation_id)
    target = _resolve_target_facts(root, target_id, operation_id)
    authorized_path = (
        target.entry.path if target.entry is not None and target.target_exists else None
    )
    git = GitState() if git_state is None else git_state
    git_safe, git_blockers = _git_safety(
        root,
        tree_clean=git.tree_clean,
        backup_ref=git.backup_ref,
        target_path=target.entry.path if target.entry is not None else None,
    )

    return GateVerdict(
        target_id=target_id,
        authorized_operation=operation_id,
        authorized_path=authorized_path,
        stage_readable=readiness.stage_readable,
        state_committed=readiness.state_committed,
        stage_pass=readiness.stage_pass,
        approval=readiness.approval,
        approval_names_target=readiness.names_target,
        approval_names_operation=readiness.names_operation,
        operation_binds=target.operation_binds,
        target_allowlisted=target.allowlisted,
        target_exists=target.target_exists,
        git_safe=git_safe,
        blockers=(*readiness.blockers, *target.blockers, *git_blockers),
    )
