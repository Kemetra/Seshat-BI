"""Path containment and committed-blob reads for ``narrative_check``.

Split out of ``narrative_check`` (already past the size budget). Two guards:

  * every path a brief or binding map names is resolved and must stay inside
    ``mappings/<table>/`` -- a contract id like ``../../x`` or a map pointing at
    another table's (or an out-of-repo) brief is refused, never read;
  * a contract revision is compared against the COMMITTED blob (``HEAD:path``)
    when the workspace is a git repository, and an uncommitted edit is reported
    separately rather than silently satisfying (or breaking) the citation.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from .git_worktree import blob_id, blob_ids
from .gitstate import run_git
from .gitutil import committed_ref

__all__ = ["BlobState", "contained_brief_path", "contained_contract_path", "blob_state"]


class BlobState(NamedTuple):
    """The worktree blob and, inside a git repository, the committed blob."""

    worktree: str | None
    committed: str | None
    in_repository: bool


def _inside(path: Path, parent: Path) -> bool:
    try:
        return path.resolve().is_relative_to(parent.resolve())
    except (OSError, ValueError):
        return False


def contained_contract_path(repo_root: Path, table: str, cid: str) -> Path | None:
    """``mappings/<table>/metrics/<cid>.yaml``, or None when it would escape."""
    metrics = repo_root / "mappings" / table / "metrics"
    path = metrics / f"{cid}.yaml"
    if not _inside(repo_root / "mappings" / table, repo_root / "mappings"):
        return None
    if path.resolve().parent != metrics.resolve():
        return None
    return path


def contained_brief_path(
    repo_root: Path, table: str, brief_ref: str | None
) -> Path | None:
    """The table's own ``narrative-brief.md``; None for any other reference.

    ``check_narrative`` validates exactly that file, so a map may only be
    grounded against it -- never another table's brief or an arbitrary path.
    """
    canonical = repo_root / "mappings" / table / "narrative-brief.md"
    if brief_ref is None:
        return canonical
    candidate = repo_root / brief_ref
    if not _inside(canonical.parent, repo_root / "mappings"):
        return None
    try:
        same = candidate.resolve() == canonical.resolve()
    except OSError:
        return None
    return canonical if same else None


def _git_sha(repo_root: Path, *args: str) -> str | None:
    result = run_git(repo_root, *args)
    return result.stdout.strip() if result.returncode == 0 else None


def _in_governed_repo(repo_root: Path) -> bool:
    if (repo_root / ".git").exists():
        return True
    # A parent repository may contain a temporary workspace without tracking
    # any of its files. Treat that workspace as standalone.
    result = run_git(repo_root, "ls-files", "-z")
    return result.returncode == 0 and bool(result.stdout)


def blob_state(repo_root: Path, path: Path) -> BlobState:
    """Worktree and committed blob shas of ``path`` (None when unavailable)."""
    try:
        data = path.read_bytes() if path.is_file() else None
    except OSError:
        data = None
    in_repository = _in_governed_repo(repo_root)
    committed = None
    if in_repository:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
        committed = _git_sha(repo_root, "rev-parse", committed_ref("HEAD", rel))
    algorithm = "sha256" if committed is not None and len(committed) == 64 else "sha1"
    # Git's ordinary text checkout hashes the LF form under core.autocrlf.
    worktree = (
        blob_id(data.replace(b"\r\n", b"\n"), algorithm) if data is not None else None
    )
    if data is not None and committed in blob_ids(data, algorithm):
        worktree = committed
    return BlobState(worktree, committed, in_repository)
