"""Hardened, read-only git state probes shared by governance gates (#334).

Governance artifacts (the unresolved-questions mirror, readiness status) are
only audit records once COMMITTED: a worktree-only edit can disappear on
checkout or revert, leaving an unaudited clearance behind. These probes let a
gate verify that the artifact it is about to trust is tracked and clean, and
read the committed (HEAD) content instead of the worktree. All probes fail
CLOSED: no git, not a repository, untracked, or dirty all read as
not-committed. The git invocation is hardened the same way as
``seshat.dbt.gate`` (no fsmonitor, no hooks, no ext protocol).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from seshat.gitutil import GIT_HARDENING, run_subprocess


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one hardened, read-only git command rooted at ``repo_root``."""
    command = [
        "git",
        *GIT_HARDENING,
        "-c",
        f"safe.directory={repo_root.as_posix()}",
        *args,
    ]
    return run_subprocess(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )


def is_tracked_and_clean(repo_root: Path, relative: str) -> bool:
    """True only when ``relative`` is tracked AND identical to its HEAD state."""
    root = Path(repo_root).resolve()
    tracked = run_git(root, "ls-files", "--error-unmatch", "--", relative)
    if tracked.returncode != 0:
        return False
    clean = run_git(root, "diff", "--quiet", "HEAD", "--", relative)
    return clean.returncode == 0


def committed_text(repo_root: Path, relative: str) -> str | None:
    """The committed (HEAD) content of a tracked, clean file; None otherwise."""
    root = Path(repo_root).resolve()
    if not is_tracked_and_clean(root, relative):
        return None
    shown = run_git(root, "show", f"HEAD:{relative}")
    if shown.returncode != 0:
        return None
    return shown.stdout
