"""Unit tests for DL1 (theme JSON purity linter). Contract rows C1-C11.

Mirrors the pbir test pattern: point repo_root at the fixture dir and pass
fixture-relative tracked paths (without a ``tests/`` prefix) so the rule scans
them as live theme files. The tests/-exemption behavior (C10) is checked with a
``tests/``-prefixed path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_theme import RULE_ID, check_theme_purity

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "theme"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*theme_files: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=theme_files)


# --- User Story 1: a contaminated theme file fails (C1-C3) -------------------


def test_c1_one_forbidden_key_one_error_with_locator() -> None:
    findings = list(check_theme_purity(_ctx("one_forbidden.theme.json")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    assert f.locator == "one_forbidden.theme.json#/measure"
    assert "measure" in f.message.lower()


def test_c2_nested_forbidden_key_locator_points_at_nested_path() -> None:
    findings = list(check_theme_purity(_ctx("nested_forbidden.theme.json")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    # The locator walks the full key path to the nested offending key.
    assert f.locator == "nested_forbidden.theme.json#/visualStyles/card/*/kpi/threshold"


def test_c3_two_forbidden_keys_two_distinct_findings() -> None:
    findings = list(check_theme_purity(_ctx("two_forbidden.theme.json")))
    assert len(findings) == 2
    assert all(f.severity is Severity.ERROR for f in findings)
    locators = {f.locator for f in findings}
    assert locators == {
        "two_forbidden.theme.json#/measure",
        "two_forbidden.theme.json#/relationship",
    }


# --- User Story 2: a clean, allowed theme file passes (C4-C7) ----------------


def test_c4_allowed_only_zero_findings() -> None:
    assert list(check_theme_purity(_ctx("allowed_only.theme.json"))) == []


def test_c5_sentiment_color_allowed_zero_findings() -> None:
    assert list(check_theme_purity(_ctx("sentiment_color.theme.json"))) == []


def test_c6_current_committed_starter_theme_zero_findings() -> None:
    # The live starter theme, discovered via its real tracked path, must stay
    # green (SC-003): the rule does not break the current build.
    ctx = _ctx("themes/tower-retail.theme.json", repo_root=REPO_ROOT)
    assert list(check_theme_purity(ctx)) == []


def test_c7_value_equal_to_forbidden_word_not_flagged() -> None:
    # A VALUE string that equals a forbidden word is not a violation; only KEY
    # names are scanned (FR-005).
    assert list(check_theme_purity(_ctx("value_not_key.theme.json"))) == []


# --- User Story 3: generic + robust (C8-C11) --------------------------------


def test_c8_malformed_json_surfaces_a_finding_no_crash() -> None:
    findings = list(check_theme_purity(_ctx("malformed.theme.json")))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    assert "could not be parsed" in f.message.lower()
    assert f.locator == "malformed.theme.json#/"


def test_c9_no_theme_files_zero_findings_no_error() -> None:
    ctx = _ctx("warehouse/x.sql", "README.md")
    assert list(check_theme_purity(ctx)) == []


def test_c10_fixture_exemption_path_excluded_from_live_scan() -> None:
    # A forbidden-key theme file under the tests/ exemption path is NOT treated
    # as a live theme file (FR-010), so it emits no finding on the live scan.
    ctx = _ctx("tests/fixtures/theme/one_forbidden.theme.json", repo_root=REPO_ROOT)
    assert list(check_theme_purity(ctx)) == []


def test_c11_two_files_both_scanned_no_code_change() -> None:
    # Generic discovery scans every committed theme file, not a hardcoded list.
    findings = list(
        check_theme_purity(_ctx("one_forbidden.theme.json", "second_area.theme.json"))
    )
    locators = {f.locator for f in findings}
    assert locators == {
        "one_forbidden.theme.json#/measure",
        "second_area.theme.json#/calculatedColumn",
    }


def test_no_tenant_or_example_literal_in_vocabulary() -> None:
    # SC-005 / Principle VII: the rule's vocabulary carries no tenant/example/
    # brand-specific literal. The forbidden/allowed sets are generic contract
    # terms only.
    from seshat.rules import design_theme

    joined = " ".join(design_theme._FORBIDDEN_TOKENS) + " ".join(
        design_theme._ALLOWED_KEYS
    )
    for banned in ("pharmacy", "c086", "ezaby", "tower", "retail"):
        assert banned not in joined.lower()
