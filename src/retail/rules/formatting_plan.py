"""Design-lint rule DL7: formatting-plan ledger well-formedness.

DL7 validates the SHAPE of a committed ``formatting-plan.md`` ledger (the
smart-formatting layer's DEFINE-side artifact). It checks that the plan is
structurally honest -- it does NOT and cannot check that a formatting choice is
good (that needs a human render; the loop is open by design). Specifically, per
committed ledger row / footer it ERRORs when:

  * a row is missing its ``principle_cited`` or ``token_cited`` (every decision
    must trace to a rubric anti-pattern + a token, or it is vibes);
  * ``principle_cited`` does not resolve to a real anti-pattern number
    (1-13 per docs/powerbi/visual-qa.md);
  * an APPLYABLE row cites a RENDER-ONLY anti-pattern (#1/#5/#6/#7) as its
    resolved principle -- a category error (bolding a title does not establish
    hierarchy; that is geometry, handoff-only);
  * the ledger contains a ``score:``/``confidence:`` FIELD (line-anchored, so
    prose mentioning "score" in a rationale cell does not trip -- hard rule #9);
  * a row's ``status`` self-declares a human-render OUTCOME (resolved/approved/
    ratified/pass/done) -- the agent may never call the result good (Principle V /
    never_self_grant_approval); allowed statuses are proposed / needs-owner-
    decision / blocked-orphan;
  * ``ratification.ratified_by`` is filled with an agent-shaped value (the agent
    is structurally forbidden to self-ratify -- Principle V);
  * a row's ``container`` is outside the adapter's formatting allow-list.

Read-only; stdlib only (re + string ops on the committed Markdown). Generic:
no tenant/example literal (Principle VII). Test fixtures exempted (is_test_path).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL7"

_LEDGER_SUFFIX = "formatting-plan.md"

# The 13 anti-patterns (docs/powerbi/visual-qa.md). Render-only = geometry/type,
# no property-level apply path; may not be cited as "resolved" by an applyable row.
_ALL_PRINCIPLES = frozenset(f"#{i}" for i in range(1, 14))
_RENDER_ONLY = frozenset({"#1", "#5", "#6", "#7"})

# The formatting containers the adapter may write (matches pbir_visual_format +
# pbir_page_background + pbir_theme_apply). A container outside this is off-limits.
_ALLOWED_CONTAINERS = frozenset(
    {"objects", "visualContainerObjects", "background", "themeCollection"}
)

# Line-anchored so it matches a real ``score:`` / ``confidence:`` FIELD (a list
# item or key), never the word "score" inside a prose rationale CELL. Anchoring
# also removes the need for a whole-document exemption (which, living in the
# copy-me template footer, could be pasted into a filled ledger and permanently
# disable the check).
_SCORE_RE = re.compile(r"^\s*-?\s*(score|confidence)\s*:", re.IGNORECASE | re.MULTILINE)

# Statuses that assert a HUMAN-render OUTCOME -- the agent may never self-declare
# any of these on any row (never_self_grant_approval / Principle V). The ledger's
# allowed statuses are proposed / needs-owner-decision / blocked-orphan.
_OUTCOME_STATUSES = frozenset({"resolved", "approved", "ratified", "pass", "done"})
_RATIFIED_RE = re.compile(r"ratified_by\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
# an agent-shaped ratifier value (empty or a quoted-empty is OK; a bare token or
# anything containing 'agent'/'claude'/'llm' is a forbidden self-ratify).
_AGENT_RATIFIER_RE = re.compile(r"agent|claude|llm|assistant", re.IGNORECASE)


def _iter_ledgers(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_LEDGER_SUFFIX)
        and not is_test_path(p)
        and not p.startswith("templates/")
    ]


def _table_rows(text: str) -> list[list[str]]:
    """Return the data rows (list of cell-lists) of the first pipe-table found.

    Skips the header row and the ``---|---`` separator; ignores non-table lines.
    """
    rows: list[list[str]] = []
    seen_header = False
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not seen_header:
            seen_header = True  # first table line is the header
            continue
        if all(set(c) <= {"-", ":"} for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows


# Column order per templates/formatting-plan.md (Task 1).
_COLS = (
    "target",
    "container",
    "group",
    "property",
    "value",
    "principle_cited",
    "token_cited",
    "apply_verb",
    "status",
    "rationale",
)


def _row(cells: list[str]) -> dict[str, str]:
    return {_COLS[i]: (cells[i] if i < len(cells) else "") for i in range(len(_COLS))}


@register(
    RULE_ID,
    "Formatting-plan ledger is well-formed (citations resolve, allow-list, no score)",
)
def check_formatting_plan(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_ledgers(ctx):
        path = ctx.repo_root / rel
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    f"ledger could not be read ({exc.__class__.__name__})",
                    f"{rel}#/",
                )
            )
            continue

        # footer-level checks (whole document). Line-anchored, so no exemption is
        # needed: prose mentioning "score" in a rationale cell no longer trips it.
        if _SCORE_RE.search(text):
            findings.append(
                Finding(
                    RULE_ID,
                    Severity.ERROR,
                    "ledger contains a score/confidence field; a formatting "
                    "plan is words-only, never a numeric score (rule #9)",
                    f"{rel}#score",
                )
            )
        m = _RATIFIED_RE.search(text)
        if m:
            val = m.group(1).strip().strip("'\"`")
            if val and _AGENT_RATIFIER_RE.search(val):
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"ratification.ratified_by is agent-filled ({val!r}); "
                        f"the agent may not self-ratify (Principle V)",
                        f"{rel}#ratified_by",
                    )
                )

        # row-level checks
        for i, cells in enumerate(_table_rows(text)):
            r = _row(cells)
            loc = f"{rel}#row{i + 1}"
            principle = r["principle_cited"]
            if not principle:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        "row is missing principle_cited (every decision must cite a "
                        "visual-qa.md anti-pattern)",
                        loc,
                    )
                )
            elif principle not in _ALL_PRINCIPLES:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"principle_cited {principle!r} does not resolve to a real "
                        f"anti-pattern (#1-#13 in docs/powerbi/visual-qa.md)",
                        loc,
                    )
                )
            if not r["token_cited"]:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        "row is missing token_cited (every decision must draw from a "
                        "committed design token)",
                        loc,
                    )
                )
            # A row may never self-declare a human-render OUTCOME status (the agent
            # cannot call the result good -- that is a human render + critique
            # outcome; never_self_grant_approval / Principle V). Applies to EVERY
            # row, not just render-only ones.
            status = r["status"].lower()
            if status in _OUTCOME_STATUSES:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"row status {r['status']!r} self-declares a human-render "
                        f"outcome; a plan row may only be proposed / "
                        f"needs-owner-decision / blocked-orphan -- resolution is a "
                        f"human render + critique, never self-declared (Principle V)",
                        loc,
                    )
                )
            # render-only anti-pattern cited as resolved/proposed by an applyable row
            applyable = r["apply_verb"] in ("A", "B", "C")
            proposed = status in ("resolved", "proposed")
            if applyable and proposed and principle in _RENDER_ONLY:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"applyable row cites render-only anti-pattern {principle} as "
                        f"{r['status']}; #1/#5/#6/#7 are geometry -- handoff-only, an "
                        f"apply verb cannot resolve them",
                        loc,
                    )
                )
            # container allow-list (empty container = a page/theme-level row is ok
            # only when apply_verb is A/C; a B row must name an allowed container)
            cont = r["container"]
            if cont and cont not in _ALLOWED_CONTAINERS:
                findings.append(
                    Finding(
                        RULE_ID,
                        Severity.ERROR,
                        f"container {cont!r} is not in the formatting allow-list "
                        f"{sorted(_ALLOWED_CONTAINERS)}",
                        loc,
                    )
                )
    return findings
