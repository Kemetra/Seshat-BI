"""The agent-facing fix table must cover every registered rule, and stay generated.

`retail-govern/SKILL.md` is the surface an agent is told to consult when `seshat check`
emits a finding. Measured before this guard existed: the registry declared 79 rule ids
and that table listed 47, so roughly a third of all findings -- every `CT*`, `DL*`,
`DS*`, and `HR*` id among them -- had no guidance on the one surface built to provide
it. Nothing caught it because no test or script read that file at all.

These tests make the coverage a bijection and the table a generated artifact, so the
same drift cannot recur silently.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from seshat.rule_fix_table import (
    END,
    FIXES_REL,
    SKILL_REL,
    RuleFixTableError,
    check_skill,
    coverage_gap,
    load_guidance,
    registered_ids,
    render_skill,
    render_table,
    sort_key,
    summary,
    write_skill,
)

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_guidance_covers_the_registry_exactly() -> None:
    """The core guard: a new rule without guidance fails, and so does stale guidance."""
    missing, stale = coverage_gap(REPO)
    assert missing == [], f"registered rules with no fix guidance: {missing}"
    assert stale == [], f"guidance for ids no longer registered: {stale}"


@pytest.mark.unit
def test_the_committed_table_matches_a_fresh_render() -> None:
    """The table is generated, so a hand-edit or a stale render is a failure."""
    assert check_skill(REPO) == []


@pytest.mark.unit
def test_ap1_is_covered() -> None:
    """The concrete id whose absence exposed the gap (spec 085, shipped rule)."""
    guidance = load_guidance(REPO)
    assert "AP1" in guidance
    assert "AP1" in (REPO / SKILL_REL).read_text(encoding="utf-8")


@pytest.mark.unit
def test_the_whole_registry_appears_in_the_rendered_table() -> None:
    rendered = render_table(REPO)
    for rule_id in registered_ids(REPO):
        assert f"| `{rule_id}` |" in rendered, f"{rule_id} missing from the table"


#: Placeholder markers, matched as WHOLE UPPERCASE WORDS plus the admitted-gap form
#: ``UNKNOWN -- ...``. A plain lowercase substring scan would reject legitimate domain
#: vocabulary: S6's guidance is about the ``-1`` *unknown member* (RC14).
_PLACEHOLDER = re.compile(r"\b(?:TBD|TODO|FIXME|XXX)\b|\bUNKNOWN\s*--")


@pytest.mark.unit
@pytest.mark.parametrize("field", ("means", "fix"))
def test_no_entry_is_empty_or_a_placeholder(field: str) -> None:
    for rule_id, entry in load_guidance(REPO).items():
        value = str(entry.get(field, "")).strip()
        assert value, f"{rule_id}.{field} is empty"
        found = _PLACEHOLDER.search(value)
        assert not found, f"{rule_id}.{field} is a placeholder: {found.group(0)!r}"


@pytest.mark.unit
def test_every_fix_names_a_concrete_artifact() -> None:
    """`fix` must point at something editable, not restate the rule."""
    for rule_id, entry in load_guidance(REPO).items():
        fix = str(entry["fix"])
        assert "`" in fix, f"{rule_id}.fix names no concrete artifact: {fix!r}"


@pytest.mark.unit
def test_the_table_carries_no_severity_or_score() -> None:
    """Reader guidance only: severity lives in severity-posture.json (hard rule #9)."""
    rendered = render_table(REPO).lower()
    for token in ("severity", "confidence score", "readiness score", "health score"):
        assert token not in rendered, f"the fix table must not carry {token!r}"


@pytest.mark.unit
def test_rows_are_ordered_by_family_then_natural_number() -> None:
    """S4a before S4b before S5 -- not lexicographic, which would give S10 before S2."""
    assert sort_key("S4a") < sort_key("S4b") < sort_key("S5")
    assert sort_key("HR2") < sort_key("HR11")
    assert sort_key("A1") < sort_key("AD1")


@pytest.mark.unit
def test_the_rendered_table_states_its_own_count() -> None:
    """A prose count that is generated cannot drift from the registry."""
    count = len(registered_ids(REPO))
    assert f"**{count}** registered rules" in render_table(REPO)


@pytest.mark.unit
def test_summary_reports_the_measured_numbers() -> None:
    counts = summary(REPO)
    assert counts["registered"] == counts["authored"]
    assert counts["missing_guidance"] == []
    assert counts["unregistered_guidance"] == []


def _clone(tmp_path: Path) -> Path:
    """A minimal repo copy: the two authorities plus the skill."""
    for rel in (FIXES_REL, SKILL_REL, Path("docs/rules/rules-manifest.json")):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, target)
    return tmp_path


@pytest.mark.unit
def test_a_missing_entry_is_reported_with_the_id_named(tmp_path: Path) -> None:
    """Deleting one rule's guidance must name that rule, not fail vaguely."""
    clone = _clone(tmp_path)
    fixes = clone / FIXES_REL
    text = fixes.read_text(encoding="utf-8")
    # Drop AP1's two-line block from the authored YAML.
    lines = text.splitlines()
    keep, skipping = [], False
    for line in lines:
        if line.startswith("  AP1:"):
            skipping = True
            continue
        if skipping and line.startswith("    "):
            continue
        skipping = False
        keep.append(line)
    fixes.write_text("\n".join(keep) + "\n", encoding="utf-8")

    missing, stale = coverage_gap(clone)
    assert missing == ["AP1"]
    assert stale == []
    reasons = check_skill(clone)
    assert reasons and "AP1" in reasons[0]
    with pytest.raises(RuleFixTableError, match="does not cover the registry"):
        render_table(clone)


@pytest.mark.unit
def test_a_hand_edited_table_is_detected(tmp_path: Path) -> None:
    clone = _clone(tmp_path)
    skill = clone / SKILL_REL
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("| `A1` |", "| `A1-EDITED` |"),
        encoding="utf-8",
    )
    reasons = check_skill(clone)
    assert reasons and "does not match a fresh render" in reasons[0]


@pytest.mark.unit
def test_a_broken_fence_is_refused_rather_than_guessed(tmp_path: Path) -> None:
    clone = _clone(tmp_path)
    skill = clone / SKILL_REL
    skill.write_text(
        skill.read_text(encoding="utf-8").replace(END, ""), encoding="utf-8"
    )
    with pytest.raises(RuleFixTableError, match="malformed rule-fix-table fence"):
        render_skill(clone)


@pytest.mark.unit
def test_regeneration_is_idempotent(tmp_path: Path) -> None:
    """A second run changes nothing -- the generated bytes are stable."""
    clone = _clone(tmp_path)
    assert write_skill(clone) is False
    assert write_skill(clone) is False


@pytest.mark.unit
def test_only_the_fenced_region_is_rewritten(tmp_path: Path) -> None:
    """Bytes outside the markers are preserved exactly."""
    clone = _clone(tmp_path)
    skill = clone / SKILL_REL
    original = skill.read_text(encoding="utf-8")
    head = original.split("<!-- SESHAT-RULE-FIX-TABLE START -->")[0]
    tail = original.split(END)[1]

    rendered = render_skill(clone)
    assert rendered.startswith(head)
    assert rendered.endswith(tail)
