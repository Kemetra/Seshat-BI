"""Render the agent-facing rule-id -> fix table from its authored source.

The ``retail-govern`` skill is what an agent is told to consult when ``seshat check``
emits a finding, and its fix table had drifted to 47 of the registry's 79 ids -- so a
third of all findings had no guidance on the one surface built to provide it. Nothing
guarded it: no test or script read that file at all.

This module renders the table from two committed authorities -- rule identity from
``docs/rules/rules-manifest.json`` and reader guidance from
``docs/rules/rule-fixes.yaml`` -- into a fenced region of the skill, so the surface
cannot drift from the registry again. Coverage is a bijection, checked by
``tests/unit/test_rule_fix_table.py``.

Carries no severity and no threshold: severity lives in
``docs/rules/severity-posture.json``, and nothing here is a score.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

START = "<!-- SESHAT-RULE-FIX-TABLE START -->"
END = "<!-- SESHAT-RULE-FIX-TABLE END -->"

SKILL_REL = Path(".claude/skills/retail-govern/SKILL.md")
FIXES_REL = Path("docs/rules/rule-fixes.yaml")
MANIFEST_REL = Path("docs/rules/rules-manifest.json")

_ID_PARTS = re.compile(r"^([A-Za-z]+)(\d*)([a-z]*)$")


class RuleFixTableError(ValueError):
    """The authored guidance and the rule registry disagree, or the fence is broken."""


def sort_key(rule_id: str) -> tuple[str, int, str]:
    """Family, then natural number, then variant: S4a before S4b before S5."""
    match = _ID_PARTS.match(rule_id)
    if not match:
        return (rule_id, 0, "")
    family, number, variant = match.groups()
    return (family, int(number) if number else 0, variant)


def registered_ids(repo_root: Path) -> list[str]:
    """Every rule id the committed manifest declares."""
    payload = json.loads((repo_root / MANIFEST_REL).read_text(encoding="utf-8"))
    entries = payload if isinstance(payload, list) else payload.get("rules", [])
    return [entry["id"] if isinstance(entry, dict) else entry for entry in entries]


def load_guidance(repo_root: Path) -> dict[str, dict[str, str]]:
    """The authored ``means``/``fix`` guidance, keyed by rule id."""
    import yaml  # lazy: keeps this off any stdlib-only import chain (B1/B3)

    payload = yaml.safe_load((repo_root / FIXES_REL).read_text(encoding="utf-8"))
    rules = (payload or {}).get("rules")
    if not isinstance(rules, dict):
        raise RuleFixTableError(f"{FIXES_REL.as_posix()} has no 'rules' mapping")
    return rules


def coverage_gap(repo_root: Path) -> tuple[list[str], list[str]]:
    """``(ids missing guidance, guidance for unregistered ids)`` -- both directions."""
    ids = set(registered_ids(repo_root))
    authored = set(load_guidance(repo_root))
    return (sorted(ids - authored, key=sort_key), sorted(authored - ids, key=sort_key))


def _row(rule_id: str, entry: dict[str, str]) -> str:
    means = str(entry.get("means", "")).strip()
    fix = str(entry.get("fix", "")).strip()
    return f"| `{rule_id}` | {means} | {fix} |"


def render_table(repo_root: Path) -> str:
    """The generated block body: a count line plus one row per registered rule."""
    missing, stale = coverage_gap(repo_root)
    if missing or stale:
        raise RuleFixTableError(
            f"guidance does not cover the registry: missing={missing} stale={stale}"
        )
    guidance = load_guidance(repo_root)
    ids = sorted(registered_ids(repo_root), key=sort_key)
    lines = [
        f"This table covers all **{len(ids)}** registered rules. It is GENERATED from",
        "`rule-fixes.yaml` -- edit that file and run",
        "`python scripts/export_rule_fix_table.py`, never this table.",
        "",
        "| Rule | Means | Where to fix |",
        "|------|-------|--------------|",
    ]
    lines += [_row(rule_id, guidance[rule_id]) for rule_id in ids]
    return "\n".join(lines)


def fenced_block(body: str) -> str:
    """``body`` wrapped in its markers, each on its own line."""
    return f"{START}\n{body}\n{END}"


def _fence_span(text: str) -> tuple[int, int]:
    """Byte span of the existing fence, markers included."""
    starts, ends = text.count(START), text.count(END)
    if starts != 1 or ends != 1:
        raise RuleFixTableError(
            f"malformed rule-fix-table fence: {starts} START and {ends} END markers"
        )
    begin = text.index(START)
    finish = text.index(END) + len(END)
    if finish <= begin:
        raise RuleFixTableError("rule-fix-table fence END precedes START")
    return (begin, finish)


def render_skill(repo_root: Path) -> str:
    """The skill file with its fenced table replaced; bytes outside are untouched."""
    path = repo_root / SKILL_REL
    text = path.read_text(encoding="utf-8")
    begin, finish = _fence_span(text)
    return text[:begin] + fenced_block(render_table(repo_root)) + text[finish:]


def write_skill(repo_root: Path) -> bool:
    """Regenerate the skill's table. Returns whether the file changed."""
    path = repo_root / SKILL_REL
    rendered = render_skill(repo_root)
    if rendered == path.read_text(encoding="utf-8"):
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def check_skill(repo_root: Path) -> list[str]:
    """Concrete drift reasons, empty when the committed table matches a fresh render."""
    missing, stale = coverage_gap(repo_root)
    reasons: list[str] = []
    if missing:
        reasons.append(
            f"{len(missing)} registered rule(s) have no guidance in "
            f"{FIXES_REL.as_posix()}: {', '.join(missing)}"
        )
    if stale:
        reasons.append(
            f"{FIXES_REL.as_posix()} carries guidance for unregistered id(s): "
            f"{', '.join(stale)}"
        )
    if reasons:
        return reasons
    path = repo_root / SKILL_REL
    if render_skill(repo_root) != path.read_text(encoding="utf-8"):
        reasons.append(
            f"{SKILL_REL.as_posix()} does not match a fresh render; run "
            "`python scripts/export_rule_fix_table.py`"
        )
    return reasons


def summary(repo_root: Path) -> dict[str, Any]:
    """Read-only projection for callers that want the numbers, not the markdown."""
    missing, stale = coverage_gap(repo_root)
    return {
        "registered": len(registered_ids(repo_root)),
        "authored": len(load_guidance(repo_root)),
        "missing_guidance": missing,
        "unregistered_guidance": stale,
    }
