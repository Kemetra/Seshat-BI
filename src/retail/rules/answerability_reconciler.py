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


@register(
    RULE_ID,
    "Domain decision-question routes resolve or are honestly marked planned",
    tier=RuleTier.KIT_SELF,
)
def check_answerability(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    domains = sorted(_iter_domains(ctx))

    if not domains:
        # FR-013: an absent corpus fails loud, never a vacuous pass.
        return [
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    "no KPI domain corpus found to check "
                    f"({_SKILL_ROOT}/domains/*.md) -- cannot pass vacuously"
                ),
                locator=f"{_SKILL_ROOT}/domains",
            )
        ]

    for rel in domains:
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=f"could not read domain file: {exc}",
                    locator=rel,
                )
            )
            continue

        for raw in _table_rows(text):
            cells = [c.strip() for c in raw.strip("|").split("|")]
            if _is_separator(cells) or _is_header(cells):
                continue
            if len(cells) != 3:
                # FR-014: a row that does not parse into three columns is reported.
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.WARNING,
                        message=(
                            "malformed decision-question row"
                            f" (expected 3 columns): {raw}"
                        ),
                        locator=rel,
                    )
                )
                continue

            question, routes, status = cells
            path_match = _BACKTICK_PATH_RE.search(routes)
            route_is_placeholder = _PLACEHOLDER in routes and path_match is None

            if status.startswith("Seeded"):
                if path_match is None:
                    # Seeded but no contract path to resolve -> neither category.
                    findings.append(_warn_neither(rel, question, status))
                    continue
                contract = path_match.group(1).strip()
                if not (ctx.repo_root / _SKILL_ROOT / contract).exists():
                    findings.append(
                        Finding(
                            rule_id=RULE_ID,
                            severity=Severity.ERROR,
                            message=(
                                f"dangling route: question '{question}' is marked"
                                f" Seeded but its contract '{contract}' does not exist"
                                " -- fix the route or re-mark the row honestly"
                            ),
                            locator=rel,
                        )
                    )
            elif status.startswith("Planned"):
                if route_is_placeholder:
                    continue  # FR-005: honest planned row, no finding.
                if (
                    path_match is not None
                    and (
                        ctx.repo_root / _SKILL_ROOT / path_match.group(1).strip()
                    ).exists()
                ):
                    # FR-017: contract was built but the row was never flipped.
                    findings.append(
                        Finding(
                            rule_id=RULE_ID,
                            severity=Severity.ERROR,
                            message=(
                                f"stale planned marker: question '{question}' is"
                                " marked Planned but its contract"
                                f" '{path_match.group(1).strip()}' now exists --"
                                " flip the row to Seeded"
                            ),
                            locator=rel,
                        )
                    )
                else:
                    findings.append(_warn_neither(rel, question, status))
            else:
                findings.append(_warn_neither(rel, question, status))
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
