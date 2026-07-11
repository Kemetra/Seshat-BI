"""Unit tests for CT2 (adjacent ramp deltaE76 floor)."""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_ramp_deltae import RULE_ID, check_ramp_deltae

pytestmark = pytest.mark.unit

_TOKENS_DECLARED = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#346699"
accessibility:
  min_adjacent_delta_e: 10.0
"""

_TOKENS_MISSING_KEY = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#346699"
accessibility:
  min_text_contrast_ratio: "4.5:1"
"""


def test_ct2_flags_near_collapsed_pair_when_floor_declared(tmp_path) -> None:
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(_TOKENS_DECLARED, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert findings[0].severity == Severity.ERROR
    assert "#336699" in findings[0].message
    assert "#346699" in findings[0].message


def test_ct2_missing_declared_floor_is_silent_skip(tmp_path) -> None:
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(_TOKENS_MISSING_KEY, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert findings == []


def test_ct2_passing_ramp_yields_no_finding(tmp_path) -> None:
    tokens = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#12263A"
accessibility:
  min_adjacent_delta_e: 10.0
"""
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(tokens, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert findings == []


def test_ct2_ignores_nonadjacent_collision(tmp_path) -> None:
    """CT2 must only walk ADJACENT pairs, never the whole set (that is CT3).

    Palette: colors[0]="#336699" and colors[2]="#346699" are near-identical
    (deltaE76 ~0.20, well below the 10.0 floor) but are NOT adjacent.
    Both adjacent pairs -- (0,1) and (1,2) -- measure ~32.6, well above the
    floor. If CT2 ever regressed to a CT3-style whole-set i<j scan, the
    (0,2) collision would be flagged and this test would fail.
    """
    tokens = """
meta:
  name: "t"
colors:
  data_colors:
    - "#336699"
    - "#12263A"
    - "#346699"
accessibility:
  min_adjacent_delta_e: 10.0
"""
    p = tmp_path / "x-design-tokens.yaml"
    p.write_text(tokens, encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=("x-design-tokens.yaml",))
    findings = list(check_ramp_deltae(ctx))
    assert findings == []
