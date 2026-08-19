"""Spec 149 -- the allowlist, git-safety and fail-open proofs.

US2 is built BEFORE US1 deliberately: the refusal path IS the governance.

The fixtures COMMIT their records. An earlier draft wrote readiness records to
the worktree and asserted they cleared, which encoded the worst fail-open in the
feature -- an agent authoring its own approval -- as correct behavior, green.
Shared builders live in ``_pbi_mcp_gate_fixtures``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate
from tests.unit._pbi_mcp_gate_fixtures import (
    OPERATION,
    OTHER_TARGET,
    TARGET,
    _allowlist_yaml,
    _build_repo,
    _commit_all,
    _evaluate,
    _init_repo,
    _readiness_yaml,
    _write,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    return _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )


# --------------------------------------------------------------------------
# CRITICAL-3 / T012 -- the allowlist is COMMITTED, never caller-supplied
# --------------------------------------------------------------------------


def test_target_not_in_the_committed_allowlist_refuses(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(targets=(OTHER_TARGET,)),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_evaluate_exposes_no_way_for_a_caller_to_widen_the_allowlist() -> None:
    """The provenance control CRITICAL-3 demanded.

    Asserted against the actual signature: if a future edit adds an allowlist
    parameter, the requesting party could supply the list permitting it, and
    FR-007 would authorize nothing. Pins the CAPABILITY (no caller-supplied
    allowlist) rather than the absence of one specific name.
    """
    import inspect

    params = set(inspect.signature(gate.evaluate).parameters)
    forbidden = {
        "allow",
        "allowlist",
        "target_allowlist",
        "allowed_targets",
        "allows",
        # Asserted-permission parameters: a caller that can pass these can lie.
        "operation_binds",
        "backup_declared",
        "approval_ok",
        "stage_pass",
    }
    leaked = params & forbidden
    assert not leaked, (
        f"gate.evaluate must not accept a caller-supplied allowlist; found {leaked}"
    )


def test_uncommitted_allowlist_widening_is_invisible(tmp_path: Path) -> None:
    """Adding a target to the allowlist without committing must not permit it."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(targets=(OTHER_TARGET,)),
    )
    _write(repo, gate.TARGET_ALLOWLIST_RELPATH, _allowlist_yaml(targets=(TARGET,)))
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_missing_allowlist_refuses_everything(tmp_path: Path) -> None:
    """No allowlist is a refusal, never an implicit permit-all."""
    repo = _build_repo(tmp_path, readiness=_readiness_yaml(), allowlist=None)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_NOT_ALLOWLISTED in verdict.blockers


def test_target_allowlisted_but_absent_on_disk_refuses(tmp_path: Path) -> None:
    """Refused as an undefined artifact -- never invented (FR-011)."""
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(),
        artifacts=(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ABSENT in verdict.blockers


# --------------------------------------------------------------------------
# FR-011a/c -- operation binding is distinct from target-naming
# --------------------------------------------------------------------------


def test_unbound_operation_refuses_even_with_a_valid_target_approval(
    committed_repo: Path,
) -> None:
    """Target-naming alone must NOT authorize an arbitrary mutation (FR-011c).

    This is the fail-open a caller holding one valid approval would otherwise
    exploit by substituting an unrelated operation.
    """
    verdict = _evaluate(committed_repo, operation_id="")
    assert not verdict.cleared
    assert verdict.approval_names_target, "the approval itself is valid"
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_omitting_the_operation_refuses(committed_repo: Path) -> None:
    """No operation id means nothing resolved; it never clears by omission."""
    verdict = gate.evaluate(
        committed_repo, TARGET, git_state=gate.GitState(tree_clean=True)
    )
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


# --------------------------------------------------------------------------
# T013 -- git safety
# --------------------------------------------------------------------------


def test_dirty_tree_without_declared_backup_refuses(committed_repo: Path) -> None:
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref=None)
    assert not verdict.cleared
    assert gate.BLOCKER_GIT_UNSAFE in verdict.blockers


def test_dirty_tree_with_declared_backup_clears(committed_repo: Path) -> None:
    """The declared-backup escape must actually work.

    Its absence would refuse every dirty tree, which the spec does not require.
    """
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_clean_tree_clears_without_a_backup(committed_repo: Path) -> None:
    assert _evaluate(committed_repo, tree_clean=True, backup_ref=None).git_safe


# --------------------------------------------------------------------------
# T014 -- a refusal has no warning-level representation
# --------------------------------------------------------------------------


