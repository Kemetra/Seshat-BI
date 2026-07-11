"""TDD tests for PP1 -- publish-pack completeness gate.

PP1 scans committed per-table handoff packs (``mappings/<table>/handoff/
bi-handoff-pack.md``) and flags any required-section index row (a-f) that is missing
or whose structured "Resolved?" cell is still a ``<placeholder>`` or the literal
``GAP``. It reuses G6's placeholder mechanism (the ``<...>`` angle-bracket form) over
the index table's resolution column ONLY -- never a free-text prose scan, so the word
"gap" in narrative does not false-positive.

Principle-V boundary (ratified): the publish-approval row (f) is checked for
presence-and-non-placeholder ONLY. PP1 never inspects WHO signed or WHETHER the
sign-off is legitimate -- a filled cell (``yes`` / a path / even ``pending``) passes;
only an unfilled ``<placeholder>`` / ``GAP`` cell is flagged. PP1 grants nothing.

The one real pack on the tree is filled, so PP1 is green on main and fires only on an
incomplete pack. Fixtures use synthetic generic packs (no domain artifact).
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.publish_pack import (
    _PACK_GLOB_SUFFIX,
    _REQUIRED_SECTIONS,
    check_publish_pack_complete,
)

pytestmark = pytest.mark.unit

_PACK_PATH = "mappings/generic_table/handoff/bi-handoff-pack.md"


def _index_table(rows: dict[str, str]) -> str:
    """Build a required-section index table; rows maps section-id -> Resolved? cell."""
    header = (
        "## Required-section index\n\n"
        "| # | Section | Points at | Resolved? |\n"
        "|---|---------|-----------|-----------|\n"
    )
    body = "".join(
        f"| {sid} | Section {sid} | `../some/artifact` | {cell} |\n"
        for sid, cell in rows.items()
    )
    return header + body + "\n"


def _full_pack() -> str:
    # All six required sections present and filled (non-placeholder, non-GAP).
    return "# BI Handoff Pack\n\n" + _index_table(
        {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    )


def _stage(tmp_path, files: dict[str, str]) -> RuleContext:
    tracked = []
    for rel, src in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src, encoding="utf-8")
        tracked.append(rel)
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


# --- C4: a fully filled pack -> no Finding ------------------------------------


def test_full_pack_passes(tmp_path) -> None:
    ctx = _stage(tmp_path, {_PACK_PATH: _full_pack()})
    assert list(check_publish_pack_complete(ctx)) == []


# --- C1: a required section still a <placeholder> -> Finding ------------------


def test_placeholder_resolution_cell_fails(tmp_path) -> None:
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    rows["a"] = "`<path / GAP>`"  # section a left unfilled
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "PP1"
    assert findings[0].severity is Severity.ERROR
    assert "a" in findings[0].message
    assert _PACK_PATH in findings[0].locator


# --- C2: a required section's Resolved? cell = GAP -> Finding -----------------


def test_gap_resolution_cell_fails(tmp_path) -> None:
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    rows["c"] = "GAP"
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "c" in findings[0].message


# --- C2b: the word "gap" in prose (not a resolution cell) -> no Finding -------


def test_prose_gap_word_does_not_false_positive(tmp_path) -> None:
    pack = (
        "# Pack\n\n"
        "Some narrative mentioning a gap in the old process, and a GAP analysis.\n\n"
        + _index_table({s: "yes" for s in sorted(_REQUIRED_SECTIONS)})
    )
    ctx = _stage(tmp_path, {_PACK_PATH: pack})
    assert list(check_publish_pack_complete(ctx)) == []


# --- C3: a pack missing a required-section row -> Finding ---------------------


def test_missing_required_section_fails(tmp_path) -> None:
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS) if s != "e"}  # drop e
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "e" in findings[0].message
    assert "missing" in findings[0].message.lower()


# --- C7: an unreadable selected pack -> fail-loud Finding ---------------------


def test_unreadable_pack_fails_loud(tmp_path) -> None:
    # Tracked pack path that does not exist on disk -> fail loud, not a crash.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(_PACK_PATH,))
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert _PACK_PATH in findings[0].locator


# --- C8 (US4): the approval row is presence/non-placeholder ONLY --------------


def test_approval_pending_is_filled_not_flagged(tmp_path) -> None:
    # A 'pending' approval cell is non-placeholder/non-GAP -> PP1 does NOT flag it.
    # PP1 checks the slot is filled, NOT whether publish is granted (Principle V).
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    rows["f"] = "pending"
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    assert list(check_publish_pack_complete(ctx)) == []


def test_approval_placeholder_is_flagged_like_any_section(tmp_path) -> None:
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    rows["f"] = "`<recorded / GAP>`"
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "f" in findings[0].message


# --- scope: template + test fixtures + no-packs are not scanned ---------------


def test_template_is_not_scanned(tmp_path) -> None:
    # The generic template (templates/handoff/...) is full of placeholders by
    # design and must NOT be scanned.
    ctx = _stage(
        tmp_path,
        {
            "templates/handoff/bi-handoff-pack.md": "# Pack\n\n"
            + _index_table({"a": "`<path / GAP>`"})
        },
    )
    assert list(check_publish_pack_complete(ctx)) == []


def test_no_packs_silent_pass(tmp_path) -> None:
    ctx = _stage(tmp_path, {"docs/readme.md": "nothing here\n"})
    assert list(check_publish_pack_complete(ctx)) == []


def test_pack_glob_suffix_is_generic(tmp_path) -> None:
    # The scanned suffix is a generic handoff path, no domain token.
    assert _PACK_GLOB_SUFFIX == "/handoff/bi-handoff-pack.md"
    for s in _REQUIRED_SECTIONS:
        assert s in {"a", "b", "c", "d", "e", "f"}


# --- regression: parser anchored to the index section + 4th-column positional ----


def test_stray_table_does_not_mask_missing_index_row(tmp_path) -> None:
    # A row "| a | ... |" in an UNRELATED table must NOT satisfy the index check
    # when the real index section omits row a. (HIGH: cross-table false-negative.)
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS) if s != "a"}  # index lacks a
    pack = (
        "# Pack\n\n"
        "## Some other table\n\n"
        "| Key | Meaning | Note |\n"
        "|---|---|---|\n"
        "| a | an unrelated abbreviation row | yes |\n\n"
        + _index_table(rows)  # the real index section, missing row a
    )
    ctx = _stage(tmp_path, {_PACK_PATH: pack})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "a" in findings[0].message
    assert "missing" in findings[0].message.lower()


def test_extra_trailing_column_does_not_shift_resolved_cell(tmp_path) -> None:
    # A pack whose index rows have an extra trailing column must still read the 4th
    # (Resolved?) column, not the last. (HIGH: greedy-.* wrong-column capture.)
    header = (
        "## Required-section index\n\n"
        "| # | Section | Points at | Resolved? | Notes |\n"
        "|---|---------|-----------|-----------|-------|\n"
    )
    body = "".join(
        f"| {s} | Section {s} | `../a` | yes | a trailing note |\n"
        for s in sorted(_REQUIRED_SECTIONS)
        if s != "b"
    )
    # Section b: Resolved? is a placeholder, but the trailing Notes column is filled.
    body += "| b | Section b | `../a` | `<path / GAP>` | a trailing note |\n"
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + header + body + "\n"})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "b" in findings[0].message  # the 4th column (placeholder), not "note"


def test_empty_resolution_cell_is_unfilled(tmp_path) -> None:
    rows = {s: "yes" for s in sorted(_REQUIRED_SECTIONS)}
    rows["d"] = ""  # empty Resolved? cell -> unfilled
    ctx = _stage(tmp_path, {_PACK_PATH: "# Pack\n\n" + _index_table(rows)})
    findings = list(check_publish_pack_complete(ctx))
    assert len(findings) == 1
    assert "d" in findings[0].message
