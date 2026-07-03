"""Unit tests for DL3 (token->theme fidelity reconciler / A1).

DL3 is the FIDELITY sibling of DL1 (purity): DL1 asserts a theme carries no
forbidden business-logic keys; DL3 asserts the styling VALUES a theme does carry
equal the values the design tokens declare they compile to.

Scope is DECLARED-correspondence only (Principle V -- the rule never invents a
mapping a human owns):
  * ``colors.data_colors[i] == theme.dataColors[i]`` -- positional, declared by
    the tokens comment "theme dataColors compiles from THIS list, T029".
  * ``colors.background == theme.background`` -- identity-named.
The sentiment map (success/warning/danger -> good/neutral/bad) and
text.primary -> foreground are OUT OF SCOPE for v1: the theme's middle sentiment
slot is amber, matching tokens ``warning`` by color but ``neutral`` by name (a
4->3 ambiguity a human must resolve), so DL3 v1 does not touch it.

Test pattern mirrors test_design_theme.py: point repo_root at a fixture dir and
pass fixture-relative tracked paths so the rule reconciles them as the live pair.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.design_theme_fidelity import check_theme_fidelity

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "theme_fidelity"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


# --- User Story 1: the live drift on main is caught (the RED case) -----------


def test_live_committed_pair_is_faithful() -> None:
    """The real tokens+theme on main are reconciled (owner ruled tokens canonical,
    2026-07-03): the theme's dataColors were updated to match the token
    data_colors, so DL3 finds no drift on the live pair. DL3's drift-detection
    behavior is proven by the fixture pairs (bg_drift / length_mismatch); this
    test guards that the committed design system stays faithful going forward.
    """
    ctx = _ctx(
        "design/tokens/tower-retail-design-tokens.yaml",
        "themes/tower-retail.theme.json",
        repo_root=REPO_ROOT,
    )
    assert list(check_theme_fidelity(ctx)) == []


# --- User Story 2: a faithful theme passes (selectivity) ---------------------


def test_matching_pair_zero_findings() -> None:
    """When every declared correspondence matches, DL3 emits nothing."""
    assert (
        list(check_theme_fidelity(_ctx("match/tokens.yaml", "match/theme.json"))) == []
    )


def test_background_identity_match_is_not_flagged() -> None:
    """colors.background == theme.background (both #FFFFFF) must stay green even
    when data_colors drift -- proves the rule is selective, not all-or-nothing."""
    findings = list(
        check_theme_fidelity(
            _ctx("bg_ok_colors_drift/tokens.yaml", "bg_ok_colors_drift/theme.json")
        )
    )
    assert all("/background" not in f.locator for f in findings)


def test_background_drift_flagged_with_locator() -> None:
    findings = list(
        check_theme_fidelity(_ctx("bg_drift/tokens.yaml", "bg_drift/theme.json"))
    )
    bg = [f for f in findings if f.locator.endswith("/background")]
    assert len(bg) == 1
    assert bg[0].severity is Severity.ERROR


# --- User Story 3: robust + generic (no crash, deferred scope untouched) -----


def test_length_mismatch_is_a_finding_not_an_index_crash() -> None:
    """If data_colors and dataColors differ in length, emit a Finding rather
    than crash on an out-of-range index."""
    findings = list(
        check_theme_fidelity(
            _ctx("length_mismatch/tokens.yaml", "length_mismatch/theme.json")
        )
    )
    assert any("length" in f.message.lower() for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_theme_missing_datacolors_is_error() -> None:
    """Codex #146: when the tokens declare data_colors but the theme drops
    dataColors entirely (or a non-list), DL3 must ERROR -- a theme with no
    categorical palette is a fidelity failure, not a silent pass."""
    findings = list(
        check_theme_fidelity(
            _ctx(
                "theme_missing_datacolors/tokens.yaml",
                "theme_missing_datacolors/theme.json",
            )
        )
    )
    dc = [f for f in findings if "dataColors" in f.locator or "dataColors" in f.message]
    assert len(dc) >= 1
    assert all(f.severity is Severity.ERROR for f in dc)
    assert any(
        "missing" in f.message.lower() or "not a list" in f.message.lower() for f in dc
    )


def test_sentiment_mapping_is_out_of_scope_v1() -> None:
    """DL3 v1 never reconciles the sentiment slots (deferred, human-owned 4->3
    map). A pair that differs ONLY on sentiment produces no finding."""
    findings = list(
        check_theme_fidelity(
            _ctx("sentiment_only_drift/tokens.yaml", "sentiment_only_drift/theme.json")
        )
    )
    assert findings == []


def test_missing_theme_zero_findings_no_error() -> None:
    """No tokens/theme pair among tracked files -> nothing to reconcile."""
    assert list(check_theme_fidelity(_ctx("warehouse/x.sql", "README.md"))) == []


def test_malformed_theme_surfaces_a_finding_no_crash() -> None:
    findings = list(
        check_theme_fidelity(_ctx("malformed/tokens.yaml", "malformed/theme.json"))
    )
    assert len(findings) >= 1
    assert any("could not be parsed" in f.message.lower() for f in findings)


def test_fixture_exemption_live_scan_excludes_tests_paths() -> None:
    """A tokens/theme pair under tests/ is a fixture, not the live pair."""
    ctx = _ctx(
        "tests/fixtures/theme_fidelity/bg_drift/tokens.yaml",
        "tests/fixtures/theme_fidelity/bg_drift/theme.json",
        repo_root=REPO_ROOT,
    )
    assert list(check_theme_fidelity(ctx)) == []


def test_no_tenant_or_example_literal_in_rule_source() -> None:
    """Principle VII: the rule carries no tenant/brand literal -- the field
    mapping is generic key names only."""
    from retail.rules import design_theme_fidelity

    src = Path(design_theme_fidelity.__file__).read_text(encoding="utf-8")
    # The generic theme key names are allowed; tenant/example literals are not.
    for banned in ("pharmacy", "c086", "ezaby"):
        assert banned not in src.lower()
