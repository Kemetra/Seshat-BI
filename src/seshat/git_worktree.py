"""Filter-free worktree comparisons for possibly externally-authored git trees.

``git status``, ``git diff <rev> -- <path>``, ``git add`` and a plain
``git hash-object`` all push worktree content through the repository's own
attribute-selected content filters before comparing it. The filter driver name
comes from the tree's ``.gitattributes`` and its command from the tree's
``.git/config``, so there is no fixed config key ``gitutil.GIT_HARDENING`` could
override: on a downloaded tree those commands execute whatever the tree's
author configured. Every stat entry of a freshly copied tree is dirty, so the
filter runs for every file.

This module answers the same questions without asking git to read worktree
content. Git is used only for commands that read the index, trees and objects
(``rev-parse``, ``ls-files -s``, ``ls-files --others``, ``ls-tree``); the
worktree side is hashed here, in Python, as a git blob.

Comparison semantics (documented because they differ from ``git status`` in two
deliberate, fail-closed ways):

* A worktree file matches a recorded blob when either its raw bytes or its
  CRLF->LF normalized bytes hash to the recorded id. Without the normalized form
  every Windows ``core.autocrlf`` checkout would read dirty. The consequence is
  that a change which ONLY swaps LF for CRLF reads clean where git would call it
  modified -- harmless here, because every consumer trusts the committed content,
  never the worktree bytes.
* Anything that cannot be reproduced without running the tree's configuration --
  a content-filtered file (e.g. LFS), a ``working-tree-encoding`` file, a path
  with ``..`` components or one resolving outside the root -- reads as modified.
  Mode-only changes (the executable bit) are not reported; gitlinks (submodules)
  are compared by recorded commit only.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from seshat.gitutil import GIT_HARDENING, run_subprocess

_GITLINK_MODE = "160000"
_SYMLINK_MODE = "120000"
_HASH_BY_OID_LENGTH = {40: "sha1", 64: "sha256"}


@dataclass(frozen=True)
class WorktreeStatus:
    """The filter-free equivalent of ``git status --porcelain --untracked-files=all``.

    ``modified`` holds every path whose worktree content differs from the index,
    whose index entry differs from HEAD (staged adds, edits and deletions), or
    that is in a conflicted state. ``untracked`` holds non-ignored files git
    does not track. Paths are relative to the queried root, POSIX-style.
    """

    modified: tuple[str, ...]
    untracked: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.modified and not self.untracked

    @property
    def paths(self) -> tuple[str, ...]:
        return (*self.modified, *self.untracked)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """One hardened, content-filter-free git read rooted at ``root`` (bytes out)."""
    return run_subprocess(
        [
            "git",
            *GIT_HARDENING,
            "-c",
            f"safe.directory={root.as_posix()}",
            "--literal-pathspecs",
            *args,
        ],
        cwd=root,
        capture_output=True,
        check=False,
        shell=False,
    )


def _records(stdout: bytes) -> list[tuple[str, str]]:
    """Split ``-z`` output of ``<meta>\\t<path>`` records into (meta, path)."""
    records: list[tuple[str, str]] = []
    for raw in stdout.split(b"\0"):
        if not raw:
            continue
        meta, _, path = raw.partition(b"\t")
        records.append(
            (meta.decode("ascii"), path.decode("utf-8", errors="surrogateescape"))
        )
    return records


def blob_id(data: bytes, algorithm: str = "sha1") -> str:
    """The git object id of ``data`` stored as a blob (no filters applied)."""
    digest = hashlib.new(algorithm)
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def blob_ids(data: bytes, algorithm: str = "sha1") -> frozenset[str]:
    """The blob ids ``data`` may be recorded under: raw, and CRLF->LF normalized."""
    ids = {blob_id(data, algorithm)}
    if b"\r\n" in data:
        ids.add(blob_id(data.replace(b"\r\n", b"\n"), algorithm))
    return frozenset(ids)


def _contained_file(root: Path, relative: str) -> Path | None:
    """``root/relative`` when it provably stays inside ``root``; else None."""
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or ".." in parts:
        return None
    candidate = root.joinpath(*parts)
    try:
        candidate.parent.resolve(strict=False).relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def _worktree_bytes(root: Path, relative: str, mode: str) -> bytes | None:
    """The bytes git would hash for this entry, or None when unreproducible."""
    candidate = _contained_file(root, relative)
    if candidate is None:
        return None
    try:
        if candidate.is_symlink():
            if mode != _SYMLINK_MODE:
                return None  # type change: regular file replaced by a link
            return os.fsencode(os.readlink(candidate)).replace(b"\\", b"/")
        if not candidate.is_file():
            return None
        # A symlink recorded on a checkout with core.symlinks=false is a plain
        # file holding the link target -- its bytes hash to the same blob.
        return candidate.read_bytes()
    except OSError:
        return None


def worktree_matches(root: Path, relative: str, mode: str, oid: str) -> bool:
    """Does the worktree copy of ``relative`` hold the blob ``oid``?"""
    if mode == _GITLINK_MODE:
        return True  # a submodule's content is its own repository's business
    algorithm = _HASH_BY_OID_LENGTH.get(len(oid))
    if algorithm is None:
        return False
    data = _worktree_bytes(root, relative, mode)
    return data is not None and oid in blob_ids(data, algorithm)


def _index_entries(root: Path, pathspecs: tuple[str, ...]) -> list[tuple[str, ...]]:
    listed = _git(root, "ls-files", "-s", "-z", "--", *pathspecs)
    if listed.returncode != 0:
        raise RuntimeError("git ls-files -s failed")
    entries = []
    for meta, path in _records(listed.stdout):
        mode, oid, stage = meta.split(" ")
        entries.append((path, mode, oid, stage))
    return entries


def _head_entries(root: Path, pathspecs: tuple[str, ...]) -> dict[str, str]:
    """``{path: "<mode> <oid>"}`` at HEAD; empty for an unborn branch."""
    if _git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode != 0:
        return {}
    listed = _git(root, "ls-tree", "-r", "-z", "HEAD", "--", *pathspecs)
    if listed.returncode != 0:
        raise RuntimeError("git ls-tree failed")
    entries: dict[str, str] = {}
    for meta, path in _records(listed.stdout):
        mode, _kind, oid = meta.split(" ")
        entries[path] = f"{mode} {oid}"
    return entries


def _modified(root: Path, pathspecs: tuple[str, ...]) -> set[str]:
    head = _head_entries(root, pathspecs)
    modified: set[str] = set()
    indexed: set[str] = set()
    for path, mode, oid, stage in _index_entries(root, pathspecs):
        indexed.add(path)
        if stage != "0" or head.get(path) != f"{mode} {oid}":
            modified.add(path)  # conflicted, or staged relative to HEAD
        elif not worktree_matches(root, path, mode, oid):
            modified.add(path)
    modified.update(path for path in head if path not in indexed)  # staged delete
    return modified


def worktree_status(root: Path | str, *pathspecs: str) -> WorktreeStatus | None:
    """Filter-free status of ``root`` (optionally limited to ``pathspecs``).

    None when ``root`` is not inside a work tree or git fails -- callers decide
    how to fail closed. Never runs a repository-configured content filter.
    """
    base = Path(root)
    try:
        probe = _git(base, "rev-parse", "--is-inside-work-tree")
        if probe.returncode != 0 or probe.stdout.strip() != b"true":
            return None
        modified = _modified(base, pathspecs)
        others = _git(
            base, "ls-files", "--others", "--exclude-standard", "-z", "--", *pathspecs
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        return None
    if others.returncode != 0:
        return None
    untracked = tuple(
        raw.decode("utf-8", errors="surrogateescape")
        for raw in others.stdout.split(b"\0")
        if raw
    )
    return WorktreeStatus(modified=tuple(sorted(modified)), untracked=untracked)


def repository_status(root: Path | str) -> tuple[WorktreeStatus, str] | None:
    """Whole-repository status for a root that may sit BELOW the git toplevel.

    :func:`worktree_status` sees only the subtree under the directory it runs
    in, while ``git status`` covers the whole repository. A precondition that
    means "the repository is clean" (a scaffold's or a write's git-safety check)
    must not go blind to a dirty file outside the subdirectory it was pointed
    at. Returns the status (paths relative to the TOPLEVEL) and ``root``'s
    prefix from the toplevel (``""`` or ``"sub/dir/"``), or None on failure.
    """
    base = Path(root)
    try:
        top = _git(base, "rev-parse", "--show-toplevel")
        prefix = _git(base, "rev-parse", "--show-prefix")
    except (OSError, subprocess.SubprocessError):
        return None
    if top.returncode or prefix.returncode:
        return None
    toplevel = Path(top.stdout.decode("utf-8", errors="surrogateescape").strip())
    status = worktree_status(toplevel)
    if status is None:
        return None
    return status, prefix.stdout.decode("utf-8", errors="surrogateescape").strip()


def worktree_matches_revision(root: Path | str, rev: str, relative: str) -> bool:
    """Is ``relative`` present at ``rev`` with exactly the worktree's content?

    The filter-free replacement for ``git diff --quiet <rev> -- <relative>``,
    except that a path absent from ``rev`` is a mismatch (fail closed) rather
    than "no difference". An option-shaped ``rev`` is refused outright.
    """
    base = Path(root)
    if not rev or rev.startswith("-"):
        return False
    try:
        listed = _git(base, "ls-tree", "-z", rev, "--", relative)
    except (OSError, subprocess.SubprocessError):
        return False
    if listed.returncode != 0:
        return False
    records = _records(listed.stdout)
    if len(records) != 1 or records[0][1] != relative:
        return False
    mode, kind, oid = records[0][0].split(" ")
    return kind == "blob" and worktree_matches(base, relative, mode, oid)
