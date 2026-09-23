"""Semantic-input discovery (metric contracts + TMDL) for gates and reports.

Domain home of the discovery ``semantic-check``, Portfolio Watch and the PBI MCP
post-write validator share, so a domain module never imports a private CLI
helper. Tracked mode reads COMMITTED state and fails closed:

  * a workspace with no ``.git`` anywhere above it has no committed state, so
    it is inspected from the working tree and reported as ``filesystem`` mode;
  * a workspace INSIDE a git repository is read from the index with
    ``git ls-files`` -- a project nested in a larger repository is scoped to its
    own subtree, never widened to an untracked working-tree walk;
  * a git failure inside a repository (e.g. dubious ownership in a container)
    raises :class:`SemanticInputsUnavailable` -- it is never silently replaced
    by a working-tree walk that would admit uncommitted files.

Stdlib-only at import time.
"""

from __future__ import annotations

from pathlib import Path

from .gitutil import GIT_HARDENING, run_subprocess

__all__ = [
    "MODE_FILESYSTEM",
    "MODE_GIT",
    "MODE_WORKTREE",
    "SemanticInputsUnavailable",
    "discover_semantic_inputs",
    "git_worktree_dirty",
    "inside_git_repository",
    "semantic_files",
]

MODE_GIT = "git"
MODE_FILESYSTEM = "filesystem"
MODE_WORKTREE = "worktree"


class SemanticInputsUnavailable(RuntimeError):
    """Committed semantic inputs cannot be established (git refused)."""


def inside_git_repository(repo: Path) -> bool:
    """True when ``repo`` or any ancestor carries a ``.git`` entry."""
    return any((path / ".git").exists() for path in (repo, *repo.parents))


def _is_input(repo: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        return False
    if rel.startswith("tests/") or "/tests/" in rel:
        return False
    return ("/metrics/" in f"/{rel}" and rel.endswith(".yaml")) or (
        ".SemanticModel/definition/" in rel and rel.endswith(".tmdl")
    )


def _git(repo: Path, *args: str) -> str:
    """Run one read-only git command against ``repo``; raise on any failure.

    Carries the ``safe.directory`` opt-in Portfolio Watch's revision readers use
    (container-mounted checkouts owned by another UID), paired with the shared
    hardening flags so a poisoned ``.git/config`` cannot execute anything.
    """
    try:
        result = run_subprocess(
            [
                "git",
                *GIT_HARDENING,
                "-c",
                f"safe.directory={repo.as_posix()}",
                "-C",
                str(repo),
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise SemanticInputsUnavailable(f"git could not run: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        raise SemanticInputsUnavailable(
            f"git {args[0]} failed ({result.returncode}): "
            f"{detail[0] if detail else 'no detail'}"
        )
    return result.stdout


def _worktree_inputs(repo: Path) -> tuple[Path, ...]:
    candidates = sorted(repo.rglob("*.yaml")) + sorted(repo.rglob("*.tmdl"))
    return tuple(path for path in candidates if _is_input(repo, path))


def discover_semantic_inputs(
    repo: Path, include_untracked: bool
) -> tuple[tuple[Path, ...], str]:
    """Return ``(inputs, mode)``; raise when committed inputs are unknowable."""
    repo = repo.resolve()
    if include_untracked:
        return _worktree_inputs(repo), MODE_WORKTREE
    if not inside_git_repository(repo):
        return _worktree_inputs(repo), MODE_FILESYSTEM
    # `ls-files` run from `repo` lists only its subtree, relative to it, so a
    # project nested inside a larger repository needs no special case.
    raw = _git(repo, "ls-files", "-z")
    inputs = tuple(
        repo / Path(rel)
        for rel in raw.split("\0")
        if rel and _is_input(repo, repo / rel)
    )
    return inputs, MODE_GIT


def semantic_files(repo: Path, include_untracked: bool) -> tuple[Path, ...]:
    """The discovered semantic inputs (see :func:`discover_semantic_inputs`)."""
    return discover_semantic_inputs(repo, include_untracked)[0]


def git_worktree_dirty(repo: Path, *pathspecs: str) -> bool:
    """True when any pathspec has uncommitted or untracked changes; raises on error."""
    return bool(
        _git(repo, "status", "--porcelain", "--untracked-files=all", "--", *pathspecs)
    )
