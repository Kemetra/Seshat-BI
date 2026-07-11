"""H3 -- decision-question answerability reconciler (spec 069).

The KPI knowledge skill publishes, per domain file, a "Decision questions this
domain answers" table: each row states a business question, a "Routes to" target
(a backtick-quoted contract path or the honest placeholder glyph), and a Status
("Seeded" / "Seeded (base)" / "Planned (...)"). Today that table is prose --
nothing checks that a question claimed answered actually routes to a contract
that exists, or that an unanswered question is honestly marked planned.

This rule parses every domain table and asserts, per row, categorically:

  - Status "Seeded" + a "Routes to" contract that EXISTS   -> pass
  - Status "Seeded" + a contract that does NOT exist       -> ERROR (dangling)
  - Status "Planned" + the honest placeholder glyph        -> pass
  - Status "Planned" + an EXISTING contract path           -> ERROR (stale marker)
  - anything else (neither resolvable nor honestly planned) -> WARNING

Principle V (FR-015): it checks route-resolution honesty ONLY. It never decides
whether a Planned KPI is "really" answerable, invents a contract, or rules which
side of a question/contract conflict is canonical -- it surfaces the drift and
stops. It emits no numeric score, percentage, or rollup (FR-010): strictly
per-question categorical. It is read-only (parse text + check file existence),
stdlib-only, and never executes, renders, or reaches a network/database.

Grounding notes honored (plan-review): a "Routes to" cell is a backtick-quoted
path optionally followed by a parenthetical qualifier (extract the backtick
path); Status is matched by ``startswith`` so "Seeded (base)" counts as Seeded;
the route resolves against the KPI skill ROOT, not the repo root or the domains
subfolder. On the current committed corpus the rule finds nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from ..core import Finding, RuleContext, RuleTier, Severity, is_test_path
from ..registry import register

RULE_ID = "AQ1"

_SKILL_ROOT = "skills/retail-kpi-knowledge"
_DOMAINS_RE = re.compile(r"^skills/retail-kpi-knowledge/domains/[^/]+\.md$")

# The honest placeholder glyph is the em dash; an ASCII hyphen is NOT equivalent
# (FR-008). A planned row uses this exact glyph in its "Routes to" cell.
_PLACEHOLDER = "—"

# The decision-question table lives under this heading (FR-003).
_TABLE_HEADING_RE = re.compile(r"(?im)^#+\s*Decision questions this domain answers\s*$")
# Extract the backtick-quoted contract path from a "Routes to" cell (FR-004);
# any trailing parenthetical qualifier is ignored.
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")


def _iter_domains(ctx: RuleContext) -> list[str]:
    return [
        p for p in ctx.tracked_files if _DOMAINS_RE.match(p) and not is_test_path(p)
    ]


def _table_rows(text: str) -> list[str]:
    """Return the raw ``|``-delimited data lines of the decision-question table."""
    m = _TABLE_HEADING_RE.search(text)
    if not m:
        return []
    rest = text[m.end() :]
    rows: list[str] = []
    seen_pipe = False
    for line in rest.splitlines():
        s = line.strip()
        if s.startswith("#") and seen_pipe:
            break  # next section ends the table
        if not s.startswith("|"):
            if seen_pipe:
                break  # a blank / non-pipe line after the table ends it
            continue
        seen_pipe = True
        rows.append(s)
    return rows


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= {"-", ":"} and c for c in cells)


def _is_header(cells: list[str]) -> bool:
    return cells and cells[0].lower().startswith("decision question")


def _no_corpus_finding() -> Finding:
    # FR-013: an absent corpus fails loud, never a vacuous pass.
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            "no KPI domain corpus found to check "
            f"({_SKILL_ROOT}/domains/*.md) -- cannot pass vacuously"
        ),
        locator=f"{_SKILL_ROOT}/domains",
    )


def _contract_exists(ctx: RuleContext, contract: str) -> bool:
    return (ctx.repo_root / _SKILL_ROOT / contract).exists()


def _malformed_finding(rel: str, raw: str) -> Finding:
    # FR-014: a row that does not parse into three columns is reported.
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.WARNING,
        message=(f"malformed decision-question row (expected 3 columns): {raw}"),
        locator=rel,
    )


@dataclass(frozen=True)
class _Row:
    """One parsed decision-question row: locator + its three parsed cells."""

    rel: str
    question: str
    status: str
    path_match: re.Match[str] | None
    route_is_placeholder: bool


def _classify_seeded(ctx: RuleContext, row: _Row) -> Finding | None:
    if row.path_match is None:
        # Seeded but no contract path to resolve -> neither category.
        return _warn_neither(row.rel, row.question, row.status)
    contract = row.path_match.group(1).strip()
    if _contract_exists(ctx, contract):
        return None
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"dangling route: question '{row.question}' is marked"
            f" Seeded but its contract '{contract}' does not exist"
            " -- fix the route or re-mark the row honestly"
        ),
        locator=row.rel,
    )


def _classify_planned(ctx: RuleContext, row: _Row) -> Finding | None:
    if row.route_is_placeholder:
        return None  # FR-005: honest planned row, no finding.
    if row.path_match is not None and _contract_exists(
        ctx, row.path_match.group(1).strip()
    ):
        # FR-017: contract was built but the row was never flipped.
        return Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=(
                f"stale planned marker: question '{row.question}' is"
                " marked Planned but its contract"
                f" '{row.path_match.group(1).strip()}' now exists --"
                " flip the row to Seeded"
            ),
            locator=row.rel,
        )
    return _warn_neither(row.rel, row.question, row.status)


def _classify_row(ctx: RuleContext, rel: str, raw: str) -> Finding | None:
    """Classify one raw table row into at most one Finding (or None to pass)."""
    cells = [c.strip() for c in raw.strip("|").split("|")]
    if _is_separator(cells) or _is_header(cells):
        return None
    if len(cells) != 3:
        return _malformed_finding(rel, raw)

    question, routes, status = cells
    path_match = _BACKTICK_PATH_RE.search(routes)
    row = _Row(
        rel=rel,
        question=question,
        status=status,
        path_match=path_match,
        route_is_placeholder=_PLACEHOLDER in routes and path_match is None,
    )

    if status.startswith("Seeded"):
        return _classify_seeded(ctx, row)
    if status.startswith("Planned"):
        return _classify_planned(ctx, row)
    return _warn_neither(rel, question, status)


def _read_domain(ctx: RuleContext, rel: str) -> tuple[str | None, Finding | None]:
    try:
        return (ctx.repo_root / rel).read_text(encoding="utf-8-sig"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, Finding(
            rule_id=RULE_ID,
            severity=Severity.ERROR,
            message=f"could not read domain file: {exc}",
            locator=rel,
        )


@register(
    RULE_ID,
    "Domain decision-question routes resolve or are honestly marked planned",
    tier=RuleTier.KIT_SELF,
)
def check_answerability(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    domains = sorted(_iter_domains(ctx))

    if not domains:
        return [_no_corpus_finding()]

    for rel in domains:
        text, read_error = _read_domain(ctx, rel)
        if read_error is not None:
            findings.append(read_error)
            continue

        for raw in _table_rows(text):
            finding = _classify_row(ctx, rel, raw)
            if finding is not None:
                findings.append(finding)
    return findings


def _warn_neither(rel: str, question: str, status: str) -> Finding:
    """FR-006: a row that is neither a resolvable Seeded nor an honest Planned."""
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.WARNING,
        message=(
            f"ambiguous row: question '{question}' (status '{status}') is neither a"
            " resolvable Seeded route nor an honest Planned placeholder"
        ),
        locator=rel,
    )