def test_non_empty_blockers_is_always_blocking(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(semantic_status="warning"),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert verdict.blockers
    assert not verdict.cleared
    assert verdict.blocking is True


def test_cleared_and_blocking_are_mutually_exclusive(committed_repo: Path) -> None:
    verdict = _evaluate(committed_repo)
    assert verdict.cleared is True
    assert verdict.blocking is False


def test_verdict_is_immutable(committed_repo: Path) -> None:
    """A caller cannot flip a refusal into a pass after the fact."""
    verdict = _evaluate(committed_repo)
    with pytest.raises(Exception):
        verdict.blockers = ()  # type: ignore[misc]


def test_verdict_carries_no_score(committed_repo: Path) -> None:
    """Hard rule #9 at the gate boundary: typed blockers, never a number."""
    verdict = _evaluate(committed_repo)
    for name, value in vars(verdict).items():
        if isinstance(value, bool):
            continue
        assert not isinstance(value, (int, float)), f"{name} looks like a score"


def test_every_blocker_id_has_readable_detail() -> None:
    """A typed blocker a human cannot read is not actionable."""
    ids = [
        value
        for name, value in vars(gate).items()
        if name.startswith("BLOCKER_") and isinstance(value, str)
    ]
    assert len(ids) == 15
    for blocker in ids:
        assert gate.BLOCKER_DETAIL.get(blocker), blocker
        assert blocker.startswith("PBIMCP-GATE-")


# --------------------------------------------------------------------------
# T019 -- the fail-open proof
# --------------------------------------------------------------------------


def test_committed_state_guard_is_what_produces_the_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable ONLY the committed-state guard; assert the old verdict returns.

    A refusal test alone cannot distinguish "the guard refused this" from "this
    would have been refused anyway for some other reason". This monkeypatches out
    exactly one thing and shows the same agent-authored, never-committed approval
    then CLEARS -- so the guard is load-bearing rather than incidental.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=_allowlist_yaml(),
        commit=False,
    )

    guarded = _evaluate(repo)
    assert not guarded.cleared
    assert gate.BLOCKER_STATE_UNCOMMITTED in guarded.blockers

    monkeypatch.setattr(gate, "is_tracked_and_clean", lambda root, rel: True)
    monkeypatch.setattr(
        gate,
        "committed_text",
        lambda root, rel: (Path(root) / rel).read_text(encoding="utf-8"),
    )

    unguarded = _evaluate(repo)
    assert unguarded.cleared, (
        "expected the fail-open to reproduce once the guard is removed; if this "
        "fails the refusal above came from something other than the guard, and "
        "the guard is not actually protecting anything"
    )


# --------------------------------------------------------------------------
# Advisor findings 1-4: every precondition is DERIVED, never asserted
# --------------------------------------------------------------------------


def test_operation_must_resolve_against_the_committed_allowlist(
    tmp_path: Path,
) -> None:
    """An unlisted operation id refuses, even for a fully approved target.

    FR-011a: the operation is *resolved from* the committed set, never accepted
    as free-form input. An earlier draft took ``operation_binds: bool`` from the
    caller -- which is a request, not a gate.
    """
    repo = _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )
    verdict = _evaluate(repo, operation_id="drop_all_tables")
    assert not verdict.cleared
    assert not verdict.operation_binds
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_operation_approved_for_another_target_does_not_authorize_this_one(
    tmp_path: Path,
) -> None:
    """FR-011c: an operation approved elsewhere is not approved here.

    ``other_only`` is listed for OTHER_TARGET, so requesting it against TARGET
    must refuse even though both targets are allowlisted.
    """
    allowlist = (
        "targets:\n"
        f"  - target_id: {TARGET}\n    path: models/{TARGET}.tmdl\n"
        f"    operations:\n      - {OPERATION}\n"
        f"  - target_id: {OTHER_TARGET}\n    path: models/{OTHER_TARGET}.tmdl\n"
        "    operations:\n      - other_only\n"
    )
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(),
        allowlist=allowlist,
        artifacts=(TARGET, OTHER_TARGET),
    )
    verdict = _evaluate(repo, operation_id="other_only")
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_target_with_no_approved_operations_refuses_every_operation(
    tmp_path: Path,
) -> None:
    """An allowlist entry omitting ``operations`` permits nothing.

    A missing key must not read as "all operations allowed" -- that would make
    the safest-looking entry the most permissive.
    """
    allowlist = f"targets:\n  - target_id: {TARGET}\n    path: models/{TARGET}.tmdl\n"
    repo = _build_repo(tmp_path, readiness=_readiness_yaml(), allowlist=allowlist)
    verdict = _evaluate(repo, operation_id=OPERATION)
    assert not verdict.cleared
    assert gate.BLOCKER_OPERATION_UNBOUND in verdict.blockers


def test_unprobed_git_state_refuses(committed_repo: Path) -> None:
    """``tree_clean=None`` means never probed, and refuses.

    A ``True`` default would let a caller that forgot to probe git clear the
    git-safety leg by omission -- a fail-open default next to a fail-closed one.
    """
    verdict = gate.evaluate(committed_repo, TARGET, OPERATION)
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_GIT_UNPROBED in verdict.blockers


