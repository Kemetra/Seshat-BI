from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adopter_sim.model import AdopterSimError
from scripts.adopter_sim.workspace import (
    MAX_WORKSPACE_PATH,
    ROOT_ENV_VAR,
    RUN_ID_LENGTH,
    assert_path_budget,
    copy_bundle,
    new_run_id,
    root_candidates,
    workspace_root,
)

pytestmark = pytest.mark.unit


def test_run_id_is_short_and_deterministic_for_a_seed() -> None:
    first = new_run_id("first-hour|messy|1")
    assert len(first) == RUN_ID_LENGTH
    assert first == new_run_id("first-hour|messy|1")


def test_different_seeds_give_different_run_ids() -> None:
    assert new_run_id("a") != new_run_id("b")


def test_run_id_is_filesystem_safe() -> None:
    assert new_run_id("first-hour|messy|1").isalnum()


def test_workspace_root_appends_run_id_to_an_ssim_parent(tmp_path: Path) -> None:
    root = workspace_root(tmp_path / "ssim", "ab12cd34")
    assert root.parent.name == "ssim"
    assert root.name == "ab12cd34"


def test_workspace_root_inserts_ssim_for_a_bare_parent(tmp_path: Path) -> None:
    root = workspace_root(tmp_path, "ab12cd34")
    assert root.parent.name == "ssim"
    assert root.name == "ab12cd34"


def test_explicit_root_env_var_is_preferred(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ROOT_ENV_VAR, str(tmp_path / "chosen"))
    assert root_candidates()[0] == tmp_path / "chosen"


def test_drive_root_is_preferred_over_temp(monkeypatch) -> None:
    monkeypatch.delenv(ROOT_ENV_VAR, raising=False)
    candidates = root_candidates()
    assert len(candidates) >= 2
    # The anchor candidate is shorter than the %TEMP% candidate it precedes.
    assert len(str(candidates[0])) < len(str(candidates[-1]))


def test_path_budget_accepts_a_short_path() -> None:
    assert assert_path_budget(Path("C:/ssim/ab12cd34")) is None


def test_path_budget_rejects_a_long_path() -> None:
    long_path = Path("C:/ssim") / ("x" * MAX_WORKSPACE_PATH)
    with pytest.raises(AdopterSimError, match="path budget"):
        assert_path_budget(long_path)


def test_preferred_root_stays_within_the_path_budget(monkeypatch) -> None:
    monkeypatch.delenv(ROOT_ENV_VAR, raising=False)
    assert assert_path_budget(workspace_root(root_candidates()[0], "ab12cd34")) is None


def _bundle(tmp_path: Path, skills: list[str], on_disk: list[str]) -> Path:
    bundle = tmp_path / "bundle"
    (bundle / "skills").mkdir(parents=True)
    for name in on_disk:
        (bundle / "skills" / name).mkdir()
        (bundle / "skills" / name / "SKILL.md").write_text("x\n", encoding="utf-8")
    entries = [{"destination": f"skills/{name}/SKILL.md"} for name in skills]
    (bundle / "bundle-manifest.json").write_text(
        json.dumps({"entries": entries}), encoding="utf-8"
    )
    return bundle


def test_copy_bundle_copies_exactly_the_declared_skills(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, ["a", "b"], ["a", "b", "undeclared"])
    config = tmp_path / ".agent"
    config.mkdir()
    copy_bundle(bundle, config)
    copied = {entry.name for entry in (config / "skills").iterdir()}
    assert copied == {"a", "b"}
    assert (config / "bundle-manifest.json").is_file()


def test_copy_bundle_fails_when_a_declared_skill_is_absent(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, ["a", "missing"], ["a"])
    config = tmp_path / ".agent"
    config.mkdir()
    with pytest.raises(AdopterSimError, match="missing"):
        copy_bundle(bundle, config)


def test_resolve_root_skips_an_uncreatable_candidate(
    monkeypatch, tmp_path, capsys
) -> None:
    """A drive-root candidate needing admin rights must not crash the run."""
    from scripts.adopter_sim import workspace as workspace_mod

    blocked = tmp_path / "blocked" / "ssim"
    clean = tmp_path / "clean" / "ssim"
    real_mkdir = Path.mkdir

    def _mkdir(self, *args, **kwargs):
        if self == blocked:
            raise PermissionError(13, "Access is denied")
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(workspace_mod, "root_candidates", lambda: (blocked, clean))
    monkeypatch.setattr(Path, "mkdir", _mkdir)
    monkeypatch.setattr(workspace_mod, "find_clean_root", lambda usable: usable[0])
    assert workspace_mod.resolve_root() == clean
    assert "not writable" in capsys.readouterr().out


def test_resolve_root_fails_cleanly_when_nothing_is_creatable(
    monkeypatch, tmp_path
) -> None:
    from scripts.adopter_sim import workspace as workspace_mod

    blocked = tmp_path / "blocked" / "ssim"

    def _mkdir(self, *args, **kwargs):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(workspace_mod, "root_candidates", lambda: (blocked,))
    monkeypatch.setattr(Path, "mkdir", _mkdir)
    with pytest.raises(AdopterSimError, match="ADOPTER_SIM_ROOT"):
        workspace_mod.resolve_root()
