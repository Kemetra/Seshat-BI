from __future__ import annotations

import os
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
# repo (fsmonitor is only an optimization).
#
# THE single definition: every module that shells out to git against a
# possibly-externally-authored tree imports `GIT_HARDENING` from here. It was
# previously re-listed locally in ~10 modules under a manual "keep in sync"
# comment, and that contract drifted -- `cli/commands/dbt.py` carried only
# `core.fsmonitor`, leaving hooksPath/protocol.ext live on a user-supplied
# `--repo` tree. A shared constant makes that drift impossible; the
# `test_git_hardening_has_a_single_definition` regression test enforces it.
# `os.devnull` (not the "/dev/null" literal) so the hooksPath override names a
# real null sink on Windows too -- several call sites already did this and the
# shared tuple must not regress them to the Unix-only spelling.
GIT_HARDENING = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "protocol.ext.allow=never",
)

# Back-compat alias for in-package callers that referenced the private name.
_GIT_HARDENING = GIT_HARDENING

# Default wall-clock cap for a subprocess. A governance helper that hangs is worse
# than one that fails: the CLI prints nothing and an MCP client waits forever with
# no way to tell "slow" from "dead". Generous enough for `git ls-files` on a large
# repo, short enough that a deadlock surfaces as a LOUD error.
SUBPROCESS_TIMEOUT = 120


def run_subprocess(
    args: list[str] | tuple[str, ...],
    **kwargs: object,
) -> subprocess.CompletedProcess:
    """``subprocess.run`` with the two settings every call site here needs.

    **``stdin=DEVNULL`` is load-bearing, not hygiene.** A child spawned without an
    explicit ``stdin`` INHERITS the parent's. When the parent is the governor MCP
    server (``seshat mcp``), that inherited handle is the live JSON-RPC pipe from
    the client: the child blocks reading a pipe only the MCP client can feed, the
    parent blocks in ``communicate()`` waiting for the child, and neither moves.

    That is issue #557 -- `seshat_run_static_check` hung indefinitely (>11 min
    observed) while the identical logic ran in 12s from the CLI, because a CLI's
    stdin is a terminal and inheriting it is harmless. Reproduced and fixed A/B
    over a real stdio pipe: unpatched hangs, ``stdin=DEVNULL`` returns in 0.0s.

    ``timeout`` converts any residual stall into ``TimeoutExpired`` instead of an
    unbounded wait, matching ``_git_ls_files``'s "fail LOUD rather than silently
    green" contract.

    **Deliberately NOT routed through here** -- the dbt/dagster execution runners
    (``dbt/gate.py``, ``dbt/runner.py``, ``dbt/scaffold/orchestrator.py``,
    ``dagster_adapter/runner.py``, ``cli/commands/dbt.py``). Those invoke
    user-authored builds that legitimately run longer than ``SUBPROCESS_TIMEOUT``,
    so a shared cap would abort real work. They are also not reachable from the
    read-only governor tools, so they do not carry the #557 deadlock. If any of
    them is ever exposed over stdio, give it ``stdin=DEVNULL`` and a timeout sized
    to that workload -- do not adopt this helper's cap.
    """
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("timeout", SUBPROCESS_TIMEOUT)
    return subprocess.run(args, **kwargs)  # type: ignore[call-overload]  # noqa: S603


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
    result = run_subprocess(
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
    result = run_subprocess(
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
