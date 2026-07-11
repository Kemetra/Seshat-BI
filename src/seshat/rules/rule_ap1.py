"""AP1 -- visual-qa <-> dashboard-qa anti-pattern parity (spec 085, idea B1).

Two committed docs carry the SAME thirteen visual-QA anti-patterns in DIFFERENT
structural formats:

  * ``docs/powerbi/visual-qa.md`` -- the prose home; each anti-pattern is a
    ``### N. Title`` heading.
  * ``.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md`` -- the
    check catalog; a pipe table ``| # | Anti-pattern | ... | Severity |``.

Both docs state the lockstep intent in prose ("same thirteen anti-patterns, same
names") but nothing enforces it, so an edit to one can silently drift from the
other. AP1 extracts the thirteen from BOTH with TWO format-specific extractors
(a single extractor no-ops on the format it was not written for -- a false green),
then fails fail-closed on any count / number->name / normalized-name divergence.

Owner ruling (ratified 2026-07-04, Ahmed Shaaban): ALIGN-FIRST, no synonym map.
The names are aligned to dashboard-qa.md (the fuller/canonical doc); AP1 enforces
exact equality under a minimal normalization (case-fold + whitespace-collapse
ONLY). No tolerance list, so nothing can rot.

Pure static markdown read: stdlib only, ``ctx.tracked_files`` only, no execution,
no DB, no Power BI, no numeric score, and it NEVER edits either doc (Principle V).
Generic governance docs, no tenant/brand literal (Principle VII).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, is_test_path
from ..registry import register

RULE_ID = "AP1"

VISUAL_QA_REL = "docs/powerbi/visual-qa.md"
DASHBOARD_QA_REL = ".claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md"

# The invariant count both docs must carry (spec FR-005/FR-013). A coordinated
# 14th anti-pattern must bump this in lockstep -- documented brittleness, not a bug.
EXPECTED_COUNT = 13

# visual-qa.md: "### 1. Too many visuals on a page"
_HEADING_RE = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
# dashboard-qa.md table data row: "| 1 | Too many visuals on one page | ... | ... |"
_TABLE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|")
# The catalog table's header row -- its 2nd cell names the anti-pattern column.
# Extraction is ANCHORED to the table that follows THIS header, so an unrelated
# numeric table elsewhere in the doc (e.g. a severity legend) is never read as an
# anti-pattern (Codex #181 P2a). A markdown table header cell "| # | Anti-pattern |".
_TABLE_HEADER_RE = re.compile(r"^\|\s*#\s*\|\s*anti-?pattern\b", re.IGNORECASE)
# A markdown separator row "|---|---|" -- allowed between the header and the data.
_TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|?\s*$")


def _normalize(name: str) -> str:
    """Minimal deterministic normalization: case-fold + whitespace-collapse ONLY.

    No synonym map (ratified align-first, spec FR-007). Two names are equal iff
    they match after this normalization.
    """
    return re.sub(r"\s+", " ", name).strip().casefold()


def _extract_headings(text: str) -> list[tuple[int, str]]:
    """Extract ``(number, raw_name)`` from the ``### N. Title`` heading format.

    Format-specific (FR-004): returns [] on the pipe-table format, which has no
    ``### N.`` headings.
    """
    out: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def _extract_table(text: str) -> list[tuple[int, str]]:
    """Extract ``(number, raw_name)`` from the anti-pattern CATALOG table only.

    Format-specific (FR-004): the ``### N.`` heading format yields zero rows.
    ANCHORED (Codex #181 P2a): extraction starts only after the catalog header
    ``| # | Anti-pattern | ... |`` and ends at the first line that is not a table
    row (or at a second header) -- so an unrelated numeric table elsewhere in the
    doc (a severity legend, a context table) is never counted as an anti-pattern.
    The ``|---|`` separator between header and data is allowed.
    """
    out: list[tuple[int, str]] = []
    in_catalog = False
    for line in text.splitlines():
        if _TABLE_HEADER_RE.match(line):
            in_catalog = True
            continue
        if not in_catalog:
            continue
        if _TABLE_SEP_RE.match(line):
            continue  # header/data separator row
        m = _TABLE_ROW_RE.match(line)
        if m:
            out.append((int(m.group(1)), m.group(2)))
            continue
        # First non-catalog-row line ends the catalog table (blank line, prose,
        # a new heading, or a foreign table's non-matching header).
        if line.strip():
            in_catalog = False
    return out


def _read(ctx: RuleContext, rel: str) -> str | None:
    try:
        return (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
    except OSError:
        return None


@register(
    RULE_ID, "visual-qa <-> dashboard-qa anti-pattern parity", tier=RuleTier.KIT_SELF
)
def check_ap1(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    # Both docs must be tracked (a fixture path never stands in for the real doc).
    tracked = set(ctx.tracked_files)
    for rel in (VISUAL_QA_REL, DASHBOARD_QA_REL):
        if rel not in tracked or is_test_path(rel):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"anti-pattern parity source not found as a tracked file: {rel}",
                    rel,
                )
            )
    if findings:
        return findings

    visual_text = _read(ctx, VISUAL_QA_REL)
    dash_text = _read(ctx, DASHBOARD_QA_REL)
    for rel, text in ((VISUAL_QA_REL, visual_text), (DASHBOARD_QA_REL, dash_text)):
        if text is None:
            findings.append(
                Finding(RULE_ID, Severity.ERROR, f"could not read {rel}", rel)
            )
    if findings:
        return findings

    visual = _extract_headings(visual_text)  # type: ignore[arg-type]
    dash = _extract_table(dash_text)  # type: ignore[arg-type]

    # FR-005: each doc's OWN list must carry exactly the expected count AND the
    # stable 1..EXPECTED_COUNT numbering (no duplicate number, no gap), before any
    # cross-doc compare -- a malformed own-list is a distinct, earlier error.
    # Count-only is insufficient: two docs can each carry 13 rows that reuse a
    # number and drop another (e.g. #7 twice, no #13) and still match each other,
    # a false green the prose's #-cross-references would break (Codex #181 P2b).
    own_list_bad = False
    expected_numbers = set(range(1, EXPECTED_COUNT + 1))
    for rel, entries in ((VISUAL_QA_REL, visual), (DASHBOARD_QA_REL, dash)):
        numbers = [n for n, _ in entries]
        if len(entries) != EXPECTED_COUNT:
            own_list_bad = True
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"{rel} lists {len(entries)} anti-patterns; expected "
                    f"{EXPECTED_COUNT} (its own list is malformed)",
                    rel,
                )
            )
        elif set(numbers) != expected_numbers or len(set(numbers)) != len(numbers):
            own_list_bad = True
            duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
            missing = sorted(expected_numbers - set(numbers))
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"{rel} anti-pattern numbering is malformed: expected the "
                    f"stable 1..{EXPECTED_COUNT} with no duplicate or gap "
                    f"(duplicate number(s): {duplicates or 'none'}; "
                    f"missing number(s): {missing or 'none'})",
                    rel,
                )
            )
    if own_list_bad:
        return findings

    # FR-006: compare by count (already equal here), number->name mapping, and
    # normalized-name membership. Both are 13 entries; compare position by number.
    visual_by_num = {n: name for n, name in visual}
    dash_by_num = {n: name for n, name in dash}

    for num in sorted(set(visual_by_num) | set(dash_by_num)):
        v_name = visual_by_num.get(num)
        d_name = dash_by_num.get(num)
        if v_name is None or d_name is None:
            present, absent = (
                (VISUAL_QA_REL, DASHBOARD_QA_REL)
                if v_name is not None
                else (DASHBOARD_QA_REL, VISUAL_QA_REL)
            )
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"anti-pattern #{num} is present in {present} but absent "
                    f"from {absent}",
                    f"{VISUAL_QA_REL}:#{num}",
                )
            )
            continue
        if _normalize(v_name) != _normalize(d_name):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"anti-pattern #{num} name diverges: visual-qa.md has "
                    f"{v_name!r}, dashboard-qa.md has {d_name!r} (align "
                    f"visual-qa.md to the dashboard-qa.md canonical name)",
                    f"{VISUAL_QA_REL}:#{num}",
                )
            )

    return findings
