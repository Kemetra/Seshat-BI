# tests/unit/test_dseam.py
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT = REPO_ROOT / ".claude" / "agents" / "powerbi-analyst.md"


def _read(path: Path) -> str:
    # Power BI / editor files may carry a UTF-8 BOM; utf-8-sig strips it.
    return path.read_text(encoding="utf-8-sig")


@pytest.mark.unit
def test_agent_references_retail_check() -> None:
    text = _read(AGENT)
    assert "seshat check" in text


@pytest.mark.unit
def test_agent_names_rule_ids() -> None:
    text = _read(AGENT)
    # The agent must point at concrete rule ids, not restate rules in prose.
    assert "D8" in text
    assert "C1" in text


@pytest.mark.unit
def test_agent_drops_marts_only_claim() -> None:
    text = _read(AGENT)
    lowered = text.lower()
    # Gold-only supersedes marts-only everywhere (spec §2 row 3, D8).
    assert "gold" in lowered
    assert "marts" not in lowered


# --- appended to tests/unit/test_dseam.py ---

SKILL = REPO_ROOT / ".claude" / "skills" / "retail-govern" / "SKILL.md"


def _frontmatter(text: str) -> str:
    # Hand-parse the leading `---` fenced YAML block (stdlib-only; no PyYAML).
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "missing opening frontmatter fence"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    raise AssertionError("missing closing frontmatter fence")


@pytest.mark.unit
def test_skill_frontmatter_valid() -> None:
    fm = _frontmatter(_read(SKILL))
    assert "name: retail-govern" in fm
    assert "description:" in fm


@pytest.mark.unit
def test_skill_references_retail_check() -> None:
    text = _read(SKILL)
    assert "seshat check" in text


@pytest.mark.unit
def test_skill_maps_rule_ids_to_fixes() -> None:
    text = _read(SKILL)
    # The skill's job is id -> fix mapping, so concrete ids must appear.
    assert "D8" in text
    assert "C2" in text


@pytest.mark.unit
def test_skill_is_bounded_invoke_only() -> None:
    lowered = _read(SKILL).lower()
    # Bounded scope must be stated in the deliverable, not just honored.
    assert "does not" in lowered
    assert "orchestrat" in lowered  # matches "orchestrate" / "orchestration"
