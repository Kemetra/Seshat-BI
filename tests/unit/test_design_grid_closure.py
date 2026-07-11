"""Unit tests for DL5 (grid arithmetic-closure self-check / A7).

DL5 recomputes, for each committed layout grid profile that declares a
column/row grid, whether the grid arithmetic CLOSES:

  usable_width  = canvas.width  - margin.left - margin.right
                == columns * column_width + (columns - 1) * gutter
  usable_height = canvas.height - margin.top  - margin.bottom
                == rows    * row_height    + (rows    - 1) * gutter

A profile whose recomputed usable dimension does NOT equal the grid-derived
dimension is an ERROR (the grid does not close). If the profile ALSO declares an
``arithmetic_check`` block, DL5 cross-checks the declared ``*_closes`` booleans
against the recomputation and ERRORs on a declared-vs-actual contradiction (a
stale hand-maintained check).

Grounded in the grid file's OWN declared geometry (Principle V -- DL5 invents no
numbers; it recomputes from committed fields and compares). A band-stack grid
with no ``column_width`` (e.g. a mobile portrait stack) has no closure to check
and is skipped. Read-only, stdlib arithmetic, no execution.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_grid_closure import check_grid_closure

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "grid"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


# --- User Story 1: the live committed 16x9 grid closes -> zero findings ------


def test_live_16x9_grid_closes_zero_findings() -> None:
    """Both committed 16x9 profiles close exactly (1232/672 and 1848/1008); DL5
    must not red the live grid."""
    ctx = _ctx("design/grids/16x9-grid.yaml", repo_root=REPO_ROOT)
    assert list(check_grid_closure(ctx)) == []


def test_live_mobile_grid_has_no_closure_to_check() -> None:
    """The mobile band-stack has no column_width closure -> DL5 skips it (no
    finding, no crash)."""
    ctx = _ctx("design/grids/mobile-grid.yaml", repo_root=REPO_ROOT)
    assert list(check_grid_closure(ctx)) == []


# --- User Story 2: a non-closing grid is caught ------------------------------


def test_width_does_not_close_is_error() -> None:
    findings = list(check_grid_closure(_ctx("bad_width/grid.yaml")))
    assert len(findings) >= 1
    f = findings[0]
    assert f.severity is Severity.ERROR
    assert "width" in f.message.lower()
    # the message states expected vs actual
    assert any(ch.isdigit() for ch in f.message)


def test_height_does_not_close_is_error() -> None:
    findings = list(check_grid_closure(_ctx("bad_height/grid.yaml")))
    assert any("height" in f.message.lower() for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_declared_check_contradicting_actual_is_error() -> None:
    """A profile that declares width_closes: true but does NOT close is a stale
    arithmetic_check -> ERROR on the declared-vs-actual contradiction."""
    findings = list(check_grid_closure(_ctx("stale_check/grid.yaml")))
    assert len(findings) >= 1
    assert any(
        "closes" in f.message.lower() or "declared" in f.message.lower()
        for f in findings
    )


# --- User Story 3: a clean synthetic grid passes; robust boundaries ----------


def test_synthetic_closing_grid_zero_findings() -> None:
    assert list(check_grid_closure(_ctx("good/grid.yaml"))) == []


def test_no_grid_files_zero_findings() -> None:
    assert list(check_grid_closure(_ctx("warehouse/x.sql", "README.md"))) == []


def test_malformed_grid_is_a_finding_not_a_crash() -> None:
    findings = list(check_grid_closure(_ctx("malformed/grid.yaml")))
    assert len(findings) >= 1
    assert any("could not be parsed" in f.message.lower() for f in findings)


def test_fixture_exemption_excludes_tests_paths() -> None:
    ctx = _ctx("tests/fixtures/grid/bad_width/grid.yaml", repo_root=REPO_ROOT)
    assert list(check_grid_closure(ctx)) == []


def test_no_tenant_or_example_literal_in_rule_source() -> None:
    from seshat.rules import design_grid_closure

    src = Path(design_grid_closure.__file__).read_text(encoding="utf-8")
    for banned in ("pharmacy", "c086", "ezaby"):
        assert banned not in src.lower()
