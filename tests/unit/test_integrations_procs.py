"""The integration installer's subprocess, cleanup and output-scrubbing seams.

The default runner is what production uses, so its hardening is asserted on the
runner itself (injected-runner tests never exercise it): stdin is closed, a
timeout is set, git config-driven exec vectors are neutralised, and credential
prompts are disabled. Every string that reaches an output surface is scrubbed.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from seshat import gitutil
from seshat.integrations import discovery, installer, procs
from seshat.integrations.render import as_json
from seshat.integrations.resolvers import Resolvers
from tests.unit._curated_stack_fixtures import (
    FakeGitHub,
    FakeNpm,
    FakePypi,
    _github_component,
    _grant_provisioning,
    _pypi_component,
    _release,
    _tools_on_path,
    _workspace,
)

pytestmark = pytest.mark.unit

_URL_SECRET = "Sup3rS3cretTok"
_BARE_SECRET = "ghbaretoken987"
_LEAKY = (
    f"fatal: could not read from https://user:{_URL_SECRET}@corp.example/simple "
    f"and https://{_BARE_SECRET}@github.com/org/repo.git"
)


def _capture_run(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    seen: list[dict] = []

    def _fake(args, **kwargs):
        seen.append({"args": list(args), **kwargs})
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(procs.subprocess, "run", _fake)
    return seen


def test_default_runner_hardens_git(tmp_path: Path, monkeypatch) -> None:
    seen = _capture_run(monkeypatch)

    procs.run(["git", "clone", "https://github.com/a/b.git", "dst"], tmp_path)

    call = seen[0]
    assert call["args"][: 1 + len(gitutil.GIT_HARDENING)] == [
        "git",
        *gitutil.GIT_HARDENING,
    ]
    assert call["args"][-3:] == ["clone", "https://github.com/a/b.git", "dst"]
    assert call["stdin"] is subprocess.DEVNULL
    assert call["timeout"] and call["timeout"] > 0
    assert call["capture_output"] is True and call["text"] is True
    assert call["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert call["env"]["GCM_INTERACTIVE"] == "never"
    assert call["cwd"] == tmp_path


def test_default_runner_closes_stdin_for_non_git_tools(tmp_path, monkeypatch) -> None:
    seen = _capture_run(monkeypatch)

    procs.run(["uv", "venv", "env"], tmp_path)

    assert seen[0]["args"] == ["uv", "venv", "env"]
    assert seen[0]["stdin"] is subprocess.DEVNULL
    assert seen[0]["timeout"] > 0


def test_a_timeout_becomes_a_failed_result(tmp_path, monkeypatch) -> None:
    def _slow(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs.get("timeout", 1))

    monkeypatch.setattr(procs.subprocess, "run", _slow)

    result = procs.run(["git", "clone", "x", "y"], tmp_path)

    assert result.returncode != 0
    assert "timed out" in result.stderr


def test_installer_and_discovery_share_the_one_runner() -> None:
    assert installer._run is procs.run
    assert discovery._run is procs.run


# --------------------------------------------------------------------------- #
# Staging cleanup.
# --------------------------------------------------------------------------- #


def test_remove_tree_deletes_read_only_files(tmp_path: Path) -> None:
    """Git for Windows marks pack files read-only; a plain rmtree leaves them."""
    tree = tmp_path / "staging" / "pack"
    tree.mkdir(parents=True)
    packed = tree / "objects.pack"
    packed.write_text("x", encoding="utf-8")
    os.chmod(packed, stat.S_IREAD)

    assert procs.remove_tree(tmp_path / "staging") is None
    assert not (tmp_path / "staging").exists()


def test_remove_tree_names_a_leftover_it_could_not_delete(tmp_path, monkeypatch):
    tree = tmp_path / "staging"
    tree.mkdir()
    monkeypatch.setattr(procs.shutil, "rmtree", lambda *a, **k: None)

    leftover = procs.remove_tree(tree)

    assert leftover is not None and str(tree) in leftover


def _fabric_resolvers() -> Resolvers:
    return Resolvers(
        github=FakeGitHub(
            release={"tag_name": "v3.0.0"}, commits={"v3.0.0": {"sha": "9" * 40}}
        ),
        npm=FakeNpm({"@microsoft/powerbi-modeling-mcp": {"dist-tags": {}}}),
        python_version=(3, 13),
    )


def _fabric_row(outcome):
    return next(row for row in outcome.rows if row.component == "fabric-skills")


def test_an_undeletable_staging_tree_is_reported_not_ignored(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _grant_provisioning(monkeypatch)
    _tools_on_path(monkeypatch)
    monkeypatch.setattr(procs.shutil, "rmtree", lambda *a, **k: None)

    def _failing(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 128, "", "fatal: not found")

    outcome = installer.apply(
        root,
        components=(_github_component(),),
        resolvers=_fabric_resolvers(),
        runner=_failing,
    )

    row = _fabric_row(outcome)
    assert row.status == installer.FAILED
    assert "could not remove" in row.detail


def test_a_leftover_staging_tree_does_not_block_the_next_clone(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _grant_provisioning(monkeypatch)
    _tools_on_path(monkeypatch)
    stale = root / ".seshat/integrations/staging/fabric-skills"
    stale.mkdir(parents=True)
    (stale / "leftover.pack").write_text("x", encoding="utf-8")

    def _clone(command: list[str], cwd: Path):
        if command[:2] == ["git", "clone"]:
            Path(command[-1]).mkdir(parents=True)
        return subprocess.CompletedProcess(command, 0, "", "")

    outcome = installer.apply(
        root,
        components=(_github_component(),),
        resolvers=_fabric_resolvers(),
        runner=_clone,
    )

    assert _fabric_row(outcome).status == installer.INSTALLED


# --------------------------------------------------------------------------- #
# Output scrubbing.
# --------------------------------------------------------------------------- #


def _assert_scrubbed(text: str) -> None:
    assert _URL_SECRET not in text
    assert _BARE_SECRET not in text


def test_scrub_removes_url_credentials_and_secret_shapes() -> None:
    guid = "72f988bf-86f1-41af-91ab-2d7cd011db47"
    scrubbed = procs.scrub(f"{_LEAKY} tenant {guid}")
    _assert_scrubbed(scrubbed)
    assert guid not in scrubbed
    assert "corp.example" in scrubbed


def test_a_failed_install_detail_is_scrubbed_end_to_end(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _grant_provisioning(monkeypatch)
    _tools_on_path(monkeypatch)

    def _leaky(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 1, "", _LEAKY)

    outcome = installer.apply(
        root,
        components=(_pypi_component(),),
        resolvers=Resolvers(
            pypi=FakePypi({"duckdb": {"releases": {"1.0.0": _release("1.0.0")}}}),
            python_version=(3, 13),
        ),
        runner=_leaky,
    )

    assert outcome.rows[0].status == installer.FAILED
    _assert_scrubbed(as_json(outcome))


def test_a_resolver_refusal_reason_is_scrubbed(tmp_path: Path) -> None:
    class _LeakyPypi:
        def project(self, dist: str) -> dict:
            raise OSError(_LEAKY)

    outcome = installer.plan(
        _workspace(tmp_path),
        components=(_pypi_component(),),
        resolvers=Resolvers(pypi=_LeakyPypi(), python_version=(3, 13)),
    )

    assert outcome.rows[0].status == installer.FAILED
    _assert_scrubbed(as_json(outcome))


def test_a_plugin_inventory_error_is_scrubbed(tmp_path: Path) -> None:
    def _runner(command: list[str], cwd: Path):
        return subprocess.CompletedProcess(command, 1, "", _LEAKY)

    inventory, error = discovery._claude_inventory(
        tmp_path, _runner, lambda name: f"/bin/{name}"
    )

    assert inventory is None
    _assert_scrubbed(error or "")