def test_unresolvable_backup_ref_refuses(committed_repo: Path) -> None:
    """A backup must be VERIFIED, not attested.

    The operator names a ref; if it does not resolve, the precondition fails.
    A boolean ``--backup-declared`` let the requesting party satisfy the
    precondition protecting the request.
    """
    verdict = _evaluate(
        committed_repo, tree_clean=False, backup_ref="refs/tags/no-such-backup"
    )
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in verdict.blockers


def test_resolvable_backup_ref_clears(committed_repo: Path) -> None:
    """The positive control: a real ref does satisfy the leg."""
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_backup_ref_guard_is_load_bearing(
    committed_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable the ref checks one at a time; each refusal must disappear in turn.

    There are now TWO independent guards on a declared backup -- the ref must
    resolve, AND it must hold the target's current content. Disabling only the
    first leaves the second refusing, which is defence in depth working. So this
    proves each guard separately rather than asserting the whole leg clears.
    """
    bogus = "refs/tags/no-such-backup"

    # Guard 1: resolution.
    first = _evaluate(committed_repo, tree_clean=False, backup_ref=bogus)
    assert not first.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in first.blockers

    monkeypatch.setattr(gate, "_ref_resolves", lambda root, ref: True)

    # With resolution neutered the refusal MOVES to the custody guard -- proof
    # that guard 1 produced the first refusal and guard 2 is independent.
    second = _evaluate(committed_repo, tree_clean=False, backup_ref=bogus)
    assert not second.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE not in second.blockers
    assert gate.BLOCKER_BACKUP_MISSES_TARGET in second.blockers

    # Guard 2: custody. With both neutered the leg clears, so nothing incidental
    # was producing these refusals.
    monkeypatch.setattr(gate, "_ref_holds_target", lambda root, ref, rel: True)
    assert _evaluate(committed_repo, tree_clean=False, backup_ref=bogus).cleared


def test_uncommitted_allowlist_names_its_own_blocker(tmp_path: Path) -> None:
    """An uncommitted allowlist is reported DISTINCTLY from not-allowlisted.

    Collapsing both into ``TARGET_NOT_ALLOWLISTED`` would tell an operator to
    add a target they already added -- FR-009 requires the specific cause.
    """
    repo = _init_repo(tmp_path)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(repo, f"models/{TARGET}.tmdl", "// m\n")
    _write(repo, "README.md", "x\n")
    _commit_all(repo)
    # Add the allowlist AFTER the commit: present in the worktree, not in HEAD.
    _write(repo, gate.TARGET_ALLOWLIST_RELPATH, _allowlist_yaml())
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_ALLOWLIST_UNCOMMITTED in verdict.blockers


def test_git_state_probe_failure_is_not_a_pass(committed_repo: Path) -> None:
    """A git failure while verifying a backup ref must refuse, not clear.

    ``dagster_adapter/evidence._is_workspace_dirty`` returns False (clean) on an
    exception; this asserts the opposite posture here.
    """

    def _boom(repo_root: Path, *args: str) -> None:
        raise OSError("git unavailable")

    import seshat.pbi_mcp_adapter.gate as gate_module

    original = gate_module.run_git
    try:
        gate_module.run_git = _boom  # type: ignore[assignment]
        verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    finally:
        gate_module.run_git = original  # type: ignore[assignment]
    assert not verdict.cleared
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in verdict.blockers


def test_a_supplied_backup_ref_is_validated_even_on_a_clean_tree(
    committed_repo: Path,
) -> None:
    """Cleanliness satisfying the gate must not leave a supplied ref unchecked.

    `_git_safety` returned early on `tree_clean=True`, skipping both ref
    resolution and the custody check. But `rollback_guidance_for` PREFERS a
    supplied ref, so an unresolvable ref made rollback fail, and a stale one would
    restore an OLDER model rather than the pre-write state -- precisely when the
    operator is relying on the guidance.

    Codex review, PR #659.
    """
    verdict = _evaluate(
        committed_repo, tree_clean=True, backup_ref="refs/tags/no-such-backup"
    )

    assert not verdict.cleared, (
        "a clean tree cleared the gate while carrying an unresolvable backup ref"
    )
    assert gate.BLOCKER_BACKUP_UNRESOLVABLE in verdict.blockers


def test_a_clean_tree_with_no_backup_ref_still_clears(committed_repo: Path) -> None:
    """Positive control: cleanliness alone remains sufficient.

    Without this, a fix that demanded a valid ref unconditionally would satisfy
    the test above while breaking the ordinary clean-tree write.
    """
    verdict = _evaluate(committed_repo, tree_clean=True, backup_ref=None)
    assert verdict.git_safe, verdict.blockers
