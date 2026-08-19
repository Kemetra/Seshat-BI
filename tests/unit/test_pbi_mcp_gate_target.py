"""Spec 149 -- the target, containment, operation-binding and backup gates.

Split from ``test_pbi_mcp_gate`` by concern: those suites cover the readiness
record and the approval; these cover what may be written and how safely.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate
from tests.unit._pbi_mcp_gate_fixtures import (
    OPERATION,
    TARGET,
    _allowlist_yaml,
    _build_repo,
    _commit_all,
    _evaluate,
    _git,
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
# Containment: an allowlisted path must not escape the repository
# --------------------------------------------------------------------------


def _repo_with_escaping_path(tmp_path: Path, path_value: str) -> Path:
    """A committed allowlist whose entry points outside the repo."""
    outside = tmp_path / "outside.tmdl"
    outside.write_text("// outside the repo\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        f"targets:\n  - target_id: {TARGET}\n"
        f"    path: {path_value.replace('{OUT}', outside.as_posix())}\n"
        f"    operations:\n      - {OPERATION}\n",
    )
    _write(repo, f"models/{TARGET}.tmdl", "// inside\n")
    _write(repo, "README.md", "fixture\n")
    _commit_all(repo)
    return repo


@pytest.mark.parametrize(
    "path_value",
    [
        pytest.param("../outside.tmdl", id="parent-traversal"),
        pytest.param("models/../../outside.tmdl", id="traversal-via-subdir"),
        pytest.param("{OUT}", id="absolute-path"),
    ],
)
def test_allowlisted_path_escaping_the_repo_refuses(
    tmp_path: Path, path_value: str
) -> None:
    """A write target must be contained by the repo it is governed in.

    The allowlist is committed and reviewed, so an escaping entry would have to
    pass a human -- but "a reviewer would have noticed" is exactly the vigilance
    assumption this gate replaces. Found by attacking the gate after it was
    written: the escape CLEARED every precondition, because containment was
    trusted rather than enforced.
    """
    repo = _repo_with_escaping_path(tmp_path, path_value)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers


def test_escape_is_refused_for_escaping_not_for_being_absent(
    tmp_path: Path,
) -> None:
    """The blocker must name the real cause.

    An escaping path that happens not to exist would otherwise be refused as
    TARGET_ABSENT, telling the operator to create the file -- which is the wrong
    fix and hides the containment breach.
    """
    repo = _repo_with_escaping_path(tmp_path, "../outside.tmdl")
    (tmp_path / "outside.tmdl").unlink()
    verdict = _evaluate(repo)
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers
    assert gate.BLOCKER_TARGET_ABSENT not in verdict.blockers


def test_a_contained_path_still_clears(committed_repo: Path) -> None:
    """The positive control: containment must not refuse legitimate targets."""
    assert _evaluate(committed_repo).cleared


def test_the_repo_root_itself_is_not_a_valid_target(tmp_path: Path) -> None:
    """``path: .`` resolves to the root, which is not a writable artifact."""
    repo = _init_repo(tmp_path)
    _write(repo, f"mappings/{TARGET}/readiness-status.yaml", _readiness_yaml())
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        f"targets:\n  - target_id: {TARGET}\n    path: .\n"
        f"    operations:\n      - {OPERATION}\n",
    )
    _write(repo, "README.md", "fixture\n")
    _commit_all(repo)
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_TARGET_ESCAPES_REPO in verdict.blockers


# --------------------------------------------------------------------------
# CRITICAL: a declared backup must HOLD the target, not merely resolve
# --------------------------------------------------------------------------


def test_backup_ref_head_on_a_dirty_tree_refuses(committed_repo: Path) -> None:
    """``--backup-ref HEAD`` with uncommitted target changes must REFUSE.

    The seventh caller-satisfies-its-own-precondition hole, found by an
    independent review of the built code. HEAD resolves fine and backs up
    NOTHING -- it is precisely where the uncommitted content is not. Worse, the
    rollback guidance would then emit ``git restore --source=HEAD``, destroying
    the operator's uncommitted work and calling it recovery.

    Verifying that a ref RESOLVES is verifying the wrong property; custody is
    what matters.
    """
    target = committed_repo / "models" / f"{TARGET}.tmdl"
    target.write_text("// UNCOMMITTED WORK IN PROGRESS\n", encoding="utf-8")

    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert not verdict.cleared
    assert not verdict.git_safe
    assert gate.BLOCKER_BACKUP_MISSES_TARGET in verdict.blockers


def test_a_backup_ref_that_holds_the_target_clears(committed_repo: Path) -> None:
    """The positive control: a genuine backup DOES satisfy the leg.

    Without this the custody check could refuse every backup and still pass the
    test above. The tree is dirty in a file OTHER than the target, so HEAD
    genuinely holds the target's current content.
    """
    (committed_repo / "README.md").write_text("dirtied elsewhere\n", encoding="utf-8")
    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD")
    assert verdict.git_safe
    assert verdict.cleared


def test_a_stash_style_ref_capturing_the_change_clears(committed_repo: Path) -> None:
    """A ref created AFTER the edit holds it, so it is a real backup.

    Uses ``git stash create``, which writes a commit object without touching the
    worktree -- the realistic way an operator captures work in progress.
    """
    target = committed_repo / "models" / f"{TARGET}.tmdl"
    target.write_text("// work in progress\n", encoding="utf-8")
    created = subprocess.run(
        ["git", "stash", "create"],
        cwd=committed_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    stash_sha = created.stdout.strip()
    assert stash_sha, "git stash create produced no object"

    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref=stash_sha)
    assert verdict.git_safe, verdict.blockers
    assert verdict.cleared


# --------------------------------------------------------------------------
# HIGH: the named human must approve the OPERATION, not just the target
# --------------------------------------------------------------------------


def test_approval_naming_only_the_target_does_not_authorize_an_operation(
    tmp_path: Path,
) -> None:
    """One approval must not authorize every operation on a target forever.

    Before this check, "approved for sales_model" cleared any operation the
    allowlist happened to list -- so "approved" meant "committed to a YAML file",
    not "a named human ruled on this change". FR-011c requires BOTH checks.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(approval_note=f"approved for {TARGET}"),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert verdict.approval_names_target, "the target IS named"
    assert not verdict.approval_names_operation
    assert gate.BLOCKER_APPROVAL_OPERATION in verdict.blockers


