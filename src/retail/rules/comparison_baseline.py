"""CB1 -- comparison-baseline declaration guard (idea H6).

A new OFF-SPINE retail-check integrity rule (a sibling of the additivity rule AD1
and the answerability rule AQ1) that reads the committed define-layer PROSE corpus
``skills/retail-kpi-knowledge/contracts/*.md`` and ERRORs when a GROWTH / COMPARISON
metric contract fails to DECLARE the two things a time comparison structurally needs:

  1. a **comparison baseline** -- what the current period is measured against
     (year-over-year / same-period-last-year / prior period). It may be RULED or
     honestly DISCLOSED as owner-pending; a SILENT omission is the defect.
  2. a **primary date field** in its Required fields -- a comparison is placed in
     time (a sale-date key / a marked date dimension / a date axis).

Detection is keyed on METRIC IDENTITY ONLY (the contract's title naming a growth /
same-store / like-for-like / year-to-date / period-over-period / year-over-year
comparison), NEVER on the presence of the baseline declaration itself. Keying on the
requirement would be CIRCULAR: a contract that OMITS the baseline could never be
detected as a comparison metric, so its omission would pass silently -- the rule would
be structurally incapable of catching its own target. High-PRECISION detection is
deliberate: a mis-worded comparison contract slipping through (false negative) is
cheaper than ERRORing a legitimate base metric (false positive) and eroding gate trust
-- the repo's Principle-V posture ("never manufacture a contract a human owns").

Principle V (mirrors AL1's tolerance of a disclosed open item): an honest
owner-pending baseline PASSES. The rule surfaces only a SILENT omission; it never
chooses a baseline for a human or forces an open ruling closed.

It is a pure static text read (stdlib ``re`` only), never executes, opens no
connection, renders no visual, emits ERROR-only categorical findings (no numeric
score), and modifies no artifact. On the current committed corpus it finds nothing
(the three comparison contracts -- net-sales-growth, same-store-sales-growth, ytd --
each declare a baseline (ruled or owner-pending) and a date field).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "CB1"

# The generic define-layer prose corpus (same as AD1). Generic glob, no
# worked-example path. The reference TEMPLATE in the tree is exempt (blank shape).
_CORPUS_RE = re.compile(r"^skills/retail-kpi-knowledge/contracts/[^/]+\.md$")
_TEMPLATE_RE = re.compile(
    r"^skills/retail-kpi-knowledge/references/.*template.*\.md$", re.I
)

_METRIC_TITLE_RE = re.compile(r"(?im)^#\s+(.+?)\s+--\s+Metric Contract\s*$")

# DETECTION (identity-only): a closed vocabulary of comparison/growth metric names,
# matched against the TITLE line only -- independent of the two requirements checked
# in the body, so a contract that omits the baseline is still detected as a comparison.
_COMPARISON_TITLE = (
    re.compile(r"\bgrowth\b", re.I),
    re.compile(r"\bsame[ -]store\b", re.I),
    re.compile(r"\blike[ -]for[ -]like\b", re.I),
    re.compile(r"\byear[ -]to[ -]date\b", re.I),
    re.compile(r"\bytd\b", re.I),
    re.compile(r"\bperiod[ -]over[ -]period\b", re.I),
    re.compile(r"\byear[ -]over[ -]year\b", re.I),
)

# REQUIREMENT 1 -- the comparison-baseline concept is addressed anywhere in the body,
# whether RULED or disclosed owner-pending. Any of these tokens counts as "addressed";
# their ABSENCE is the silent omission the rule targets.
_BASELINE_ADDRESSED = (
    re.compile(r"\bcomparison[ -]baseline\b", re.I),
    re.compile(r"\bbaseline\b", re.I),
    re.compile(r"\bsame[ -]period[ -]last[ -]year\b", re.I),
    re.compile(r"\bSPLY\b"),
    re.compile(r"\byear[ -]over[ -]year\b", re.I),
    re.compile(r"\bprior[ -]period\b", re.I),
    re.compile(r"\bprior[ -]year\b", re.I),
)

# REQUIREMENT 2 -- a primary DATE field in the Required-fields block: a sale-date key,
# a marked date dimension, or an explicit date axis. Closed vocabulary, hyphen-tolerant.
_DATE_FIELD = (
    re.compile(r"\bdate\s+key\b", re.I),
    re.compile(r"\bdate\s+dimension\b", re.I),
    re.compile(r"\bdate\s+axis\b", re.I),
    re.compile(r"\bdate\s+table\b", re.I),
    re.compile(r"\bdate\s+field\b", re.I),
)

_REQUIRED_HEADING_RE = re.compile(r"(?im)^\**required fields\**\s*$")


def _iter_corpus(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _CORPUS_RE.match(p) and not _TEMPLATE_RE.match(p) and not is_test_path(p)
    ]


def _title(text: str, rel: str) -> str:
    m = _METRIC_TITLE_RE.search(text)
    if m:
        return m.group(1).strip()
    return rel.rsplit("/", 1)[-1].removesuffix(".md")


def _is_comparison(title: str) -> bool:
    return any(pat.search(title) for pat in _COMPARISON_TITLE)


def _required_fields_block(text: str) -> str:
    """Prose from the Required-fields heading to the next ``**Heading**`` / ``#``."""
    m = _REQUIRED_HEADING_RE.search(text)
    if not m:
        return ""
    rest = text[m.end() :]
    out: list[str] = []
    for line in rest.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or re.match(r"^\*\*[^*]+\*\*\s*$", stripped):
            break  # next section heading ends the block
        out.append(stripped)
    return "\n".join(out)


def _baseline_addressed(text: str) -> bool:
    return any(pat.search(text) for pat in _BASELINE_ADDRESSED)


def _has_date_field(required_block: str) -> bool:
    return any(pat.search(required_block) for pat in _DATE_FIELD)


@register(
    RULE_ID,
    "Comparison/growth metric contract declares a baseline and a primary date field",
)
def check_comparison_baseline(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(_iter_corpus(ctx)):
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=f"could not read define-layer contract: {exc}",
                    locator=rel,
                )
            )
            continue

        title = _title(text, rel)
        if not _is_comparison(title):
            continue  # not a comparison/growth metric -- out of scope, no verdict

        if not _baseline_addressed(text):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"'{title}' is a comparison/growth metric but declares no"
                        " comparison baseline -- state the baseline (e.g. SPLY /"
                        " prior period), ruled or honestly owner-pending; the rule"
                        " never chooses it (Principle V)"
                    ),
                    locator=rel,
                )
            )

        if not _has_date_field(_required_fields_block(text)):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"'{title}' is a comparison/growth metric but its Required"
                        " fields name no primary date field (a sale-date key / marked"
                        " date dimension / date axis) -- a comparison must be placed"
                        " in time"
                    ),
                    locator=rel,
                )
            )
    return findings
