"""Integration test: Dashboard Semantic Audit (spec 123, US5, FR-017/018/019/020).

The audit is a report-level coherence check, DISTINCT from the shipped
per-visual anti-pattern QA (``docs/powerbi/visual-qa.md`` /
``.claude/skills/powerbi-dashboard-design/workflows/dashboard-qa.md``): it asks
whether the WHOLE report answers its committed Report Intent, not whether any
one visual is well-formed. It emits ONLY the spec-fixed closed enum verbatim
(FR-017) -- ``covered / incomplete / missing / conflicting / warning / blocked
/ not_applicable_with_reason`` -- and MUST NOT produce any numeric score or
ranking (FR-020/FR-035).

This test sits ON the real risk (memory: verifier must sit on the risk), not
adjacent to it:

- an intent question with NO page that traces to it -> ``missing`` (US5 AC#1);
- a diagnostic-purpose report with NO driver visual represented -> ``incomplete``
  (US5 AC#2) -- checked against driver VISUAL TYPES
  (key_influencers/decomposition_tree/smart_narrative), never the intent's
  ``driver_metrics`` list (those are metric roles, not visual evidence);
- a composition whose single page carries >1 distinct intent business_question
  -> ``conflicting`` (US5 AC#3) -- the mechanical, pinned-down trigger for "a
  page lacks one coherent purpose";
- FR-020 non-recomputation, proven by construction, not by inspecting the
  helper's source (that would be a circular oracle): the audit is handed a
  REAL committed ``a11y-rtl-readiness-checklist.md`` and a recorded
  dashboard-planner-verdict fixture in a tmp repo root that has NO
  ``design/tokens/...`` file present at all -- the audit still emits findings
  that CITE those two paths and ECHO their recorded dispositions, proving it
  read-and-cited rather than re-derived (it could not have re-derived CT1 --
  the token file it would need does not exist in this tmp root).
- FR-019: every finding (not just the three headline cases) carries non-empty
  cited evidence and a named owner_or_correction (pulled from the intent's own
  ``owner`` field, never hardcoded).
- FR-017/FR-035: every finding's category is one of the closed seven, and no
  finding's rendered text contains a percent/score token anywhere (mirrors
  SL1's ``_PERCENT_RE`` guard in ``src/seshat/rules/scorecard.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.semantic_audit import CATEGORIES, AuditSubject, run_semantic_audit

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_A11Y = (
    _REPO_ROOT
    / "mappings"
    / "retail_store_sales"
    / "design"
    / "a11y-rtl-readiness-checklist.md"
)

# Mirrors SL1's forbidden-score-token guard (a digit immediately followed by %).
_PERCENT_RE = re.compile(r"\d\s*%")


def _base_intent(**overrides: object) -> dict:
    intent = {
        "owner": "Ahmed Shaaban (report_owner)",
        "purpose": "monitoring",
        "business_questions": [
            {"question_id": "q1", "text": "How are we doing overall?"},
            {"question_id": "q2", "text": "How do sales trend over time?"},
        ],
        "outcome_metrics": [{"name": "TotalSales"}],
        "driver_metrics": [],
        "guardrail_metrics": [{"name": "DiscountedTransactionRate"}],
    }
    intent.update(overrides)
    return intent


def _page(
    page_id: str, question_ids: list[str], visuals: list[dict] | None = None
) -> dict:
    return {
        "page_id": page_id,
        "business_question_ids": question_ids,
        "visuals": visuals or [],
    }


def _composition(pages: list[dict]) -> dict:
    return {
        "pages": [
            {"page_id": p["page_id"], "order": i} for i, p in enumerate(pages, 1)
        ],
        "landing_page": pages[0]["page_id"] if pages else "",
    }


def _run(
    intent: dict, pages: list[dict], *, repo_root: Path = _REPO_ROOT, **cite_paths
):
    """Run the audit over an in-memory intent/pages, bundling them (plus the
    derived composition) into an AuditSubject -- the one call convention every
    test below shares, so the per-test bodies stay about the assertion.
    ``cite_paths`` forwards the optional planner_verdicts_path / a11y_checklist_path
    citations verbatim to :func:`run_semantic_audit`."""
    return run_semantic_audit(
        repo_root=repo_root,
        subject=AuditSubject(
            intent=intent, composition=_composition(pages), pages=pages
        ),
        **cite_paths,
    )


def _all_findings_well_formed(findings) -> None:
    """FR-017/019/020/035 invariants that must hold for EVERY finding emitted,
    not only the ones a specific test asserts a category for."""
    assert findings, "expected at least one finding"
    for f in findings:
        assert f.category in CATEGORIES
        assert f.evidence, f"finding {f.check!r} cites no evidence"
        assert f.owner_or_correction, f"finding {f.check!r} names no owner/correction"
        rendered = (
            f"{f.check} {f.category} {' '.join(f.evidence)} {f.owner_or_correction}"
        )
        assert not _PERCENT_RE.search(rendered), (
            f"finding {f.check!r} carries a score token"
        )


# --- US5 AC#1: an intent question with no page answering it -> missing -------


def test_intent_question_with_no_page_is_missing() -> None:
    intent = _base_intent()
    pages = [_page("overview", ["q1"])]  # q2 is never covered by any page
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    coverage_findings = [
        f for f in findings if f.check == "every_intent_question_covered"
    ]
    assert coverage_findings, "expected an every_intent_question_covered finding"
    missing = [f for f in coverage_findings if f.category == "missing"]
    assert missing, "an uncovered intent question must yield a 'missing' finding"
    assert any("q2" in e for f in missing for e in f.evidence)


@pytest.mark.parametrize(
    ("pages", "check"),
    [
        ([_page("overview", ["q1", "q2"])], "every_intent_question_covered"),
        (
            [_page("overview", ["q1"]), _page("trend", ["q2"])],
            "page_single_coherent_purpose",
        ),
    ],
    ids=["all-intent-questions-covered", "one-question-per-page"],
)
def test_check_reports_covered(pages: list[dict], check: str) -> None:
    """A well-formed report reports `covered` on both coherence checks: every intent
    question traces to a page (US5 AC#1), and each page carries a single business
    question (US5 AC#3)."""
    findings = _run(_base_intent(), pages)
    _all_findings_well_formed(findings)
    matched = [f for f in findings if f.check == check]
    assert matched, f"expected a {check} finding"
    assert all(f.category == "covered" for f in matched)


# --- US5 AC#2: diagnostic report with no driver VISUAL is incomplete --------


def test_diagnostic_report_with_no_driver_visual_is_incomplete() -> None:
    intent = _base_intent(purpose="diagnostic")
    # No driver-type visual anywhere (key_influencers/decomposition_tree/
    # smart_narrative) -- only a plain bar chart. intent.driver_metrics is
    # ALSO empty, but that must not be what the check reads (it reads visual
    # evidence, per the module docstring / data-model.md).
    pages = [
        _page(
            "overview",
            ["q1", "q2"],
            visuals=[{"visual_id": "v1", "visual_type": "bar_chart"}],
        )
    ]
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    driver_findings = [f for f in findings if f.check == "diagnostic_has_drivers"]
    assert driver_findings
    assert all(f.category in ("incomplete", "missing") for f in driver_findings)


def test_diagnostic_report_with_driver_visual_is_covered() -> None:
    intent = _base_intent(purpose="diagnostic")
    pages = [
        _page(
            "overview",
            ["q1", "q2"],
            visuals=[{"visual_id": "v1", "visual_type": "key_influencers"}],
        )
    ]
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    driver_findings = [f for f in findings if f.check == "diagnostic_has_drivers"]
    assert driver_findings
    assert all(f.category == "covered" for f in driver_findings)


def test_non_diagnostic_report_driver_check_is_not_applicable() -> None:
    intent = _base_intent(purpose="monitoring")
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    driver_findings = [f for f in findings if f.check == "diagnostic_has_drivers"]
    assert driver_findings
    assert all(f.category == "not_applicable_with_reason" for f in driver_findings)


# --- US5 AC#3: one page carrying >1 distinct business question -> conflicting


def test_page_with_multiple_business_questions_is_conflicting() -> None:
    intent = _base_intent()
    # ONE page mapped to BOTH q1 and q2 -- lacks one coherent purpose (the
    # mechanical, pinned-down trigger: >1 distinct intent business_question on
    # a single page).
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    purpose_findings = [
        f for f in findings if f.check == "page_single_coherent_purpose"
    ]
    assert purpose_findings
    conflicting = [f for f in purpose_findings if f.category == "conflicting"]
    assert conflicting, "a page answering >1 distinct question must be 'conflicting'"
    assert any("overview" in e for f in conflicting for e in f.evidence)


# --- FR-020: reuse committed outputs, never recompute (planner + a11y) ------


def test_reuses_recorded_planner_verdict_never_reruns_planner(tmp_path: Path) -> None:
    """The 'pages not duplicate' check reads a RECORDED planner-verdict fixture
    and cites it; it must never invoke the dashboard-planner's own set-relation
    logic (FR-020: reuse committed OUTPUTS, never recompute)."""
    subject_dir = tmp_path / "mappings" / "demo_table" / "design"
    subject_dir.mkdir(parents=True)
    verdicts_path = subject_dir / "dashboard-planner-verdicts.yaml"
    verdicts_path.write_text(
        "verdicts:\n"
        '  - proposal_page: "overview"\n'
        '    verdict: "new"\n'
        '    of_page: ""\n',
        encoding="utf-8",
    )

    intent = _base_intent()
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(
        intent,
        pages,
        repo_root=tmp_path,
        planner_verdicts_path=(
            "mappings/demo_table/design/dashboard-planner-verdicts.yaml"
        ),
    )

    _all_findings_well_formed(findings)
    dup_findings = [f for f in findings if f.check == "pages_not_duplicate"]
    assert dup_findings
    assert all(f.category == "covered" for f in dup_findings)
    assert any(
        "dashboard-planner-verdicts.yaml" in e for f in dup_findings for e in f.evidence
    )


def test_recorded_duplicate_planner_verdict_surfaces_as_conflicting(
    tmp_path: Path,
) -> None:
    subject_dir = tmp_path / "mappings" / "demo_table" / "design"
    subject_dir.mkdir(parents=True)
    verdicts_path = subject_dir / "dashboard-planner-verdicts.yaml"
    verdicts_path.write_text(
        "verdicts:\n"
        '  - proposal_page: "overview"\n'
        '    verdict: "duplicate"\n'
        '    of_page: "summary"\n',
        encoding="utf-8",
    )

    intent = _base_intent()
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(
        intent,
        pages,
        repo_root=tmp_path,
        planner_verdicts_path=(
            "mappings/demo_table/design/dashboard-planner-verdicts.yaml"
        ),
    )

    _all_findings_well_formed(findings)
    dup_findings = [f for f in findings if f.check == "pages_not_duplicate"]
    assert dup_findings
    assert any(f.category == "conflicting" for f in dup_findings)


def test_a11y_finding_cites_real_checklist_and_never_reads_design_tokens(
    tmp_path: Path,
) -> None:
    """The strongest FR-020 oracle: drop the REAL committed
    a11y-rtl-readiness-checklist.md into a tmp repo root that has NO
    design/tokens/ file present at all, and confirm the audit still emits a
    finding citing the checklist path and echoing its recorded roll-up status
    (`warning`, per the real file's `overall_status`). If the helper tried to
    RE-DERIVE CT1 contrast instead of reading the recorded disposition, it
    would have to open design/tokens/... which does not exist in this tmp
    root -- proving non-recomputation by construction, not by inspecting the
    helper's source (memory: verifier must sit on the risk, not be circular).
    """
    assert _REAL_A11Y.is_file(), (
        "fixture precondition: the real worked instance must exist"
    )

    dest_dir = tmp_path / "mappings" / "retail_store_sales" / "design"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / "a11y-rtl-readiness-checklist.md"
    dest.write_text(_REAL_A11Y.read_text(encoding="utf-8-sig"), encoding="utf-8")

    # Explicitly confirm no design/tokens/ exists in this tmp root -- so a
    # helper that tried to re-derive CT1 contrast would hard-fail, not silently
    # succeed by accident.
    assert not (tmp_path / "design" / "tokens").exists()

    intent = _base_intent()
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(
        intent,
        pages,
        repo_root=tmp_path,
        a11y_checklist_path=(
            "mappings/retail_store_sales/design/a11y-rtl-readiness-checklist.md"
        ),
    )

    _all_findings_well_formed(findings)
    a11y_findings = [
        f for f in findings if f.check == "accessibility_mobile_rtl_addressed"
    ]
    assert a11y_findings
    assert any(
        "a11y-rtl-readiness-checklist.md" in e
        for f in a11y_findings
        for e in f.evidence
    )
    # The real file's recorded roll-up is `warning` -- the audit must ECHO that
    # recorded disposition, not silently reclassify it as clean.
    assert any(f.category == "warning" for f in a11y_findings)


def test_missing_a11y_checklist_is_missing_not_fabricated(tmp_path: Path) -> None:
    intent = _base_intent()
    pages = [_page("overview", ["q1", "q2"])]
    findings = _run(
        intent,
        pages,
        repo_root=tmp_path,
        a11y_checklist_path=(
            "mappings/retail_store_sales/design/a11y-rtl-readiness-checklist.md"
        ),
    )

    _all_findings_well_formed(findings)
    a11y_findings = [
        f for f in findings if f.check == "accessibility_mobile_rtl_addressed"
    ]
    assert a11y_findings
    assert all(f.category == "missing" for f in a11y_findings)


# --- FR-035: closed enum + no numeric score, across the whole finding set ---


def test_no_numeric_score_anywhere_across_a_full_run() -> None:
    intent = _base_intent(purpose="diagnostic")
    pages = [
        _page(
            "overview",
            ["q1", "q2"],
            visuals=[{"visual_id": "v1", "visual_type": "card"}],
        )
    ]
    findings = _run(intent, pages)

    _all_findings_well_formed(findings)
    for f in findings:
        assert f.category in CATEGORIES


# --- Doc/module parity: the T028 skill workflow must never drift from the ---
# --- T029 module's closed enum (mirrors the visual-qa.md <-> dashboard-qa.md
# --- "keep the two in sync" discipline already used for the anti-pattern list).


def test_workflow_doc_carries_the_seven_value_enum_verbatim_and_no_percent() -> None:
    workflow_path = (
        _REPO_ROOT
        / ".claude"
        / "skills"
        / "powerbi-dashboard-design"
        / "workflows"
        / "dashboard-semantic-audit.md"
    )
    assert workflow_path.is_file(), "T028 workflow file must exist"
    text = workflow_path.read_text(encoding="utf-8")

    enum_line = (
        "covered | incomplete | missing | conflicting | warning | blocked | "
        "not_applicable_with_reason"
    )
    assert enum_line in text, (
        "the workflow doc must carry the FR-017 closed enum VERBATIM, in the "
        "module's declared order, or the two will drift"
    )
    assert set(CATEGORIES) == {
        "covered",
        "incomplete",
        "missing",
        "conflicting",
        "warning",
        "blocked",
        "not_applicable_with_reason",
    }
    assert not _PERCENT_RE.search(text), (
        "the workflow doc must carry no percent/score token"
    )


def test_module_categories_constant_matches_data_model_enum_exactly() -> None:
    """CATEGORIES is the single source of truth every check draws its
    ``category`` from; pin it against data-model.md's Semantic Audit Finding
    enum so a future edit cannot silently add/remove/rename a value."""
    assert CATEGORIES == frozenset(
        {
            "covered",
            "incomplete",
            "missing",
            "conflicting",
            "warning",
            "blocked",
            "not_applicable_with_reason",
        }
    )
