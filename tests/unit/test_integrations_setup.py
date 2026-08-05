from pathlib import Path

from seshat.integrations_setup import setup_integrations


def test_setup_defaults_to_a_network_free_plan(tmp_path: Path) -> None:
    results = setup_integrations(tmp_path)
    assert [item.status for item in results][:2] == ["planned", "planned"]
    assert not (tmp_path / ".seshat" / "integrations").exists()


def test_existing_skill_bundle_is_detected(tmp_path: Path) -> None:
    root = tmp_path / ".seshat" / "integrations" / "skills-for-fabric"
    for relative in (
        "skills/semantic-model-consumption/SKILL.md",
        "skills/semantic-model-authoring/SKILL.md",
        "plugins/powerbi-authoring/skills/powerbi-report-authoring/SKILL.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("name: test\n", encoding="utf-8")
    results = setup_integrations(tmp_path)
    assert results[0].status == "present"
