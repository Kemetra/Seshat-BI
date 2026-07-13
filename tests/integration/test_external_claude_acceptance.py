from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import scripts.external_agent_acceptance as acceptance
from scripts.external_agent_acceptance import (
    AcceptanceError,
    CliRequest,
    _ensure_isolated,
    classify_transcript,
    execute_cli,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/public_distribution/claude"


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_external_claude_semantic_journey_passes_shared_outcome() -> None:
    record = classify_transcript(ROOT, _load("acceptance.pass.json"))
    assert record["status"] == "pass"
    assert record["observed_stage"] == "source"
    assert record["human_gate_observed"] is True
    assert record["secrets_or_pii_exposed"] is False
    assert record["fabricated_score"] is False


def test_external_claude_classifier_rejects_pii_shaped_output() -> None:
    record = classify_transcript(ROOT, _load("acceptance.pii-fail.json"))
    assert record["status"] == "fail"
    assert record["secrets_or_pii_exposed"] is True
    assert any("PII-shaped" in blocker for blocker in record["blockers"])


def test_claude_update_and_uninstall_fixture_detects_stale_cache() -> None:
    valid = _load("lifecycle.valid.json")
    stale = _load("lifecycle.stale-cache.json")
    assert valid["resolved_version_after_update"] == valid["installed_version"]
    assert valid["uninstall_removed_plugin"] is True
    assert valid["workspace_preserved"] is True
    assert stale["resolved_version_after_update"] != stale["installed_version"]


def test_external_profile_and_workspace_must_be_outside_repo(tmp_path: Path) -> None:
    _ensure_isolated(ROOT, tmp_path / "profile", tmp_path / "workspace")
    with pytest.raises(AcceptanceError, match="outside"):
        _ensure_isolated(ROOT, ROOT / ".profiles/claude", tmp_path / "workspace")


def test_cli_execution_uses_the_isolated_installed_plugin_not_the_dev_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(acceptance.shutil, "which", lambda _name: "claude")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(acceptance.subprocess, "run", fake_run)
    profile = tmp_path / "profile"
    workspace = tmp_path / "workspace"
    execute_cli(
        ROOT,
        CliRequest("claude-code", profile, workspace, 30),
    )
    command = [str(item) for item in captured["command"]]
    assert "--plugin-dir" not in command
    assert str(ROOT) not in " ".join(command)
    assert captured["env"]["CLAUDE_CONFIG_DIR"] == str(profile / ".claude")
