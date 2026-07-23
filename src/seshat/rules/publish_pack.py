"""PP1 -- publish-pack completeness gate.

A committed BI handoff pack (``mappings/<table>/handoff/bi-handoff-pack.md``) is the
Stage 7 (Publish Ready) deliverable. Its "Required-section index" table lists six
sections (a-f: metric contracts, readiness scorecard, reconciliation, known caveats,
data dictionary, publish approval), each with a structured "Resolved?" cell. A cell
left as a ``<placeholder>`` or recorded as ``GAP`` means that section is unfilled --
the pack cannot reach "complete" (per the template's own semantics). Today nothing
fails the gate on such a pack; PP1 makes incompleteness a structural ERROR.

PP1 reuses G6's placeholder mechanism (the ``<...>`` angle-bracket form) over the
index table's resolution column ONLY -- it never scans narrative prose, so the word
"gap" in free text does not false-positive. It is a pure static text read (parse the
committed markdown), never executes, and modifies no pack/template/readiness file.

Principle-V publish-safety boundary (ratified, spec 049 ## Clarifications): the
publish-approval row (f) is checked for PRESENCE and a non-placeholder/non-GAP cell
ONLY. PP1 NEVER inspects, validates, populates, or grants WHO signed or WHETHER the
sign-off is legitimate -- a filled cell (``yes`` / a path / even ``pending``) passes;
PP1 grants nothing. "Slot filled" is not "publish approved" -- that distinction is the
readiness verdict's job, not PP1's.

Ratified rulings (spec 049): required set = the template's six index rows a-f at index
granularity (the four MANDATORY caveats are not decomposed); severity = ERROR; scan
per-table instances only (the generic template is excluded -- it is placeholders by
design); no-packs -> silent pass (mirrors G6); advances no readiness stage.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

# Only per-table handoff-pack instances (mappings/<table>/handoff/bi-handoff-pack.md)
# are scanned. The generic template is full of <placeholder> tokens by design and is
# excluded WHEREVER it ships: the repo-root templates/ copy AND any packaged copy the
# scaffold-design verb bundles (e.g. integrations/<agent>/seshat-bi/templates/handoff/
# ...). Excluding by the `templates/handoff/` tail (not one exact path) keeps a real
# per-table pack -- which never contains a `templates/handoff/` segment -- scanned.
_PACK_GLOB_SUFFIX = "/handoff/bi-handoff-pack.md"
_TEMPLATE_TAIL = "templates/handoff/bi-handoff-pack.md"


def _is_generic_template(path: str) -> bool:
    """True for the placeholder-only generic template at any shipped location."""
    return path == _TEMPLATE_TAIL or path.endswith("/" + _TEMPLATE_TAIL)


# The six required-section index rows the template defines (a-f). Membership is the
# ratified closed set; index granularity only.
_REQUIRED_SECTIONS: frozenset[str] = frozenset({"a", "b", "c", "d", "e", "f"})

# A placeholder resolution cell is angle-bracketed ("<path / GAP>", "<recorded / GAP>")
# -- the same convention G6 governs. Reused as the unfilled signal.
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")

# The index section is anchored by its heading so only THIS table is parsed -- a stray
# table elsewhere in the pack whose first cell is a single letter a-f cannot populate
# the section map (which would mask a genuinely-missing index row).
_INDEX_HEADING_RE = re.compile(r"^##\s+Required-section index\b", re.IGNORECASE)
_NEXT_HEADING_RE = re.compile(r"^##\s+")

# An index row, matched POSITIONALLY: column 1 = section id (a-f), and the 4th column
# is the structured "Resolved?" cell. Middle cells use [^|]* (NOT greedy .*) so an
# extra trailing column (e.g. a Notes column) cannot shift the captured cell -- the
# 4th column is pinned regardless of how many columns follow it.
_INDEX_ROW_RE = re.compile(
    r"^\|\s*([a-f])\s*\|[^|]*\|[^|]*\|\s*(?P<resolved>[^|]*?)\s*\|"
)


def _iter_packs(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_PACK_GLOB_SUFFIX)
        and not _is_generic_template(p)
        and not is_test_path(p)
    ]


def _cell_is_unfilled(cell: str) -> bool:
    """True if a Resolved? cell is unfilled: empty, a <placeholder>, or literal GAP.

    Note an empty cell -- including an empty inline-code span, which strips to the
    empty string -- is treated as unfilled: a required section with no recorded
    resolution is by definition incomplete.
    """
    stripped = cell.strip().strip("`").strip()
    if not stripped:
        return True
    if _PLACEHOLDER_RE.search(cell):
        return True
    # The literal GAP token as the whole cell value (not the word inside prose).
    return stripped.upper() == "GAP"


def _index_section_lines(text: str) -> list[str]:
    """The lines of ONLY the '## Required-section index' section.

    Anchors to the index heading and stops at the next '## ' heading, so tables in
    other sections of the pack cannot contribute rows to the section map.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_section = False
    for line in lines:
        if _INDEX_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section:
            if _NEXT_HEADING_RE.match(line):
                break
            out.append(line)
    return out


@register("PP1", "Committed publish/handoff pack has every required section filled")
def check_publish_pack_complete(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(_iter_packs(ctx)):
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except OSError as exc:
            # A tracked-but-unreadable pack fails loud rather than crashing the gate.
            findings.append(
                Finding(
                    rule_id="PP1",
                    severity=Severity.ERROR,
                    message=f"could not read handoff pack: {exc}",
                    locator=rel,
                )
            )
            continue

        # Parse the required-section index: id -> resolution cell. Only rows WITHIN
        # the '## Required-section index' section are considered, so a stray a-f row
        # in another table cannot mask a genuinely-missing index row.
        resolved: dict[str, str] = {}
        for line in _index_section_lines(text):
            m = _INDEX_ROW_RE.match(line)
            if m:
                resolved[m.group(1)] = m.group("resolved")

        for sid in sorted(_REQUIRED_SECTIONS):
            if sid not in resolved:
                findings.append(
                    Finding(
                        rule_id="PP1",
                        severity=Severity.ERROR,
                        message=(
                            f"handoff pack is missing required-section index row "
                            f"{sid!r} -- the pack cannot reach 'complete'"
                        ),
                        locator=f"{rel}:section[{sid}]",
                    )
                )
            elif _cell_is_unfilled(resolved[sid]):
                findings.append(
                    Finding(
                        rule_id="PP1",
                        severity=Severity.ERROR,
                        message=(
                            f"handoff pack required section {sid!r} is unfilled "
                            f"(placeholder or GAP in its Resolved? cell) -- fill it "
                            f"or record the blocking reason; the pack is incomplete"
                        ),
                        locator=f"{rel}:section[{sid}]",
                    )
                )
    return findings
