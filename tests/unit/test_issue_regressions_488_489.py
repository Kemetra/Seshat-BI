"""Regression tests for issues #488 and #489 (routing to shipped capabilities).

Both issues share a shape with #486/#487: the capability exists and works, but the
path a user is told to take does not lead to it.

  - #488: `source-map.yaml` has a canonical shape that only `seshat validate`
    enforces, and the source-mapping skill told users to "copy blanks from
    `templates/`" -- a path that exists ONLY in the Seshat development repo. A
    pipx user following that instruction hand-authors a map that silently misses
    the shape. The canonical blanks do ship, via `seshat scaffold-source`.
  - #489: `seshat orchestration-assess` is a complete recommend-then-decide
    assessor for the dbt/Dagster adapters, but no skill referenced it, so
    `retail-build-warehouse` went straight to hand-written SQL and the adapters
    were bypassed silently rather than declined deliberately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SKILLS = _REPO_ROOT / ".claude" / "skills"


def _skill_text(name: str) -> str:
    return (_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# #488 -- route people to the canonical scaffolder, not a dev-only path
# ---------------------------------------------------------------------------


def test_source_mapping_skill_does_not_send_users_to_a_dev_only_templates_path() -> (
    None
):
    """The root cause of #488: `templates/` only exists in the dev repo.

    Anyone who installed the kit as a tool cannot follow that instruction, so they
    hand-author `source-map.yaml` and miss the canonical shape.
    """
    text = _skill_text("source-mapping")

    assert "copy blanks from templates/" not in text
    assert "copy the five template blanks" not in text


def test_source_mapping_skill_names_the_scaffolder() -> None:
    text = _skill_text("source-mapping")

    assert "seshat scaffold-source" in text


def test_fresh_next_action_names_the_source_map_it_scaffolds() -> None:
    """The guidance named only the profile + readiness file, omitting source-map.yaml
    -- which `scaffold-source` does write, and whose shape later stages require."""
    from seshat.agent_next import _FRESH_NEXT_ACTION

    assert "scaffold-source" in _FRESH_NEXT_ACTION
    assert "source-map.yaml" in _FRESH_NEXT_ACTION


def test_scaffolder_writes_every_file_the_guidance_promises() -> None:
    """Guard against the guidance drifting from what the scaffolder actually does."""
    from seshat.agent_next import _FRESH_NEXT_ACTION
    from seshat.stage1_scaffold import _STAGE1_FILES

    missing = [name for name in _STAGE1_FILES if name not in _FRESH_NEXT_ACTION]
    assert not missing, f"guidance omits scaffolded files: {missing}"


def test_validate_source_map_load_failure_points_at_the_scaffolder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed/absent map used to fail with no route to the canonical shape."""
    from seshat.cli import main

    bad_map = tmp_path / "source-map.yaml"
    bad_map.write_text("this: [is not: a valid map\n", encoding="utf-8")

    main(["validate", "--repo", str(tmp_path), "--source-map", str(bad_map)])
    err = capsys.readouterr().err

    # Only assert the pointer when the load actually failed; if the environment
    # short-circuits earlier (no db extra / no DSN), there is nothing to assert.
    if "could not load source-map" in err:
        assert "scaffold-source" in err


def test_source_map_cli_help_names_the_canonical_shape() -> None:
    import argparse

    from seshat.cli.parser_validation import _add_validate_parser

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    _add_validate_parser(sub)

    help_text = next(
        action.help
        for action in sub.choices["validate"]._actions
        if getattr(action, "dest", None) == "source_map"
    )
    assert "canonical" in (help_text or "").lower()


# ---------------------------------------------------------------------------
# #489 -- surface the adapter choice before hand-writing SQL
# ---------------------------------------------------------------------------


def test_build_warehouse_skill_surfaces_the_orchestration_assessor() -> None:
    """#489: the skill that would otherwise write direct SQL never mentioned the
    adapters, so they were bypassed silently instead of declined on purpose."""
    text = _skill_text("retail-build-warehouse")

    assert "orchestration-assess" in text
    assert "dbt" in text.lower() and "dagster" in text.lower()


def test_build_warehouse_checkpoint_does_not_let_the_agent_adopt_an_adapter() -> None:
    """Surfacing a recommendation must not become self-granted adoption."""
    text = _skill_text("retail-build-warehouse")

    assert "never adopts" in text or "do NOT adopt" in text


def test_orchestration_assessor_verdicts_referenced_by_the_skill_are_real() -> None:
    """Guard the skill's quoted verdicts against drifting from the engine."""
    from seshat.orchestration_assess import (
        _ALREADY_ADOPTED,
        _CONSIDER,
        _NOT_RECOMMENDED,
    )

    text = _skill_text("retail-build-warehouse")

    for verdict in (_CONSIDER, _NOT_RECOMMENDED, _ALREADY_ADOPTED):
        assert verdict in text, f"skill omits real verdict {verdict!r}"