def test_approval_naming_target_and_operation_clears(committed_repo: Path) -> None:
    """The positive control for the operation-naming rule."""
    verdict = _evaluate(committed_repo)
    assert verdict.approval_names_operation
    assert verdict.cleared


def test_operation_must_be_named_as_a_whole_token_too(tmp_path: Path) -> None:
    """The same whole-token discipline applies to the operation name.

    An approval naming ``update_measure_draft`` must not authorize
    ``update_measure``.
    """
    repo = _build_repo(
        tmp_path,
        readiness=_readiness_yaml(
            approval_note=f"approved for {TARGET}: {OPERATION}_draft"
        ),
        allowlist=_allowlist_yaml(),
    )
    verdict = _evaluate(repo)
    assert not verdict.cleared
    assert gate.BLOCKER_APPROVAL_OPERATION in verdict.blockers


def test_a_blob_sha_is_not_an_acceptable_backup(committed_repo: Path) -> None:
    """``rev-parse --verify`` accepts a BLOB; ``git restore --source=<blob>`` fails.

    So a blob cleared the gate while the emitted rollback guidance would exit 128
    exactly when the operator needed it. A backup must be restore-capable.
    """
    blob = subprocess.run(
        ["git", "rev-parse", f"HEAD:models/{TARGET}.tmdl"],
        cwd=committed_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert blob, "expected a blob sha"

    target = committed_repo / "models" / f"{TARGET}.tmdl"
    target.write_text("// work in progress\n", encoding="utf-8")

    verdict = _evaluate(committed_repo, tree_clean=False, backup_ref=blob)
    assert not verdict.cleared
    assert gate.BLOCKER_BACKUP_MISSES_TARGET in verdict.blockers


def test_the_emitted_rollback_command_actually_runs_for_an_accepted_ref(
    committed_repo: Path,
) -> None:
    """Whatever the gate accepts as a backup must survive `git restore`.

    Runs the emitted command rather than asserting its shape, which is what
    would have caught the blob case.
    """
    from seshat.pbi_mcp_adapter.validation import rollback_guidance_for

    target = committed_repo / "models" / f"{TARGET}.tmdl"
    original = target.read_text(encoding="utf-8")

    # Accept the ref FIRST, while HEAD still holds the target's current bytes --
    # that is the state a real run is in when the gate clears. Corrupting the file
    # before asking would (correctly) trip PBIMCP-GATE-14, since HEAD would no
    # longer be a backup of what is about to change.
    assert _evaluate(committed_repo, tree_clean=False, backup_ref="HEAD").git_safe

    # Now the "write" happens and goes wrong.
    target.write_text("// corrupted\n", encoding="utf-8")

    command = rollback_guidance_for(f"models/{TARGET}.tmdl", "HEAD")[0]
    completed = subprocess.run(
        command.split("#")[0].strip().split(),
        cwd=committed_repo,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert target.read_text(encoding="utf-8") == original


def test_a_ref_that_lacks_the_target_is_not_a_backup(committed_repo: Path) -> None:
    """A commit that never contained the file cannot be its backup.

    ``git diff`` against a tree lacking the path reports no difference, so a
    diff-only check would accept it.
    """
    _git(committed_repo, "checkout", "-q", "--orphan", "empty-branch")
    _git(committed_repo, "rm", "-rq", "--cached", ".")
    (committed_repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
    _git(committed_repo, "add", "unrelated.txt")
    _git(committed_repo, "commit", "-q", "-m", "orphan", "--no-gpg-sign")
    orphan = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=committed_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert not gate._ref_holds_target(committed_repo, orphan, f"models/{TARGET}.tmdl")
