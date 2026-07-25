from __future__ import annotations

import subprocess
from pathlib import Path

from seshat.core import RuleContext


def make_git_repo(tmp_path: Path) -> Path:
    """Init a deterministic git repo at tmp_path/repo with identity and main branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def make_kit_self_repo(repo: Path) -> Path:
    """Give ``repo`` the markers that identify it as the kit's OWN source repo.

    The KIT_SELF rule tier activates on kit IDENTITY -- the kit's package source
    plus a ``seshat-bi`` distribution declaration -- not on ``.seshat/`` substrate
    presence, which ``seshat init`` writes into consumer repos too (issue #486).
    Tests that want the kit-self checks to actually RUN must shape the fixture
    this way; see ``seshat.kit_lint.is_kit_self_repo``.
    """
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    pkg = repo / "src" / "seshat"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    return repo


def commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True
    )


def context_for(repo: Path) -> RuleContext:
    out = subprocess.run(
        ["git", "ls-files"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
    tracked = tuple(line for line in out.splitlines() if line)
    return RuleContext(repo_root=repo, tracked_files=tracked)
