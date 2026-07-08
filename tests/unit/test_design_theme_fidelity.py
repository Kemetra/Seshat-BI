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


# --- DL8: sentiment 4->3 fidelity (opt-in, inert until owner declares the map) --

from retail.rules.design_theme_fidelity import (  # noqa: E402
    SENTIMENT_RULE_ID,
    check_sentiment_fidelity,
)


def test_sentiment_map_absent_is_zero_findings_refuse_to_invent() -> None:
    """No meta.sentiment_map -- DL8 must never guess a correspondence
    (Principle V). Reuses the DL3 sentiment-drift fixture, which has
    colors.sentiment but no map."""
    findings = list(
        check_sentiment_fidelity(
            _ctx("sentiment_only_drift/tokens.yaml", "sentiment_only_drift/theme.json")
        )
    )
    assert findings == []


def test_sentiment_map_declared_but_malformed_is_error_not_silent() -> None:
    """A botched opt-in (a declared meta.sentiment_map with a blank/non-string
    value) must ERROR -- silently treating it as 'no map' would disable the
    guard the author asked for while the spec still claims fidelity is verified.
    """
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_bad_value/tokens.yaml",
                "sentiment_map_bad_value/theme.json",
            )
        )
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)
    assert any("malformed" in f.message.lower() for f in findings)


def test_sentiment_map_faithful_is_zero_findings() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_faithful/tokens.yaml",
                "sentiment_map_faithful/theme.json",
            )
        )
    )
    assert findings == []


def test_sentiment_map_drift_is_error_with_locator() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx("sentiment_map_drift/tokens.yaml", "sentiment_map_drift/theme.json")
        )
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(f.rule_id == SENTIMENT_RULE_ID for f in findings)
    assert any("sentiment" in f.locator for f in findings)


def test_sentiment_map_missing_key_is_error() -> None:
    """A declared map key with no counterpart on either side ERRORs (never
    silently drops the mapping)."""
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_missing_key/tokens.yaml",
                "sentiment_map_missing_key/theme.json",
            )
        )
    )
    assert len(findings) >= 1
    assert all(f.severity is Severity.ERROR for f in findings)


def test_sentiment_map_malformed_tokens_is_error_not_crash() -> None:
    findings = list(
        check_sentiment_fidelity(
            _ctx(
                "sentiment_map_malformed/tokens.yaml",
                "sentiment_map_malformed/theme.json",
            )
        )
    )
    assert len(findings) >= 1
    assert any("could not be parsed" in f.message.lower() for f in findings)


def test_sentiment_rule_id_is_dl8_not_dl3() -> None:
    assert SENTIMENT_RULE_ID == "DL8"


def test_dl3_still_ignores_sentiment_after_dl8_lands() -> None:
    """Regression guard: adding DL8 must not change check_theme_fidelity's
    behavior -- DL3 stays sentiment-blind."""
    from retail.rules.design_theme_fidelity import check_theme_fidelity

    findings = list(
        check_theme_fidelity(
            _ctx("sentiment_only_drift/tokens.yaml", "sentiment_only_drift/theme.json")
        )
    )
    assert findings == []


def test_sentiment_live_pairs_are_green_on_main() -> None:
    """emits-on-main guard for both committed pairs:

    * executive-dark now DECLARES an owner-ratified meta.sentiment_map (T19,
      2026-07-08) that is byte-exact faithful to its theme -- DL8 fires but
      finds zero drift (green because faithful, NOT because inert).
    * tower-retail declares NO map, so DL8 is inert-by-absence on it -- proving
      the rule refuses to invent a correspondence even though tower's sentiment
      colors actually drift.
    """
    from retail.rules.design_theme_fidelity import _load_yaml, _sentiment_map_for

    exec_dark = _ctx(
        "design/tokens/executive-dark-design-tokens.yaml",
        "themes/executive-dark.theme.json",
        repo_root=REPO_ROOT,
    )
    tower = _ctx(
        "design/tokens/tower-retail-design-tokens.yaml",
        "themes/tower-retail.theme.json",
        repo_root=REPO_ROOT,
    )
    # executive-dark declares a map and is faithful -> zero findings
    exec_doc, _ = _load_yaml(
        REPO_ROOT / "design/tokens/executive-dark-design-tokens.yaml"
    )
    assert _sentiment_map_for(exec_doc) == {
        "success": "good",
        "warning": "neutral",
        "danger": "bad",
    }
    assert list(check_sentiment_fidelity(exec_dark)) == []
    # tower-retail declares no map -> inert by absence
    tower_doc, _ = _load_yaml(
        REPO_ROOT / "design/tokens/tower-retail-design-tokens.yaml"
    )
    assert _sentiment_map_for(tower_doc) is None
    assert list(check_sentiment_fidelity(tower)) == []
