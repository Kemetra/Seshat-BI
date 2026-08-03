from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adopter_sim.blindness import (
    assert_no_dev_ancestor,
    assert_no_leak,
    assert_outside_repo,
    assert_profile_isolated,
    find_clean_root,
)
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit


def test_workspace_inside_repo_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = repo / "benchmark" / "journeys" / "runs" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match="descendant of REPO_ROOT"):
        assert_outside_repo(workspace, repo)


def test_workspace_outside_repo_is_accepted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert assert_outside_repo(workspace, repo) is None


def test_dev_claude_md_in_ancestor_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("dev rules\n", encoding="utf-8")
    workspace = tmp_path / "nested" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match="CLAUDE.md"):
        assert_no_dev_ancestor(workspace, stop_at=tmp_path.parent)


def test_dev_git_dir_in_ancestor_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    workspace = tmp_path / "nested" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match=r"\.git"):
        assert_no_dev_ancestor(workspace, stop_at=tmp_path.parent)


def test_workspace_own_claude_md_and_git_are_allowed(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "CLAUDE.md").write_text("client rules\n", encoding="utf-8")
    (workspace / ".git").mkdir()
    assert assert_no_dev_ancestor(workspace, stop_at=tmp_path.parent) is None


def test_strict_mode_detects_a_dirty_chain_above_the_boundary(tmp_path: Path) -> None:
    """Without stop_at the walk reaches the filesystem root.

    A pytest tmp_path lives under the user profile, which on a developer machine
    holds CLAUDE.md -- exactly the inheritance find_clean_root exists to avoid.
    """
    marker = tmp_path.parents[-1] / "CLAUDE.md"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    if not any(
        (ancestor / name).exists()
        for ancestor in workspace.parents
        for name in ("CLAUDE.md", "AGENTS.md", ".git")
    ):
        pytest.skip(f"no dev marker above {workspace} on this machine ({marker})")
    with pytest.raises(AdopterSimError):
        assert_no_dev_ancestor(workspace)


def test_find_clean_root_skips_a_dirty_candidate(tmp_path: Path) -> None:
    dirty_parent = tmp_path / "dirty"
    dirty_parent.mkdir()
    (dirty_parent / "CLAUDE.md").write_text("dev\n", encoding="utf-8")
    dirty = dirty_parent / "ssim"
    clean = tmp_path.parents[-1] / "ssim-clean-probe"
    if _dirty_ancestor_exists(clean):
        pytest.skip("no clean drive-root candidate on this machine")
    assert find_clean_root([dirty, clean]) == clean


def test_find_clean_root_fails_with_an_actionable_message(tmp_path: Path) -> None:
    dirty_parent = tmp_path / "dirty"
    dirty_parent.mkdir()
    (dirty_parent / "CLAUDE.md").write_text("dev\n", encoding="utf-8")
    with pytest.raises(AdopterSimError, match="ADOPTER_SIM_ROOT"):
        find_clean_root([dirty_parent / "ssim"])


def _dirty_ancestor_exists(path: Path) -> bool:
    return any(
        (ancestor / name).exists()
        for ancestor in path.resolve().parents
        for name in ("CLAUDE.md", "AGENTS.md", ".git")
    )


def _profile(tmp_path: Path, skills: list[str]) -> Path:
    config = tmp_path / ".agent"
    (config / "skills").mkdir(parents=True)
    for name in skills:
        (config / "skills" / name).mkdir()
    return config


def _manifest(tmp_path: Path, skills: list[str]) -> Path:
    path = tmp_path / "bundle-manifest.json"
    path.write_text(json.dumps({"skills": skills}), encoding="utf-8")
    return path


def test_profile_matching_the_manifest_is_accepted(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern", "source-mapping"])
    manifest = _manifest(tmp_path, ["retail-govern", "source-mapping"])
    assert assert_profile_isolated(config, manifest) is None


def test_extra_on_disk_skill_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern", "internal-dev-helper"])
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="internal-dev-helper"):
        assert_profile_isolated(config, manifest)


def test_missing_bundle_skill_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern"])
    manifest = _manifest(tmp_path, ["retail-govern", "source-mapping"])
    with pytest.raises(AdopterSimError, match="missing"):
        assert_profile_isolated(config, manifest)


def test_global_rules_dir_in_profile_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern"])
    (config / "rules" / "common").mkdir(parents=True)
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="rules"):
        assert_profile_isolated(config, manifest)


def test_global_claude_md_in_profile_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern"])
    (config / "CLAUDE.md").write_text("global rules\n", encoding="utf-8")
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="CLAUDE.md"):
        assert_profile_isolated(config, manifest)


def test_agent_self_report_cannot_satisfy_the_inventory_check(tmp_path: Path) -> None:
    """The inventory comes from disk. An agent claiming to be clean is ignored."""
    config = _profile(tmp_path, ["retail-govern", "internal-dev-helper"])
    (config / "agent-says.txt").write_text(
        "I only have retail-govern loaded.\n", encoding="utf-8"
    )
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="internal-dev-helper"):
        assert_profile_isolated(config, manifest)


def test_leak_check_rejects_a_dev_path(tmp_path: Path) -> None:
    repo = tmp_path / "Seshat-BI"
    repo.mkdir()
    transcript = f"I looked at {repo / 'core.py'} for this."
    with pytest.raises(AdopterSimError, match="REPO_ROOT"):
        assert_no_leak(transcript, repo)


def test_leak_check_rejects_a_specs_reference(tmp_path: Path) -> None:
    with pytest.raises(AdopterSimError, match="specs/"):
        assert_no_leak("see specs/138-agent-driven-bundle/plan.md", tmp_path / "repo")


def test_leak_check_rejects_a_src_seshat_reference(tmp_path: Path) -> None:
    with pytest.raises(AdopterSimError, match="src/seshat"):
        assert_no_leak("defined in src/seshat/kit_lint.py", tmp_path / "repo")


def test_leak_check_accepts_a_clean_transcript(tmp_path: Path) -> None:
    assert assert_no_leak("I scaffolded mappings/orders/.", tmp_path / "repo") is None
