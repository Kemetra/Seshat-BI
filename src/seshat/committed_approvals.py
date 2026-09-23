"""Committed-approval reader for the run-next decision surface (audit F045).

An approval in ``readiness-status.yaml`` is a named human's ruling, and it is only
an audit record once it is COMMITTED: a worktree-only entry can be written by
anyone with write access to the checkout and disappears on checkout or revert.
``run_next`` therefore trusts an approval only when the same stage is approved in
BOTH the worktree copy and the ``HEAD`` copy of the file.

Deliberately NOT ``gitstate.committed_text``: that returns ``None`` for a dirty
file, which would also discard every legitimately committed approval the moment
anyone edits an unrelated line. The ``HEAD`` blob is read directly instead.

Fails CLOSED, like every ``gitstate`` probe: no git, not a repository, or a file
that is not committed at ``HEAD`` all read as "no committed approvals".
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

UNCOMMITTED_APPROVAL_KIND = "uncommitted_approval"


def _head_document(repo_root: Path, status_path: Path) -> dict[str, Any] | None:
    import yaml

    from seshat.gitstate import run_git

    root = Path(repo_root).resolve()
    try:
        relative = status_path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        shown = run_git(root, "show", f"HEAD:./{relative}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if shown.returncode != 0 or not shown.stdout:
        return None
    try:
        data = yaml.safe_load(shown.stdout.lstrip("﻿"))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def committed_approvals(repo_root: Path | None, status_path: Path | None) -> object:
    """The ``approvals`` value recorded at ``HEAD``, or ``[]`` when unavailable."""
    if repo_root is None or status_path is None:
        return []
    document = _head_document(repo_root, status_path)
    if document is None:
        return []
    return document.get("approvals", [])


def uncommitted_approval_caveat(stages: set[str]) -> dict[str, str]:
    """Name every stage approved in the worktree but not at ``HEAD``."""
    names = ", ".join(sorted(stages))
    return {
        "kind": UNCOMMITTED_APPROVAL_KIND,
        "detail": (
            f"approval for {names} is not committed at HEAD (an uncommitted "
            "worktree edit, or a workspace outside a git repository) and is not "
            "honoured; commit the named owner's approval so it becomes an audit "
            "record."
        ),
    }
