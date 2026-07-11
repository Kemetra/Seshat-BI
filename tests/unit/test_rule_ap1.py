"""Unit tests for AP1 (visual-qa <-> dashboard-qa anti-pattern parity / B1).

AP1 extracts the thirteen anti-patterns from BOTH docs with TWO format-specific
extractors and fails fail-closed on any count / number->name / normalized-name
divergence. Owner-ratified align-first (no synonym map): exact normalized-name
equality after the owner aligns visual-qa.md to the dashboard-qa.md canonical
names.

Fixture pattern mirrors the other rule tests: each scenario dir carries BOTH docs
at their real relative paths; the test points repo_root at the scenario and lists
those two paths as tracked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.rule_ap1 import (
    DASHBOARD_QA_REL,
    VISUAL_QA_REL,
    _extract_headings,
    _extract_table,
    _normalize,
    check_ap1,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "antipattern_parity"


def _ctx(scenario: str) -> RuleContext:
    """A context rooted at a fixture scenario, tracking both parity docs."""
    return RuleContext(
        repo_root=FIXTURES / scenario,
        tracked_files=(VISUAL_QA_REL, DASHBOARD_QA_REL),
    )


# --- US1: aligned pair passes -------------------------------------------------


def test_good_aligned_pair_zero_findings() -> None:
    assert list(check_ap1(_ctx("good"))) == []


# --- US1: count / drift cases each ERROR --------------------------------------


def test_count_mismatch_is_error_before_compare() -> None:
    findings = list(check_ap1(_ctx("count_mismatch")))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "malformed" in findings[0].message
    assert findings[0].locator == VISUAL_QA_REL


def test_dropped_entry_is_error_naming_the_gap() -> None:
    # dashboard-qa.md skips #7 and adds #14 (13 rows, numbering {1-6,8-14}). This
    # is a malformed OWN-list numbering (gap + out-of-range), which the own-list
    # numbering guard (Codex #181 P2b) catches before the cross-doc compare -- an
    # earlier, more precise error than the old "#7 absent across docs" path. The
    # gap is still named (the missing 7).
    findings = list(check_ap1(_ctx("dropped_entry")))
    assert findings, "a number gap must ERROR"
    assert all(f.severity is Severity.ERROR for f in findings)
    joined = " ".join(f.message for f in findings)
    assert "7" in joined  # the dropped number is named (either "#7" or "missing 7")


def test_renamed_entry_is_error_naming_both_strings() -> None:
    findings = list(check_ap1(_ctx("renamed_entry")))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "#6" in findings[0].message
    assert "diverges" in findings[0].message


def test_reordered_is_error() -> None:
    findings = list(check_ap1(_ctx("reordered")))
    assert findings, "a number->name reorder must ERROR"
    assert all(f.severity is Severity.ERROR for f in findings)


def test_malformed_own_list_is_error() -> None:
    findings = list(check_ap1(_ctx("malformed_own")))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "malformed" in findings[0].message
    assert findings[0].locator == VISUAL_QA_REL


# --- US2: format-specific extractors (the reviewer's fragility flag) ----------


def test_heading_extractor_returns_empty_on_table_format() -> None:
    table_text = (
        "| # | Anti-pattern | Rule | Severity |\n"
        "|---|--------------|------|----------|\n"
        "| 1 | Too many visuals on one page | r | warning |\n"
    )
    assert _extract_headings(table_text) == []


def test_table_extractor_returns_empty_on_heading_format() -> None:
    heading_text = "### 1. Too many visuals on one page\n\nBody.\n"
    assert _extract_table(heading_text) == []


def test_each_extractor_returns_thirteen_from_its_own_doc() -> None:
    root = FIXTURES / "good"
    vis = (root / VISUAL_QA_REL).read_text(encoding="utf-8")
    dash = (root / DASHBOARD_QA_REL).read_text(encoding="utf-8")
    assert len(_extract_headings(vis)) == 13
    assert len(_extract_table(dash)) == 13


# --- Codex #181 P2 hardening: extractor specificity + duplicate numbers --------


def test_foreign_numeric_table_is_not_read_as_anti_patterns() -> None:
    """Codex #181 P2a: dashboard-qa.md carries a valid 13-row catalog PLUS an
    unrelated numeric table (a severity legend). The extractor must anchor to the
    anti-pattern catalog only -- reading the legend rows would inflate the count
    and falsely ERROR (or, worse, mask a real drift). A well-formed pair with a
    foreign numeric table present must still PASS."""
    assert list(check_ap1(_ctx("foreign_numeric_table"))) == []


def test_duplicate_number_is_error_even_when_both_docs_share_it() -> None:
    """Codex #181 P2b: both docs reuse #7 and omit #13 (13 rows each). The naive
    number->name dict collapses the duplicate, so a pure cross-doc compare returns
    green even though neither doc carries the stable 1..13 numbering the prose
    cross-references. AP1 must validate each doc's OWN numbering (no dupes, no gaps)
    and ERROR."""
    findings = list(check_ap1(_ctx("duplicate_number")))
    assert findings, "a duplicate/gapped own-list numbering must ERROR"
    assert all(f.severity is Severity.ERROR for f in findings)
    joined = " ".join(f.message for f in findings).lower()
    assert "7" in joined or "13" in joined or "number" in joined


# --- US3: normalization is case-fold + whitespace only, NO synonym map --------


def test_normalize_casefold_and_whitespace_only() -> None:
    assert _normalize("Too  Many   Visuals") == _normalize("too many visuals")
    # NO synonym map: "a page" and "one page" must NOT be treated as equal.
    assert _normalize("on a page") != _normalize("on one page")


# --- missing source doc is a fail-closed ERROR --------------------------------


def test_missing_source_doc_is_error() -> None:
    ctx = RuleContext(repo_root=FIXTURES / "good", tracked_files=(VISUAL_QA_REL,))
    findings = list(check_ap1(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == DASHBOARD_QA_REL
