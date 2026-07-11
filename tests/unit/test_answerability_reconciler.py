"""Unit tests for the Decision-Question Answerability Reconciler (spec 069, H3).

The rule globs the KPI-skill domain files, parses each "Decision questions this
domain answers" table, and per row asserts categorically:

  - Status "Seeded" + a "Routes to" contract that EXISTS   -> no finding
  - Status "Seeded" + a contract that does NOT exist       -> ERROR (dangling)
  - Status "Planned" + the honest placeholder glyph (em-)  -> no finding
  - Status "Planned" + an EXISTING contract path           -> ERROR (stale marker)
  - anything else (neither resolvable Seeded nor honest Planned) -> WARNING

It resolves "Routes to" against the KPI skill root, extracts the backtick-quoted
contract path (ignoring any trailing parenthetical qualifier), matches Status by
startswith (so "Seeded (base)" counts as Seeded), reads only committed text +
file existence, and emits no numeric score or rollup (categorical only).

Fixtures are planted under a temp KPI-skill tree so the parser is exercised
against committed-shape tables, mirroring the shipped routing-rule test harness.
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.answerability_reconciler import (
    RULE_ID,
    check_answerability,
)

pytestmark = pytest.mark.unit

_SKILL = "skills/retail-kpi-knowledge"
_DOMAINS = f"{_SKILL}/domains"
_CONTRACTS = f"{_SKILL}/contracts"
_PLACEHOLDER = "—"  # em dash, the honest planned placeholder glyph


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _findings(ctx):
    return [f for f in check_answerability(ctx) if f.rule_id == RULE_ID]


def _domain(name: str, rows: list[tuple[str, str, str]]) -> str:
    body = [
        f"# {name}\n",
        "## Decision questions this domain answers\n",
        "| Decision question | Routes to | Status |",
        "|-------------------|-----------|--------|",
    ]
    for q, routes, status in rows:
        body.append(f"| {q} | {routes} | {status} |")
    return "\n".join(body) + "\n"


# --------------------------------------------------------------------------- #
# US1 -- dangling Seeded route is an ERROR
# --------------------------------------------------------------------------- #
def test_seeded_resolvable_route_passes(tmp_path):
    files = {
        f"{_CONTRACTS}/net-sales.md": "# Net Sales\n",
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("How much did we sell?", "`contracts/net-sales.md`", "Seeded")],
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_seeded_dangling_route_is_error(tmp_path):
    files = {
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("How much did we sell?", "`contracts/gone.md`", "Seeded")],
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "contracts/gone.md" in findings[0].message
    assert "sales.md" in findings[0].locator


def test_seeded_route_with_parenthetical_qualifier_resolves(tmp_path):
    # The real corpus shape: `contracts/x.md` (sliced by branch key). The parser
    # must extract the backtick path, not the whole cell.
    files = {
        f"{_CONTRACTS}/net-sales.md": "# Net Sales\n",
        f"{_DOMAINS}/branch.md": _domain(
            "Branch",
            [
                (
                    "How much does each branch sell?",
                    "`contracts/net-sales.md` (sliced by branch key)",
                    "Seeded (base)",
                )
            ],
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


# --------------------------------------------------------------------------- #
# US1 -- honest Planned row passes; stale Planned marker is an ERROR
# --------------------------------------------------------------------------- #
def test_planned_with_placeholder_passes(tmp_path):
    files = {
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("How fast is growth?", _PLACEHOLDER, "Planned (needs prior period)")],
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_stale_planned_marker_pointing_at_existing_contract_is_error(tmp_path):
    files = {
        f"{_CONTRACTS}/net-sales.md": "# Net Sales\n",
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("How much did we sell?", "`contracts/net-sales.md`", "Planned")],
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "stale" in findings[0].message.lower()


# --------------------------------------------------------------------------- #
# US2 -- neither-category row is a WARNING
# --------------------------------------------------------------------------- #
def test_ambiguous_status_is_warning(tmp_path):
    files = {
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("Something?", _PLACEHOLDER, "TBD")],
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING


def test_seeded_with_placeholder_route_is_warning(tmp_path):
    # Seeded but route is the placeholder (status/route disagree) -> neither -> WARNING.
    files = {
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("Something?", _PLACEHOLDER, "Seeded")],
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING


# --------------------------------------------------------------------------- #
# US3 + edges -- generic glob, empty/absent corpus, malformed row
# --------------------------------------------------------------------------- #
def test_new_domain_file_is_checked_generically(tmp_path):
    files = {
        f"{_DOMAINS}/brand_new_domain.md": _domain(
            "BrandNew",
            [("New q?", "`contracts/missing.md`", "Seeded")],
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1 and findings[0].severity == Severity.ERROR


def test_domain_without_table_is_no_finding(tmp_path):
    files = {f"{_DOMAINS}/prose_only.md": "# Prose only\n\nNo table here.\n"}
    assert _findings(_ctx(tmp_path, files)) == []


def test_absent_corpus_fails_loud(tmp_path):
    # No domain files at all -> fail loud (FR-013), never a vacuous pass.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = _findings(ctx)
    assert any(f.severity == Severity.ERROR for f in findings)


def test_malformed_row_is_reported(tmp_path):
    # A row with the wrong column count under the table -> reported, not skipped.
    body = (
        "# Sales\n\n## Decision questions this domain answers\n"
        "| Decision question | Routes to | Status |\n"
        "|---|---|---|\n"
        "| only two | columns |\n"
    )
    files = {f"{_DOMAINS}/sales.md": body}
    findings = _findings(_ctx(tmp_path, files))
    assert any(
        f.severity in (Severity.ERROR, Severity.WARNING)
        and "malformed" in f.message.lower()
        for f in findings
    )


def test_findings_carry_no_numeric_score(tmp_path):
    files = {
        f"{_DOMAINS}/sales.md": _domain(
            "Sales",
            [("q?", "`contracts/gone.md`", "Seeded")],
        ),
    }
    for f in _findings(_ctx(tmp_path, files)):
        assert f.severity in (Severity.ERROR, Severity.WARNING)
