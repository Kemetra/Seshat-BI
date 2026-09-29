"""Commit a file into a tmp repository, for gates that read HEAD, not the worktree."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def commit_file(repo: Path, relpath: str, text: str) -> Path:
    """Write ``relpath`` under ``repo`` and commit it (initialising git if needed)."""
    if not (repo / ".git").exists():
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@example.com")
        _git(repo, "config", "user.name", "T")
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-qm", f"add {relpath}", "--no-gpg-sign")
    return path
