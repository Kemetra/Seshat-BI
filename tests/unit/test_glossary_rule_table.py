"""E2 (glossary-table sliver) -- glossary rule-table <-> live registry bijection.

Feature 043 already locks the live registry against two golden records:
``test_rules_manifest_snapshot.py`` (the manifest) and ``test_wiring_meta_gate.py``
(EXPECTED_RULE_IDS + the 5-place wiring). SC2 locks the prose "N rules" COUNT. But
nothing checked the glossary's per-rule TABLE (docs/glossary.md "Static check rules")
against the live registry: a rule could be added/renamed and the human-facing table
left stale while the count stayed right (add one, drop one) or while SC2's count claim
was updated but the row was not.

This test closes that gap: every rule id in the live registry MUST appear as a
backtick-quoted id in the glossary rule-table, and every id in the table MUST be a
live rule. It is the glossary-TABLE sibling of the manifest snapshot test.

Test-only: no @register rule, no rule-count change, no score. Read-only.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GLOSSARY = _REPO_ROOT / "docs" / "glossary.md"

# A rule id: 1-3 uppercase letters + a digit + optional lowercase suffix (S4a, DL2).
_ID_RE = re.compile(r"`([A-Z]{1,3}[0-9][0-9a-z]?)`")

# Bare tokens that appear in the section as PROSE, not as a rule row -- e.g. the
# "(`S4` is split into `S4a`/`S4b`)" note. These are not rule ids.
_PROSE_TOKENS = frozenset({"S4"})


def _live_rule_ids() -> set[str]:
    import seshat.rules  # noqa: F401

    importlib.reload(seshat.rules)  # re-fire @register after any sibling clear
    from seshat import registry

    return {r.id for r in registry.all_rules()}


def _glossary_table_ids() -> set[str]:
    """Ids from the Static-check-rules TABLE rows (lines starting with '|')."""
    text = _GLOSSARY.read_text(encoding="utf-8")
    m = re.search(r"^##+\s*Static check rules.*$", text, re.M)
    assert m, "docs/glossary.md has no 'Static check rules' section"
    section = text[m.end() :]
    # stop at the next top-level section, if any
    nxt = re.search(r"^##\s", section, re.M)
    if nxt:
        section = section[: nxt.start()]
    ids: set[str] = set()
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue  # only table rows carry rule ids
        ids.update(_ID_RE.findall(line))
    return ids - _PROSE_TOKENS


def test_every_live_rule_is_in_the_glossary_table() -> None:
    live = _live_rule_ids()
    table = _glossary_table_ids()
    missing = sorted(live - table)
    assert not missing, (
        f"rules missing from the docs/glossary.md rule table: {missing} "
        f"-- add each id's row (and keep the count line + SC2 anchor in lockstep)"
    )


def test_every_glossary_table_id_is_a_live_rule() -> None:
    live = _live_rule_ids()
    table = _glossary_table_ids()
    stale = sorted(table - live)
    assert not stale, (
        f"glossary rule table lists ids that are not live rules: {stale} "
        f"-- a renamed/removed rule left a stale row (or add it to _PROSE_TOKENS "
        f"if it is a prose reference, not a rule row)"
    )
