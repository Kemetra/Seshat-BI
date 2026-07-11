"""Unit tests for DL2 (background-spec purity linter). Contract rows C1-C13.

Mirrors the DL1/pbir test pattern: point repo_root at the fixture dir and pass
fixture-relative tracked paths (without a ``tests/`` prefix) so the rule scans
them as live filled background specs. The tests/-exemption behavior (C3) is
checked with a ``tests/``-prefixed path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_background import RULE_ID, check_background_purity

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "background"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*specs: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=specs)


def _fdc(spec: str, key: str) -> str:
    """A forbidden_dynamic_content locator for a fixture file + key."""
    return f"{spec}#/forbidden_dynamic_content/{key}"


def _qa(spec: str, item: str) -> str:
    """A qa_checklist locator for a fixture file + item."""
    return f"{spec}#/qa_checklist/{item}"


# --- US1: a filled spec that declares a defect fails (C5, C6, C10) ----------


def test_c5_one_forbidden_true_one_error_with_locator() -> None:
    findings = list(check_background_purity(_ctx("one_forbidden_true.background.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    assert f.locator == _fdc("one_forbidden_true.background.yaml", "contains_kpi_value")
    assert "contains_kpi_value" in f.message


def test_c6_two_forbidden_true_two_distinct_findings() -> None:
    findings = list(check_background_purity(_ctx("two_forbidden_true.background.yaml")))
    assert len(findings) == 2
    assert all(f.severity is Severity.ERROR for f in findings)
    locators = {f.locator for f in findings}
    spec = "two_forbidden_true.background.yaml"
    assert locators == {
        _fdc(spec, "contains_kpi_value"),
        _fdc(spec, "contains_dynamic_title"),
    }


def test_c10_bare_false_qa_item_one_finding() -> None:
    findings = list(check_background_purity(_ctx("qa_false_no_reason.background.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    assert f.locator == _qa(
        "qa_false_no_reason.background.yaml", "whitespace_preserved"
    )


# --- US2: a clean, compliant filled spec passes (C7, C11) -------------------


def test_c7_compliant_spec_zero_findings() -> None:
    assert list(check_background_purity(_ctx("compliant.background.yaml"))) == []


def test_c11_qa_false_with_reason_zero_findings() -> None:
    assert (
        list(check_background_purity(_ctx("qa_false_with_reason.background.yaml")))
        == []
    )


def test_sc005_same_item_false_reason_passes_no_reason_fails() -> None:
    # SC-005 pairing: the same qa item false+reason passes, false+no-reason fails.
    assert (
        list(check_background_purity(_ctx("qa_false_with_reason.background.yaml")))
        == []
    )
    assert (
        len(list(check_background_purity(_ctx("qa_false_no_reason.background.yaml"))))
        == 1
    )


# --- US3: generic, inert-until-filled, robust (C1-C4, C8, C9, C12, C13) ------


def test_c1_two_files_both_scanned_generic_discovery() -> None:
    findings = list(
        check_background_purity(
            _ctx("one_forbidden_true.background.yaml", "second_page.background.yaml")
        )
    )
    locators = {f.locator for f in findings}
    assert locators == {
        _fdc("one_forbidden_true.background.yaml", "contains_kpi_value"),
        _fdc("second_page.background.yaml", "contains_measure_or_metric"),
    }


def test_c2_template_is_exempt() -> None:
    # The blank template carries <true|false> placeholders; it is exempt from
    # discovery entirely and must produce zero findings even if tracked.
    ctx = _ctx("templates/background-spec.yaml", repo_root=REPO_ROOT)
    assert list(check_background_purity(ctx)) == []


def test_c3_fixture_exemption_path_excluded_from_live_scan() -> None:
    # A defect-declaring spec under the tests/ exemption path is NOT treated as a
    # live filled spec (FR-010), so it emits no finding on the live scan.
    ctx = _ctx(
        "tests/fixtures/background/one_forbidden_true.background.yaml",
        repo_root=REPO_ROOT,
    )
    assert list(check_background_purity(ctx)) == []


def test_c4_no_filled_spec_zero_findings_no_error() -> None:
    ctx = _ctx("warehouse/x.sql", "README.md")
    assert list(check_background_purity(ctx)) == []


def test_c8_placeholder_in_forbidden_key_finding() -> None:
    findings = list(check_background_purity(_ctx("placeholder.background.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity is Severity.ERROR
    assert "placeholder" in f.message.lower()
    assert f.locator == _fdc("placeholder.background.yaml", "contains_kpi_value")


def test_c9_non_boolean_forbidden_value_finding() -> None:
    findings = list(check_background_purity(_ctx("non_boolean.background.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity is Severity.ERROR
    assert "non-boolean" in f.message.lower()
    assert f.locator == _fdc("non_boolean.background.yaml", "contains_kpi_value")


def test_c12_malformed_yaml_surfaces_a_finding_no_crash() -> None:
    findings = list(check_background_purity(_ctx("malformed.background.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    assert "could not be parsed" in f.message.lower()
    assert f.locator == "malformed.background.yaml#/"


def test_c13_no_tenant_or_example_literal_in_vocabulary() -> None:
    # C13 / Principle VII: the rule's frozen vocabulary carries no tenant/example/
    # brand literal -- only generic contract terms from the template.
    from seshat.rules import design_background

    joined = (
        " ".join(design_background._FORBIDDEN_KEYS)
        + " "
        + " ".join(design_background._QA_ITEMS)
        + " "
        + design_background._BACKGROUND_SUFFIX
    )
    for banned in ("pharmacy", "c086", "ezaby", "tower", "retail"):
        assert banned not in joined.lower()


def test_vocabulary_matches_template_verbatim() -> None:
    # The 7 forbidden keys + 9 qa items are derived VERBATIM from the two declared
    # blocks in templates/background-spec.yaml (Clarifications Q2). This guards
    # against silent drift between the template contract and the rule vocabulary.
    import yaml

    from seshat.rules import design_background

    doc = yaml.safe_load(
        (REPO_ROOT / "templates" / "background-spec.yaml").read_text(encoding="utf-8")
    )
    assert set(design_background._FORBIDDEN_KEYS) == set(
        doc["forbidden_dynamic_content"]
    )
    assert set(design_background._QA_ITEMS) == set(doc["qa_checklist"])
