from __future__ import annotations

import subprocess
from pathlib import Path

from .core import Finding, RegisteredRule, RuleContext, Severity

# git's "not a git repository" sentinel exit code (the expected non-repo case).
_GIT_NOT_A_REPO = 128


def _git_ls_files(repo_root: Path) -> tuple[str, ...]:
    """Return repo-relative POSIX paths for every tracked file.

    Dispatches on the git exit code so a governance gate never passes
    vacuously on a broken git:

    * ``0``   -> the tracked-file list.
    * ``128`` -> ``repo_root`` is not a git repository (e.g. a bare tmp dir in
      tests); return ``()`` — the expected non-repo case.
    * any other non-zero code -> ``RuntimeError`` so CI misconfiguration fails
      LOUD (red) rather than silently green.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == _GIT_NOT_A_REPO:
        return ()
    if result.returncode != 0:
        raise RuntimeError(
            f"git ls-files failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    # git ls-files already emits forward slashes; split on newlines, drop blanks.
    return tuple(line for line in result.stdout.splitlines() if line)


def build_context(
    repo_root: Path,
    commit_range: str | None = None,
    commit_message: str | None = None,
) -> RuleContext:
    """Build the read-only context every rule receives.

    ``commit_range`` and ``commit_message`` are the contract-v2 invocation
    fields: populated by the CLI flags ``--commit-range`` / ``--commit-msg-file``
    and consumed by P2. Both default to ``None`` (no commit context), which is
    the local ``retail check`` mode.
    """
    return RuleContext(
        repo_root=repo_root,
        tracked_files=_git_ls_files(repo_root),
        commit_range=commit_range,
        commit_message=commit_message,
    )


def _format(finding: Finding) -> str:
    return (
        f"[{finding.severity.value}] {finding.rule_id} "
        f"{finding.message} ({finding.locator})"
    )


def run(rules: tuple[RegisteredRule, ...], ctx: RuleContext) -> int:
    exit_code = 0
    for registered in rules:
        for finding in registered.rule(ctx):
            print(_format(finding))
            if finding.severity is Severity.ERROR:
                exit_code = 1
    return exit_code
