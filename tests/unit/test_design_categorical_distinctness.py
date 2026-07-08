"""Unit tests for CT3 (categorical distinctness whole-set pre-check).

CT3 is a deterministic, read-only accessibility check: it computes the CIE76
deltaE76 Euclidean Lab distance between every i<j pair of committed
`colors.data_colors` entries and compares the minimum against a token-declared
`accessibility.min_categorical_deltae` floor. A collapse below the floor is an
ERROR naming both hexes and the computed distance.

Missing declared floor -> SILENT SKIP, not ERROR (Principle V / emits-on-main):
this is a normal-vision near-collapse guard, not a colorblind-safe claim, and
a tokens file that never opted in must stay clean on main.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.design_categorical_distinctness import (
    RULE_ID,
    check_categorical_distinctness,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "categorical_distinctness"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ct3_id_is_registered() -> None:
    assert RULE_ID == "CT3"


def test_missing_floor_key_is_silent_skip(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#2FB6C5'\n",
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []


def test_near_identical_pair_below_floor_errors(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        (
            "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#2FB6C5'\n"
            "    - '#12263A'\n"
            "accessibility:\n  min_categorical_deltae: 2.0\n"
        ),
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    findings = list(check_categorical_distinctness(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert findings[0].severity == Severity.ERROR
    assert "#2FB6C4" in findings[0].message
    assert "#2FB6C5" in findings[0].message


def test_distinct_palette_at_or_above_floor_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        (
            "colors:\n  data_colors:\n    - '#2FB6C4'\n    - '#12263A'\n"
            "accessibility:\n  min_categorical_deltae: 2.0\n"
        ),
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    assert list(check_categorical_distinctness(ctx)) == []


def test_malformed_tokens_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    # An unterminated quoted scalar is unparseable YAML -- the rule must
    # surface a clean ERROR finding, never raise.
    _write(
        tmp_path / "design" / "tokens" / "demo-design-tokens.yaml",
        "colors:\n  data_colors:\n    - '#2FB6C4\n",
    )
    ctx = _ctx("design/tokens/demo-design-tokens.yaml", repo_root=tmp_path)
    findings = list(check_categorical_distinctness(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert findings[0].severity == Severity.ERROR
    assert "could not be parsed" in findings[0].message.lower()


def test_committed_executive_dark_tokens_are_clean_on_main() -> None:
    rel = "design/tokens/executive-dark-design-tokens.yaml"
    ctx = _ctx(rel, repo_root=REPO_ROOT)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []  # no min_categorical_deltae declared yet -> skip


def test_committed_tower_retail_tokens_are_clean_on_main() -> None:
    rel = "design/tokens/tower-retail-design-tokens.yaml"
    ctx = _ctx(rel, repo_root=REPO_ROOT)
    findings = list(check_categorical_distinctness(ctx))
    assert findings == []  # no min_categorical_deltae declared yet -> skip
