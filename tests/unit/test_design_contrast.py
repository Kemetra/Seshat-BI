"""Unit tests for CT1 (WCAG contrast pre-check / A3).

CT1 is a deterministic, read-only accessibility check: it computes the WCAG 2.x
sRGB relative-luminance contrast ratio between committed static token colors and
compares each declared text/background pair against the token-declared floor.
A pair below the floor is an ERROR with the computed ratio in the message; a
pair at/above the floor is clean.

DECLARED pairs only (Principle V -- the rule checks the correspondences the
tokens themselves annotate as "AA on bg", never invents which pairs matter):
  * ``colors.text.{primary,secondary,muted}`` vs ``colors.background`` at the
    ``accessibility.min_text_contrast_ratio`` floor (WCAG AA normal text).

The ratio is deterministic arithmetic on committed hexes, NOT a fabricated
confidence score (hard rule #9): it is a pass/fail categorical test against a
declared threshold.

Test pattern mirrors test_design_theme.py / test_design_theme_fidelity.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_contrast import (
    RULE_ID,
    _contrast_ratio,
    check_contrast,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "contrast"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


# --- The luminance/ratio math is correct (WCAG reference values) -------------


def test_black_on_white_is_21_to_1() -> None:
    # WCAG's canonical maximum contrast ratio.
    assert round(_contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_white_on_white_is_1_to_1() -> None:
    assert round(_contrast_ratio("#FFFFFF", "#FFFFFF"), 2) == 1.0


def test_ratio_is_symmetric() -> None:
    a = _contrast_ratio("#1A1D21", "#FFFFFF")
    b = _contrast_ratio("#FFFFFF", "#1A1D21")
    assert round(a, 4) == round(b, 4)


# --- User Story 1: a low-contrast text pair fails (below the floor) ----------


def test_low_contrast_text_pair_is_error_with_ratio() -> None:
    findings = list(check_contrast(_ctx("bad/tokens.yaml")))
    assert len(findings) >= 1
    f = findings[0]
    assert f.rule_id == RULE_ID
    assert f.severity is Severity.ERROR
    # the computed ratio and the floor both appear in the message
    assert ":1" in f.message
    assert "text" in f.locator or "text" in f.message.lower()


# --- User Story 2: an all-AA-passing token set is clean ----------------------


def test_all_pairs_pass_zero_findings() -> None:
    assert list(check_contrast(_ctx("good/tokens.yaml"))) == []


def test_live_committed_tokens_text_pairs_meet_aa() -> None:
    """The real conservative palette on main is designed to clear AA for text on
    the near-white background -- CT1 must not red the live token set."""
    ctx = _ctx("design/tokens/tower-retail-design-tokens.yaml", repo_root=REPO_ROOT)
    findings = list(check_contrast(ctx))
    assert findings == [], (
        f"live tokens unexpectedly fail AA: {[f.message for f in findings]}"
    )


# --- User Story 3: robust + generic ------------------------------------------


def test_no_tokens_file_zero_findings() -> None:
    assert list(check_contrast(_ctx("warehouse/x.sql", "README.md"))) == []


def test_missing_floor_is_a_finding_not_a_crash() -> None:
    """A tokens file with text/background but no declared floor cannot be checked
    -> surface a finding, never crash or silently pass."""
    findings = list(check_contrast(_ctx("no_floor/tokens.yaml")))
    assert len(findings) >= 1
    assert any(
        "floor" in f.message.lower() or "ratio" in f.message.lower() for f in findings
    )


def test_malformed_hex_is_a_finding_not_a_crash() -> None:
    findings = list(check_contrast(_ctx("bad_hex/tokens.yaml")))
    assert len(findings) >= 1
    assert any(
        "could not" in f.message.lower() or "invalid" in f.message.lower()
        for f in findings
    )


def test_fixture_exemption_excludes_tests_paths() -> None:
    ctx = _ctx("tests/fixtures/contrast/bad/tokens.yaml", repo_root=REPO_ROOT)
    assert list(check_contrast(ctx)) == []


def test_no_tenant_or_example_literal_in_rule_source() -> None:
    from seshat.rules import design_contrast

    src = Path(design_contrast.__file__).read_text(encoding="utf-8")
    for banned in ("pharmacy", "c086", "ezaby"):
        assert banned not in src.lower()
