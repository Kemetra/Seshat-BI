"""Shared fixtures for the spec-149 write-gate suites.

US2 is built BEFORE US1 deliberately: the refusal path IS the governance, and
building the write path first would leave a window in which mutation exists
without a proven gate.

**The fixtures COMMIT their records.** An earlier draft of this suite wrote
readiness records to the worktree and asserted they cleared, which encoded the
worst fail-open in the feature -- an agent authoring its own approval -- as
correct behavior, with a green suite. ``committed_repo`` therefore runs real
``git`` commands, and ``test_uncommitted_but_passing_record_refuses`` is the
positive control that proves the committed-state check is load-bearing.

Two repo-earned bars enforced structurally, not by convention:

* **No absence-assertions.** Nothing asserts a symbol is missing; every test
  asserts an observable verdict, so it cannot go green when a capability ships in
  a different shape.
* **No vacuous branches.** The precondition suite is hold-N-break-one AND asserts
  a refusal COUNT, so a branch that stopped being exercised is visible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate

TARGET = "sales_model"
OTHER_TARGET = "returns_model"
#: An operation id the committed allowlist approves for TARGET.
OPERATION = "update_measure"
#: A shape-valid owner: a named decider WITH an authority class. A bare name is
#: rejected by ``approval_is_shape_valid`` (issue #487), which is why the earlier
#: draft's ``owner: Ahmed Shaaban`` was itself wrong.
OWNER = "Ahmed Shaaban (data_owner)"


def _readiness_yaml(
    *,
    target: str = TARGET,
    semantic_status: str = "pass",
    approval_note: str | None = None,
    approval_stage: str = "publish_ready",
    owner: str = OWNER,
    include_approval: bool = True,
) -> str:
    note = (
        f"approved for {target}: {OPERATION}"
        if approval_note is None
        else approval_note
    )
    body = (
        "stages:\n"
        f"  semantic_model_ready:\n    status: {semantic_status}\n"
        "  publish_ready:\n    status: pass\n"
    )
    if include_approval:
        body += (
            "approvals:\n"
            f"  - stage: {approval_stage}\n"
            f"    owner: {owner!r}\n"
            "    at: '2026-08-18'\n"
            f"    note: {note!r}\n"
        )
    return body


def _allowlist_yaml(targets: tuple[str, ...] = (TARGET,)) -> str:
    if not targets:
        return "targets: []\n"
    rows = "".join(
        f"  - target_id: {name}\n"
        f"    path: models/{name}.tmdl\n"
        "    operations:\n"
        f"      - {OPERATION}\n"
        for name in targets
    )
    return f"targets:\n{rows}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def _write(repo: Path, relpath: str, text: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message, "--no-gpg-sign")


def _build_repo(
    tmp_path: Path,
    *,
    readiness: str | None = None,
    allowlist: str | None = None,
    artifacts: tuple[str, ...] = (TARGET,),
    target: str = TARGET,
    commit: bool = True,
) -> Path:
    """A repo with the requested state, committed unless told otherwise."""
    repo = _init_repo(tmp_path)
    if readiness is not None:
        _write(repo, f"mappings/{target}/readiness-status.yaml", readiness)
    if allowlist is not None:
        _write(repo, gate.TARGET_ALLOWLIST_RELPATH, allowlist)
    for name in artifacts:
        _write(repo, f"models/{name}.tmdl", f"// {name}\n")
    # A repo needs at least one commit for HEAD to resolve.
    _write(repo, "README.md", "fixture\n")
    if commit:
        _commit_all(repo)
    else:
        # Commit ONLY the baseline so HEAD exists; leave the state files untracked.
        _git(repo, "add", "README.md")
        for name in artifacts:
            _git(repo, "add", f"models/{name}.tmdl")
        if allowlist is not None:
            _git(repo, "add", gate.TARGET_ALLOWLIST_RELPATH)
        _git(repo, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return repo


@pytest.fixture
def committed_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    return _build_repo(
        tmp_path, readiness=_readiness_yaml(), allowlist=_allowlist_yaml()
    )


def _evaluate(repo: Path, **kwargs: object) -> gate.GateVerdict:
    params: dict[str, object] = {
        "repo_root": repo,
        "target_id": TARGET,
        "operation_id": OPERATION,
        "tree_clean": True,
    }
    params.update(kwargs)
    return gate.evaluate(**params)  # type: ignore[arg-type]
