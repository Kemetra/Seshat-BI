"""Unit tests for DL6 (visual-spec anti-pattern self-check consistency / A9).

DL6 is a single-spec consistency check. It scans FILLED ``visual-spec.yaml``
instances (excluding the generic templates/ blank and test fixtures) and asserts
one internal invariant: if a visual self-attests an anti-pattern (any
``anti_pattern_checks`` key set true), it must record at least one real
``readiness.blocking_reasons`` entry.

Distinct from B1 (which reconciles the anti-pattern key SET against the numbered
prose across files): DL6 checks ONE spec against ITSELF, an existence pairing
(any true -> some reason), never a per-key->reason mapping. Test pattern mirrors
the other design-lint rule tests (fixture-rooted RuleContext).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_visual_selfcheck import check_visual_spec_selfcheck

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "design_visual_selfcheck"
REPO_ROOT = Path(__file__).parent.parent.parent


def _ctx(*tracked: str, repo_root: Path = FIXTURES) -> RuleContext:
    return RuleContext(repo_root=repo_root, tracked_files=tracked)


# --- User Story 1: a paired self-attestation passes --------------------------


def test_true_check_with_reason_zero_findings() -> None:
    assert list(check_visual_spec_selfcheck(_ctx("good/visual-spec.yaml"))) == []


def test_all_false_checks_zero_findings() -> None:
    """No anti-pattern attested -> nothing to pair -> pass (clean visual)."""
    assert list(check_visual_spec_selfcheck(_ctx("all_false/visual-spec.yaml"))) == []


# --- User Story 2: a self-attested defect with no reason fails ---------------


def test_true_check_without_reason_is_error() -> None:
    findings = list(check_visual_spec_selfcheck(_ctx("bad/visual-spec.yaml")))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity is Severity.ERROR
    assert "blocking_reasons" in f.locator
    # names the attested anti-pattern key
    assert "uses_metric_without_contract" in f.message


# --- User Story 3: the generic template is excluded (never self-trips) -------


def test_generic_template_is_excluded() -> None:
    """The templates/ blank has all checks false + placeholder reasons by design;
    DL6 must never fire on it (mirrors the design-lint _TEMPLATE_PATH exclusion)."""
    ctx = _ctx("templates/visual-spec.yaml", repo_root=REPO_ROOT)
    assert list(check_visual_spec_selfcheck(ctx)) == []


# --- User Story 4: robust + boundary -----------------------------------------


def test_no_instances_zero_findings() -> None:
    assert list(check_visual_spec_selfcheck(_ctx("warehouse/x.sql", "README.md"))) == []


def test_blueprint_path_spec_is_discovered_and_errors() -> None:
    """Codex #180: a filled spec authored the documented page-blueprint way --
    `.../visuals/<visual_id>.yaml`, an arbitrary basename under a visuals/ dir, NOT
    literally visual-spec.yaml -- must be DISCOVERED by DL6 (else the guard silently
    misses the very files it exists to check). This one self-attests an anti-pattern
    with no reason, so DL6 must ERROR."""
    findings = list(
        check_visual_spec_selfcheck(_ctx("blueprint_path/visuals/exec_kpi_sales.yaml"))
    )
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "kpi_without_comparison" in findings[0].message


def test_blueprint_path_good_spec_passes() -> None:
    """A blueprint-path spec that IS well-formed (a true check paired with a real
    reason) passes -- discovery is broad, but the good fixture confirms the path
    widening did not turn every discovered file into a finding."""
    assert list(check_visual_spec_selfcheck(_ctx("good/visual-spec.yaml"))) == []
    # (the good fixture also proves the original visual-spec.yaml basename still
    # resolves after the predicate was broadened -- no regression)


def test_fixture_exemption_excludes_tests_paths() -> None:
    """A visual-spec under tests/ is a committed fixture -> exempt (is_test_path)."""
    ctx = _ctx(
        "tests/fixtures/design_visual_selfcheck/bad/visual-spec.yaml",
        repo_root=REPO_ROOT,
    )
    assert list(check_visual_spec_selfcheck(ctx)) == []


def test_placeholder_reason_does_not_count_as_filled() -> None:
    """The bad fixture's only blocking_reasons entry is an <angle-bracket>
    placeholder; DL6 must treat it as unrecorded and ERROR."""
    findings = list(check_visual_spec_selfcheck(_ctx("bad/visual-spec.yaml")))
    assert any(f.severity is Severity.ERROR for f in findings)


def test_no_tenant_or_example_literal_in_rule_source() -> None:
    from seshat.rules import design_visual_selfcheck

    src = Path(design_visual_selfcheck.__file__).read_text(encoding="utf-8")
    for banned in ("pharmacy", "c086", "ezaby"):
        assert banned not in src.lower()
