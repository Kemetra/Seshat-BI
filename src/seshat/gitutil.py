from __future__ import annotations

import re
import subprocess
from pathlib import Path

# A safe git revision-range shape: one or two refs joined by `..`/`...`, built
# from ref-name chars only. Crucially it must NOT start with `-`, or git would
# parse it as an OPTION (`--output=...`, `-n1`) rather than a revision -- a
# CI-input option-injection surface (audit 2026-06-26 #24).
# `\Z` (not `$`): in Python `$` also matches just before a trailing newline, so a
# `"a..b\n"` would pass and be handed to git verbatim. `\Z` anchors the true end.
_SAFE_RANGE_RE = re.compile(r"^[A-Za-z0-9_][\w./~^@-]*(\.\.\.?[\w./~^@-]+)?\Z")
# Cap on stderr spliced into an error message so a failing git command cannot dump
# unbounded (or sensitive) output into a RuntimeError / Finding (audit #27).
_STDERR_LIMIT = 300

# git's "not a git repository" sentinel exit code (the expected non-repo case,
# e.g. a fresh pip-only workspace before `git init`). Mirrors the same-named
# constant in ``runner`` so the two git wrappers treat the condition identically.
_GIT_NOT_A_REPO = 128

# `repo_root` here can be an EXTERNALLY-AUTHORED tree -- notably a downloaded PBIP
# project the user runs `seshat adopt-pbip` against, reached via the adoption
# seams. `git -C <tree>` (like cwd=<tree>) makes git read THAT tree's own
# `.git/config`, so an attacker-supplied `core.fsmonitor` (a command git runs on
# status/check-ignore/ls-files) or `core.hooksPath` executes in the analyst's
# shell -- arbitrary code execution from merely assessing a project.
# `safe.directory` does NOT help: the victim owns the extracted files, so the
# dubious-ownership block never fires. These flags neutralize the config-driven
# exec vectors at the shared git wrapper and are a harmless no-op on a trusted
# repo (fsmonitor is only an optimization). Keep in sync with
# pbip_adoption._safety.GIT_UNTRUSTED_TREE_HARDENING.
_GIT_HARDENING = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "protocol.ext.allow=never",
)


def validate_commit_range(range_expr: str) -> str:
    """Return ``range_expr`` if it is a safe git revision range, else ``ValueError``.

    Rejects anything starting with ``-`` (git option injection) or containing
    characters outside the conservative ref-name set. The caller passes the result
    to ``git log`` as a positional revision argument.
    """
    if not isinstance(range_expr, str) or not _SAFE_RANGE_RE.match(range_expr):
        raise ValueError(f"unsafe git commit range: {range_expr!r}")
    return range_expr


def git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *_GIT_HARDENING, "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # non-UTF-8 bytes on git's stderr must not crash the decode
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if len(stderr) > _STDERR_LIMIT:
            # ASCII marker only -- a non-ASCII char raises UnicodeEncodeError on a
            # Windows charmap console (cp437/cp850); see global encoding rule.
            stderr = stderr[:_STDERR_LIMIT] + "... (truncated)"
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): {stderr}"
        )
    return result.stdout


def git_check_ignore(repo_root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", *_GIT_HARDENING, "-C", str(repo_root), "check-ignore", "-q", path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    if result.returncode == _GIT_NOT_A_REPO:
        # `repo_root` is not a git repository (e.g. a pip-only client's fresh
        # workspace before `git init`). Nothing can be gitignored there, so the
        # answer is a clean "not ignored" -- NOT a crash (#371). Mirrors the
        # exit-128 tolerance in runner._git_ls_files, so the two sibling helpers
        # agree on the identical "not a repo" condition.
        return False
    raise RuntimeError(f"git check-ignore error ({result.returncode}): {result.stderr}")


def git_log_subjects(repo_root: Path, range_expr: str) -> list[str]:
    """Return the commit subjects in ``range_expr`` (excluding merges).

    ``range_expr`` is validated as a safe revision range (no leading ``-``, ref
    chars only) before use — it is then passed as a positional git-log revision
    (e.g. ``"origin/main..HEAD"`` or ``"HEAD~20..HEAD"``). An unsafe range raises
    ``ValueError``; a git-rejected (but safe-shaped) range raises ``RuntimeError``
    via :func:`git_output`, so neither silently no-op's.
    """
    range_expr = validate_commit_range(range_expr)
    out = git_output(repo_root, "log", "--no-merges", range_expr, "--format=%s")
    return [line for line in out.splitlines() if line]
