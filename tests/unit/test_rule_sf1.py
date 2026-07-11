"""Unit tests for SF1 (cross-layer checklist fork detector / I3).

SF1 globs skills/**/checklists/*.md, groups by basename, and reconciles every
2+-skill collision against the human-authored docs/quality/shared-spine.yaml
(shared = byte-identical; distinct = may differ). Fail-closed on undeclared
collisions, shared-drift, a bad enum value, and a missing manifest; WARN on a
stale entry and a moot distinct.

Fixture pattern: each scenario dir is a mini-repo (skills/**/checklists/*.md +
docs/quality/shared-spine.yaml); the test lists the scenario's files as tracked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.rule_sf1 import check_sf1

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "shared_fork"


def _ctx(scenario: str) -> RuleContext:
    """A context rooted at a scenario, tracking every file under it (posix rels)."""
    root = FIXTURES / scenario
    tracked = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    return RuleContext(repo_root=root, tracked_files=tuple(tracked))


def _one(scenario: str) -> list:
    return list(check_sf1(_ctx(scenario)))


# --- pass cases ---------------------------------------------------------------


def test_shared_identical_passes() -> None:
    assert _one("shared_identical") == []


def test_distinct_differ_passes() -> None:
    assert _one("distinct_differ") == []


def test_unique_basename_no_finding() -> None:
    assert _one("unique_basename") == []


# --- ERROR cases --------------------------------------------------------------


def test_undeclared_collision_is_error() -> None:
    findings = _one("undeclared")
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "undeclared" in findings[0].message
    assert "agg.md" in findings[0].message


def test_shared_drift_is_error() -> None:
    findings = _one("shared_drift")
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "diverging" in findings[0].message


def test_missing_manifest_is_error() -> None:
    findings = _one("missing_manifest")
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "not found" in findings[0].message


def test_bad_enum_value_is_error() -> None:
    findings = _one("bad_enum")
    assert any(
        f.severity is Severity.ERROR and "must be one of" in f.message for f in findings
    )


def test_three_copy_shared_drift_is_error() -> None:
    findings = _one("three_copy_shared")
    assert any(
        f.severity is Severity.ERROR and "diverging" in f.message for f in findings
    )


# --- WARNING cases ------------------------------------------------------------


def test_distinct_identical_is_warning() -> None:
    findings = _one("distinct_identical")
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "moot" in findings[0].message


def test_stale_entry_is_warning() -> None:
    findings = _one("stale_entry")
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARNING
    assert "no longer" in findings[0].message


# --- Codex #182 P2a: recursive checklist glob (skills/**/checklists/) ----------


def test_nested_skill_path_collision_is_detected() -> None:
    """Codex #182 P2a: the documented scope is skills/**/checklists/*.md, but the
    one-segment regex skipped a nested pack (skills/vendor/bi-python-knowledge/
    checklists/agg.md), missing a same-basename collision that must be declared.
    The nested copy collides with skills/bi-bigdata-knowledge/checklists/agg.md
    and is undeclared -> SF1 must ERROR."""
    findings = _one("nested_collision")
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "agg.md" in findings[0].message
    assert "undeclared" in findings[0].message


# --- SC-004: the rule never writes the manifest -------------------------------


def test_rule_source_has_no_write() -> None:
    src = (
        Path(__file__).parent.parent.parent / "src" / "seshat" / "rules" / "rule_sf1.py"
    ).read_text(encoding="utf-8")
    assert "write_text" not in src
    assert "write_bytes" not in src
