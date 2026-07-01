"""SL1 -- coverage-scorecard linter.

A committed per-table KPI coverage scorecard
(``mappings/<table>/<...>coverage-scorecard.md``) is the F8 artifact that answers, for
one source table, which KPIs can be served today -- as an explicit **status + named
blocker**, never a number (hard rule #9). Today nothing structurally enforces that a
FILLED scorecard is well-formed; SL1 makes four structural defects an ERROR.

SL1 validates STRUCTURE only. It NEVER adjudicates whether a stated "Covered" is
truly covered (that needs the table's real fields + the contract's real status -- a
Principle-V judgment). It checks, per row of the anchored status table:

  C1  the Coverage-status cell is one of the five closed enum values;
  C2  a ``Blocked -- ...`` row names a specific blocker (the Blocker cell is filled);
  C3  a ``Covered`` row's ``contracts/<file>.md`` path resolves to a tracked file
      (the contract-path-resolves invariant applies to Covered rows ONLY; Planned /
      Out of scope legitimately carry ``--``);
  C4  no ``<number>%`` token appears anywhere (the no-percentage / no-score law).

It is a pure static text read (parse committed markdown), never executes, opens no
connection, and modifies no scorecard/template file.

Ratified decisions (spec 056 ## Clarifications):
  - rule id ``SL1``; severity ERROR;
  - scan tracked ``mappings/**/*coverage-scorecard.md`` instances only -- the generic
    template file is excluded by explicit path (it is placeholders + an illustrative
    worked example by design), and ``tests/`` fixtures are excluded via is_test_path;
  - only rows in the anchored ``> Table:`` status table are parsed (a stray four-column
    table elsewhere contributes no rows);
  - no committed instance -> silent pass (mirrors PP1/G6); advances no readiness stage;
  - a tracked-but-unreadable instance fails loud (an ERROR), never crashes the gate.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

# Per-table scorecard instances live under mappings/<table>/ and end with this suffix.
# Restricting to mappings/ (not any tracked *coverage-scorecard.md) keeps a reference or
# doc file that happens to use the name from being parsed as a filled scorecard.
_INSTANCE_RE = re.compile(r"^mappings/[^/]+/.*coverage-scorecard\.md$")
_TEMPLATE_PATH = (
    "skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md"
)

# The five closed coverage statuses (F8 vocabulary). Compared after dash-normalization
# so an ASCII "--" and a unicode em-dash "—" both match.
_ENUM: frozenset[str] = frozenset(
    {
        "covered",
        "blocked -- missing field",
        "blocked -- needs business definition",
        "planned",
        "out of scope",
    }
)

# The status table is anchored by its per-table caption so only THIS table's rows are
# parsed; a stray four-column table in another section cannot contribute rows. The
# anchored region ends at the NEXT heading of ANY level (##, ###, ...) so a notes table
# under a deeper subheading is not swept in (C9 / FR-009).
_TABLE_ANCHOR_RE = re.compile(r"^>\s*Table:", re.IGNORECASE)
_NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+")

# A status-table data row, matched POSITIONALLY:
# | KPI | Contract | Coverage status | Blocker |
# The separator row (|---|---|) and the header row are filtered out separately.
_ROW_RE = re.compile(
    r"^\|\s*(?P<kpi>[^|]*?)\s*\|\s*(?P<contract>[^|]*?)\s*\|\s*(?P<status>[^|]*?)\s*\|\s*(?P<blocker>[^|]*?)\s*\|"
)
_SEP_RE = re.compile(r"^\|[\s:|-]+\|$")
# contracts/<file>.md inside an inline-code span or bare.
_CONTRACT_RE = re.compile(r"contracts/[^\s`|]+\.md")
# A number immediately followed by a percent sign -- the forbidden score token. A bare
# "%" with no adjacent digit (e.g. inside a KPI name) does not match.
_PERCENT_RE = re.compile(r"\d\s*%")


def _iter_scorecards(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _INSTANCE_RE.match(p) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _norm(cell: str) -> str:
    """Lower-case, strip backticks, and normalize dashes for the enum compare."""
    s = cell.strip().strip("`").strip().lower()
    s = s.replace("—", "--").replace("–", "--")  # em/en dash -> --
    s = re.sub(r"\s*--\s*", " -- ", s)  # collapse spacing around --
    return re.sub(r"\s+", " ", s).strip()


def _is_dash(cell: str) -> bool:
    s = cell.strip().strip("`").strip().replace("—", "--").replace("–", "--")
    return s in ("", "--")


def _status_table_rows(text: str) -> tuple[list[re.Match], list[str]]:
    """Parse the anchored '> Table:' status table.

    Returns ``(rows, malformed)`` where ``rows`` are the well-formed 4-column data-row
    matches and ``malformed`` are the raw text of table-ish lines (start with ``|``)
    inside the anchored region that FAIL the 4-column shape (e.g. a 3-cell row missing
    the Blocker column) -- those are flagged, never silently skipped.

    The region starts at the '> Table:' caption and ends at the FIRST of: a heading of
    any level, or -- once the table's rows have started -- a non-table, non-blank line
    that does NOT start with ``|`` (prose). A stray 4-column table under a '###'
    subheading or after intervening prose is therefore excluded (C9 / FR-009), while a
    malformed pipe-row within the table is reported (not dropped).
    """
    lines = text.splitlines()
    out: list[re.Match] = []
    malformed: list[str] = []
    in_section = False
    header_seen = False
    for line in lines:
        if _TABLE_ANCHOR_RE.match(line):
            in_section = True
            header_seen = False
            continue
        if not in_section:
            continue
        if _NEXT_HEADING_RE.match(line):
            break  # a new heading of any level ends the anchored table region
        if _SEP_RE.match(line):
            header_seen = True
            continue
        m = _ROW_RE.match(line)
        if not m:
            stripped = line.strip()
            if not stripped:
                continue
            # A pipe-started line that failed the 4-column shape is a MALFORMED row --
            # flag it (only after the table's data rows have begun). A non-pipe,
            # non-blank line is prose and ends the anchored region.
            if header_seen and stripped.startswith("|"):
                malformed.append(stripped)
                continue
            if header_seen:
                break
            continue
        # Skip the header row (the one before the separator) -- its status cell is the
        # literal column label, not a data value.
        if not header_seen:
            continue
        out.append(m)
    return out, malformed


@register("SL1", "Committed KPI coverage scorecard is structurally well-formed")
def check_coverage_scorecard(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    tracked = set(ctx.tracked_files)
    for rel in sorted(_iter_scorecards(ctx)):
        try:
            text = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            # A tracked-but-unreadable/undecodable scorecard fails loud (an ERROR),
            # rather than crashing the gate (UnicodeDecodeError is not an OSError).
            findings.append(
                Finding(
                    rule_id="SL1",
                    severity=Severity.ERROR,
                    message=f"could not read coverage scorecard: {exc}",
                    locator=rel,
                )
            )
            continue

        rows, malformed = _status_table_rows(text)
        for bad in malformed:
            findings.append(
                Finding(
                    rule_id="SL1",
                    severity=Severity.ERROR,
                    message=(
                        "coverage scorecard has a malformed status-table row "
                        "(not the required 4 columns | KPI | Contract | Coverage "
                        f"status | Blocker |): {bad}"
                    ),
                    locator=rel,
                )
            )
        for m in rows:
            kpi = m.group("kpi").strip()
            contract = m.group("contract")
            status_raw = m.group("status")
            blocker = m.group("blocker")
            status = _norm(status_raw)

            # C4: no <number>% token anywhere in the row.
            if _PERCENT_RE.search(m.group(0)):
                findings.append(
                    Finding(
                        rule_id="SL1",
                        severity=Severity.ERROR,
                        message=(
                            f"coverage scorecard row '{kpi}' contains a percentage/"
                            "score token; coverage is status + named blocker, never a "
                            "number (rule #9)"
                        ),
                        locator=rel,
                    )
                )

            # C1: status must be in the closed enum.
            if status not in _ENUM:
                findings.append(
                    Finding(
                        rule_id="SL1",
                        severity=Severity.ERROR,
                        message=(
                            f"coverage scorecard row '{kpi}' has status "
                            f"'{status_raw.strip()}' outside the allowed set "
                            "(Covered / Blocked -- missing field / Blocked -- needs "
                            "business definition / Planned / Out of scope)"
                        ),
                        locator=rel,
                    )
                )
                # enum unknown -> the status-conditional checks below don't apply
                continue

            # C2: a Blocked -- ... row must name a specific blocker.
            if status.startswith("blocked") and _is_dash(blocker):
                findings.append(
                    Finding(
                        rule_id="SL1",
                        severity=Severity.ERROR,
                        message=(
                            f"coverage scorecard row '{kpi}' is Blocked but names no "
                            "specific blocker (missing field or undecided policy)"
                        ),
                        locator=rel,
                    )
                )

            # C3: a Covered row's contract path must resolve to a tracked file. The
            # scorecard cites the contract as `contracts/<file>.md` under its skill
            # root (the F8 template's own convention), while the tracked file is e.g.
            # skills/retail-kpi-knowledge/contracts/<file>.md. So resolve by SUFFIX: the
            # citation is satisfied if any tracked file path ends with the cited
            # `contracts/<file>.md` (exact-match remains a subset of this).
            if status == "covered":
                cm = _CONTRACT_RE.search(contract)
                cited = cm.group(0) if cm else None
                resolves = cited is not None and any(
                    t == cited or t.endswith("/" + cited) for t in tracked
                )
                if not resolves:
                    findings.append(
                        Finding(
                            rule_id="SL1",
                            severity=Severity.ERROR,
                            message=(
                                f"coverage scorecard row '{kpi}' is Covered but its "
                                "contract path does not resolve to a tracked "
                                "contracts/<file>.md"
                            ),
                            locator=rel,
                        )
                    )
    return findings
