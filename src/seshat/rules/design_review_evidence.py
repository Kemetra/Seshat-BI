"""Design-lint rule DL4: design-review evidence well-formedness gate (C1).

A verify-slot-only completeness gate. DL4 scans FILLED design-review evidence
instances (``**/design-review-evidence.md``, excluding the generic templates/
blank) and asserts each required field is PRESENT and non-placeholder, so a
``dashboard_ready: pass`` can cite a well-formed evidence artifact.

DISTINCT FROM RS1 (Principle: no restatement of a shipped rule). RS1 checks a
``dashboard_ready`` pass carries evidence[] and a matching approvals[] entry AT
ALL. DL4 checks the SHAPE of the cited artifact -- the fields a well-formed
design-review record must carry. It never inspects whether the design is good
(the reviewer's judgment) and never reads/fills the approval slot (RS1 + a named
human own that). Mirrors PP1's discipline: "slot filled != approved"; DL4 checks
presence, grants nothing, writes nothing.

Required fields (structural presence-only, NEVER content-validated):
``page_id``, ``anti_patterns_checked``, ``contrast_pairs``, ``reviewer``,
``date``. A field left as an angle-bracket ``<placeholder>`` (the G6/PP1
convention) or absent is unfilled -> ERROR with a field-anchored locator.

Pure static markdown read: no execution, no DB, no Power BI, no approval grant.
Generic: field names only, no tenant/brand literal (Principle VII).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL4"

_INSTANCE_SUFFIX = "/design-review-evidence.md"
_TEMPLATE_PATH = "templates/design-review-evidence.md"

# The required fields a filled record must carry. The two list-sections
# (anti_patterns_checked, contrast_pairs) are checked for heading PRESENCE; the
# three scalar fields for a filled value on their bullet line.
_SCALAR_FIELDS: tuple[str, ...] = ("page_id", "reviewer", "date")
_SECTION_FIELDS: tuple[str, ...] = ("anti_patterns_checked", "contrast_pairs")

_PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def _iter_instances(ctx: RuleContext) -> list[str]:
    """Filled per-page instances; the generic template + fixtures are excluded."""
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_INSTANCE_SUFFIX) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _scalar_value(text: str, field: str) -> str | None:
    """The value on a ``- **field:** value`` bullet, or None if the bullet is absent."""
    m = re.search(
        rf"^-\s*\*\*{re.escape(field)}:\*\*\s*(?P<val>.*)$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if m is None:
        return None
    return m.group("val").strip()


def _is_unfilled(value: str) -> bool:
    """A scalar value is unfilled if empty or an angle-bracket placeholder."""
    stripped = value.strip().strip("`").strip()
    if not stripped:
        return True
    return bool(_PLACEHOLDER_RE.search(value))


def _section_lines(text: str, field: str) -> list[str] | None:
    """The lines under a ``### field`` heading up to the next heading.

    Returns None if the heading is absent; otherwise the section's body lines.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_section = False
    head_re = re.compile(rf"^#{{2,3}}\s+{re.escape(field)}\b", re.IGNORECASE)
    next_re = re.compile(r"^#{1,6}\s+")
    for line in lines:
        if head_re.match(line):
            in_section = True
            continue
        if in_section:
            if next_re.match(line):
                break
            out.append(line)
    return out if in_section else None


def _section_has_filled_row(body: list[str]) -> bool:
    """True if the section body has at least one table row that is not a
    placeholder-only row (i.e. a real, filled entry, not the template blank).

    A markdown table row starts with ``|``. The header row and the ``|---|``
    separator are ignored; a data row every cell of which is a ``<placeholder>``
    (or empty) does not count as filled.
    """
    for line in body:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|?\s*$", stripped):
            continue  # separator row |---|---|
        cells = [c.strip().strip("`").strip() for c in stripped.strip("|").split("|")]
        # Header row: skip the literal template header names.
        lowered = [c.lower() for c in cells]
        if lowered and lowered[0] in ("anti_pattern", "pair"):
            continue
        # A filled data row has at least one cell with real content (no
        # angle-bracket placeholder, non-empty).
        if any(c and not _PLACEHOLDER_RE.search(c) for c in cells):
            return True
    return False


@register(
    RULE_ID, "A filled design-review evidence record carries every required field"
)
def check_design_review_evidence(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(_iter_instances(ctx)):
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except OSError as exc:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"could not read design-review evidence: {exc}",
                    rel,
                )
            )
            continue

        for field in _SCALAR_FIELDS:
            value = _scalar_value(text, field)
            if value is None:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"design-review evidence is missing the required "
                        f"{field!r} field",
                        f"{rel}:field[{field}]",
                    )
                )
            elif _is_unfilled(value):
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"design-review evidence {field!r} field is unfilled "
                        f"(placeholder or empty); fill it before citing this "
                        f"record as dashboard_ready evidence",
                        f"{rel}:field[{field}]",
                    )
                )

        for field in _SECTION_FIELDS:
            body = _section_lines(text, field)
            if body is None:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"design-review evidence is missing the required "
                        f"{field!r} section",
                        f"{rel}:section[{field}]",
                    )
                )
            elif not _section_has_filled_row(body):
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"design-review evidence {field!r} section has no filled "
                        f"row (only template placeholders); record at least one "
                        f"real entry before citing this as dashboard_ready evidence",
                        f"{rel}:section[{field}]",
                    )
                )
    return findings
