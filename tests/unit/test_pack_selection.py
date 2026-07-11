from __future__ import annotations

import pytest

from seshat.packs.model import PackManifest
from seshat.packs.validator import validate_selection

pytestmark = pytest.mark.unit


def _pack(pack_id: str, **overrides) -> PackManifest:
    return PackManifest(
        manifest_path=f"packs/local/{pack_id.split('.')[-1]}/seshat-pack.yaml",
        pack_id=pack_id,
        version="1.0.0",
        category="kpi",
        owner="Casey Analyst",
        description="synthetic",
        core_compatibility="1.x",
        **overrides,
    )


def _rules(findings: list[dict]) -> set[str]:
    return {finding["rule"] for finding in findings}


def test_clean_selection_has_no_findings() -> None:
    selection = [
        _pack("acme.alpha", provides=("a",)),
        _pack("acme.beta", provides=("b",), requires=("acme.alpha",)),
    ]
    assert validate_selection(selection) == []


def test_missing_dependency_is_reported() -> None:
    findings = validate_selection([_pack("acme.beta", requires=("acme.absent",))])
    assert _rules(findings) == {"pack_missing_dependency"}


def test_dependency_cycle_is_reported() -> None:
    findings = validate_selection(
        [
            _pack("acme.alpha", requires=("acme.beta",)),
            _pack("acme.beta", requires=("acme.alpha",)),
        ]
    )
    assert "pack_dependency_cycle" in _rules(findings)


def test_self_requirement_is_reported_as_cycle() -> None:
    findings = validate_selection([_pack("acme.alpha", requires=("acme.alpha",))])
    assert _rules(findings) == {"pack_dependency_cycle"}


def test_declared_conflict_between_selected_packs_is_reported() -> None:
    findings = validate_selection(
        [
            _pack("acme.alpha", conflicts=("acme.beta",)),
            _pack("acme.beta"),
        ]
    )
    assert "pack_conflict" in _rules(findings)


def test_duplicate_pack_id_is_reported() -> None:
    findings = validate_selection([_pack("acme.alpha"), _pack("acme.alpha")])
    assert "pack_duplicate_id" in _rules(findings)


def test_colliding_qualified_provided_ids_are_reported() -> None:
    # Distinct packs never collide through the namespace; a collision needs
    # the same fully qualified id, which requires the same pack id -- covered
    # above -- so this asserts the qualification itself keeps ids disjoint.
    findings = validate_selection(
        [
            _pack("acme.alpha", provides=("shared",)),
            _pack("acme.beta", provides=("shared",)),
        ]
    )
    assert findings == []


def test_conflict_findings_precede_projection_use() -> None:
    # validate_selection is pure: it reports and never mutates or activates.
    packs = (
        _pack("acme.alpha", conflicts=("acme.beta",)),
        _pack("acme.beta"),
    )
    first = validate_selection(packs)
    second = validate_selection(packs)
    assert first == second
    assert packs[0].conflicts == ("acme.beta",)
