"""Shared fixtures for the spec-140 workbench tests.

Builds on `_studio_workspace_fixtures` rather than hand-rolling readiness documents: a
fixture only these tests can read would make the suite green while proving nothing
about the shipped readers.

Paths are derived from the shipped `decision_store.STORE_PATHS` and built with
`pathlib`, never hardcoded separators -- the CI `unit` job runs `ubuntu-latest` only,
so a POSIX-locked fixture stays green in CI forever and fails only on Windows
(issue #691).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from unit import _studio_workspace_fixtures as workspace_fixtures

from seshat import decision_store

API = "/api/v1"
_BASE_URL = "http://127.0.0.1:9999"
_BROWSER_ORIGIN = {"Origin": _BASE_URL}

#: The semantic-decisions store file, taken from the shipped constant so this fixture
#: cannot drift from the path the gate reads.
SEMANTIC_DECISIONS = decision_store.STORE_PATHS[0]


def _app(root: Path, *, table: str):
    """A Studio app over a workspace holding one ready table, plus its token.

    `fastapi` is imported INSIDE the functions that need it, not at module scope. The
    CI `unit` job installs no app extras, so a module-level import would make every
    module that merely imports these fixtures die at COLLECTION -- including the
    decision-write tests, which need no web stack at all.
    """
    # DO NOT HOIST to module scope: `ruff check --fix` has done exactly that once, and
    # it re-broke CI's extras-free `unit` job. Verify with `grep -c '^from fastapi'`
    # after any lint --fix on this file.
    from fastapi.testclient import TestClient

    from seshat.studio.app import create_app

    workspace_fixtures.write_ready_table(root, table=table)
    app, token = create_app(root, port=9999)
    client = TestClient(app, base_url=_BASE_URL, headers=dict(_BROWSER_ORIGIN))
    return client, token


def studio_client(root: Path, *, table: str = "ready_sales"):
    """An authenticated TestClient over a real workspace."""
    client, token = _app(root, table=table)
    bootstrapped = client.post(f"{API}/bootstrap", params={"token": token})
    assert bootstrapped.status_code == 204, bootstrapped.text
    return client


def unauthenticated_client(root: Path, *, table: str = "ready_sales"):
    """The same app with bootstrap deliberately NOT performed.

    Exists so a test can prove the authenticated client's success came from
    authentication rather than from a missing guard.
    """
    client, _ = _app(root, table=table)
    return client


@dataclass(frozen=True)
class GitWorkspace:
    """A real git repo, so committed-vs-uncommitted state is genuinely testable."""

    root: Path

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            # fsmonitor off: the repo's own hardening for untrusted/temporary trees.
            ["git", "-c", "core.fsmonitor=false", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def commit_all(self, message: str) -> None:
        self._git("add", "-A")
        self._git(
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--no-gpg-sign",
            "-m",
            message,
        )

    def head_sha(self) -> str:
        return self._git("rev-parse", "HEAD")

    def tracked_files_at_head(self) -> tuple[str, ...]:
        """Repo-relative tracked paths at HEAD, in the shape `store_files` expects."""
        listed = self._git("ls-tree", "-r", "--name-only", "HEAD")
        return tuple(line for line in listed.splitlines() if line)

    def file_at_head(self, relative: str) -> str | None:
        """The committed content of one path at HEAD, or None if absent there."""
        try:
            return self._git("show", f"HEAD:{relative}")
        except subprocess.CalledProcessError:
            return None


def git_workspace(root: Path) -> GitWorkspace:
    """Initialise `root` as a real git repo with a committer identity."""
    workspace = GitWorkspace(root)
    workspace._git("init", "-q")
    workspace._git("config", "user.email", "test@example.invalid")
    workspace._git("config", "user.name", "Test Runner")
    return workspace


def store_file(root: Path, *, relative: str = SEMANTIC_DECISIONS) -> Path:
    """The decision store file, created empty if absent.

    `relative` defaults to the shipped semantic-decisions path; pass another member of
    `decision_store.STORE_PATHS` for the other stores.
    """
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("decisions: []\n", encoding="utf-8")
    return path
