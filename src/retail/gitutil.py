from __future__ import annotations

import subprocess
from pathlib import Path


def git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): {result.stderr}"
        )
    return result.stdout


def git_check_ignore(repo_root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError(f"git check-ignore error ({result.returncode}): {result.stderr}")


def git_log_subjects(repo_root: Path, range_expr: str) -> list[str]:
    """Return the commit subjects in ``range_expr`` (excluding merges).

    ``range_expr`` is used VERBATIM as the git-log revision range
    (e.g. ``"origin/main..HEAD"`` or ``"HEAD~20..HEAD"``) — the caller owns
    range construction. Raises ``RuntimeError`` (via :func:`git_output`) if git
    rejects the range, so a malformed range surfaces to the caller rather than
    silently no-op'ing.
    """
    out = git_output(repo_root, "log", "--no-merges", range_expr, "--format=%s")
    return [line for line in out.splitlines() if line]
