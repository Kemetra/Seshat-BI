"""Unit tests for DL4 (design-review evidence well-formedness gate / C1).

DL4 is a verify-slot-only completeness gate. It scans FILLED design-review
evidence instances (``**/design-review-evidence.md``, excluding the generic
templates/ blank) and asserts each required field is PRESENT and non-placeholder.

Distinct from RS1 (which checks that a dashboard_ready pass carries evidence[]
and an approvals[] entry at all): DL4 checks the SHAPE of the cited artifact --
the fields a well-formed design-review record must carry -- never whether the
design is good and never the approval itself. It mirrors PP1's discipline:
"slot filled != approved"; DL4 checks presence, grants nothing, writes nothing.

Required fields (structural, presence-only -- NEVER content-validated):
  page_id, anti_patterns_checked, contrast_pairs, reviewer, date.
The approval slot stays EMPTY for a human to sign; DL4 never fills or reads it
as a grant.

Test pattern mirrors the other design-lint rule tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_review_evidence import check_design_review_evidence

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "design_review"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


# --- User Story 1: a filled, well-formed instance passes ---------------------


def test_well_formed_instance_zero_findings() -> None:
    assert (
        list(check_design_review_evidence(_ctx("good/design-review-evidence.md"))) == []
    )


# --- User Story 2: a placeholder/missing field fails -------------------------


def test_placeholder_field_is_error_with_field_locator() -> None:
    findings = list(
        check_design_review_evidence(_ctx("placeholder/design-review-evidence.md"))
    )
    assert len(findings) >= 1
    f = findings[0]
    assert f.severity is Severity.ERROR
    # names the unfilled field
    assert "reviewer" in f.locator.lower() or "reviewer" in f.message.lower()


def test_missing_required_field_is_error() -> None:
    findings = list(
        check_design_review_evidence(_ctx("missing_field/design-review-evidence.md"))
    )
    assert len(findings) >= 1
    assert any("date" in (f.message + f.locator).lower() for f in findings)


# --- User Story 3: the generic template is excluded (never self-trips) -------


def test_generic_template_is_excluded() -> None:
    """The templates/ blank is full of <placeholder> tokens by design; DL4 must
    never fire on it (mirrors PP1's _TEMPLATE_PATH exclusion)."""
    ctx = _ctx("templates/design-review-evidence.md", repo_root=REPO_ROOT)
    assert list(check_design_review_evidence(ctx)) == []


def test_committed_template_is_wellformed_shape() -> None:
    """The real committed template must exist and carry every required field
    marker so an author knows the shape to fill (it is excluded from the scan,
    but its shape is what DL4 enforces on instances)."""
    tmpl = REPO_ROOT / "templates" / "design-review-evidence.md"
    assert tmpl.exists()
    text = tmpl.read_text(encoding="utf-8")
    for field in (
        "page_id",
        "anti_patterns_checked",
        "contrast_pairs",
        "reviewer",
        "date",
    ):
        assert field in text, f"template missing required field marker {field!r}"


# --- User Story 4: robust + boundary -----------------------------------------


def test_placeholder_only_list_section_is_error() -> None:
    """Codex #146: a list-section (anti_patterns_checked / contrast_pairs) whose
    only rows are still template placeholders is not filled -- DL4 must ERROR, not
    pass on the heading's mere presence."""
    findings = list(
        check_design_review_evidence(_ctx("empty_section/design-review-evidence.md"))
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)
    assert any(
        "anti_patterns_checked" in (f.message + f.locator)
        or "contrast_pairs" in (f.message + f.locator)
        for f in findings
    )


def test_no_instances_zero_findings() -> None:
    assert (
        list(check_design_review_evidence(_ctx("warehouse/x.sql", "README.md"))) == []
    )


def test_fixture_exemption_excludes_tests_paths() -> None:
    ctx = _ctx(
        "tests/fixtures/design_review/placeholder/design-review-evidence.md",
        repo_root=REPO_ROOT,
    )
    assert list(check_design_review_evidence(ctx)) == []


def test_approval_slot_is_never_read_as_grant() -> None:
    """DL4 checks structural fields only; an instance whose approval slot is
    EMPTY (the human hasn't signed) is still well-formed -- DL4 must not require
    the approval to be filled (that is RS1's approvals[] job, and the human's)."""
    assert (
        list(check_design_review_evidence(_ctx("good/design-review-evidence.md"))) == []
    )


def test_no_tenant_or_example_literal_in_rule_source() -> None:
    from seshat.rules import design_review_evidence

    src = Path(design_review_evidence.__file__).read_text(encoding="utf-8")
    for banned in ("pharmacy", "c086", "ezaby"):
        assert banned not in src.lower()
