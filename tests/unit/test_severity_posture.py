"""Golden-file snapshot test for the severity-posture lock (feature 044).

Asserts the committed ``docs/rules/severity-posture.json`` matches the LIVE
severity posture observed by forcing every registered rule (and the L3
governance surface) to fire over minimal synthetic fixtures. Fails closed on any
drift -- a rule whose emitted severity set changes (an ERROR dropping out of
``{ERROR, WARNING}``, a class added, a rule added/removed) without regenerating
the record breaks this test. The fix is always: run ``retail severity-posture``
and commit the record in the same change.

This test adds NO new ``EXPECTED_RULE_ID`` and registers NO rule -- it is a
test-only golden assertion, not a ``retail check`` rule. Comparison is by parsed
DATA (not raw text), so a cross-platform CRLF round-trip cannot flake it
(FR-012).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retail.severity_posture import (
    L3_KEY,
    NO_FINDING_MARKER,
    RECORD_REL_PATH,
    _live_rules,
    build,
    render,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD_PATH = _REPO_ROOT / RECORD_REL_PATH
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "severity"

_REGEN_HINT = (
    "severity-posture record is out of date. Regenerate it and commit the result "
    "in the same change:\n    retail severity-posture\n"
)

# Example-domain identifier tokens that must NEVER appear in a generic artifact or
# a planted fixture (Principle VII). The lock test scans the planted fixture FILES
# itself because is_test_path exempts them from the live rules (SC-007).
_EXAMPLE_DOMAIN_TOKENS = (
    "retail_store_sales",
    "pharmacy",
    "c086",
)


def _load_committed() -> dict:
    # Parse JSON (line-ending agnostic) so a Windows CRLF round-trip under
    # core.autocrlf cannot flake this comparison (FR-012).
    return json.loads(_RECORD_PATH.read_text(encoding="utf-8"))


def test_committed_record_matches_live_posture() -> None:
    """The committed record equals the freshly observed live posture (US1, FR-003)."""
    assert _RECORD_PATH.exists(), f"{RECORD_REL_PATH} does not exist. " + _REGEN_HINT
    expected = build()
    committed = _load_committed()

    if committed != expected:
        # Actionable message: name each drifted rule + its recorded-vs-observed
        # severity-set delta, then the regen hint (FR-003 / FR-004).
        exp_reg = expected["registered"]
        com_reg = committed.get("registered", {})
        exp_ids = set(exp_reg)
        com_ids = set(com_reg)
        missing = sorted(exp_ids - com_ids)  # live but absent from record
        stale = sorted(com_ids - exp_ids)  # in record but no longer live
        drifted = sorted(
            f"{i}: recorded={com_reg[i]} observed={exp_reg[i]}"
            for i in exp_ids & com_ids
            if exp_reg[i] != com_reg[i]
        )
        l3_delta = ""
        if expected["l3"] != committed.get("l3"):
            l3_delta = (
                f"\n  L3 drift: recorded={committed.get('l3')} "
                f"observed={expected['l3']}"
            )
        pytest.fail(
            "severity-posture drift:\n"
            f"  missing (live but not recorded): {missing}\n"
            f"  stale (recorded but not live): {stale}\n"
            f"  class-set drift: {drifted}" + l3_delta + "\n" + _REGEN_HINT
        )


def test_generation_is_idempotent() -> None:
    """Generating twice yields byte-identical output (determinism, SC-002/SC-003)."""
    assert render() == render()


def test_record_adds_no_new_rule_and_no_expected_rule_id() -> None:
    """Record adds NO new registered rule and NO new EXPECTED_RULE_ID (FR-007/SC-004).

    The registered section's entry count equals the live registry size (this
    feature is test-only). The L3 entry lives in a SEPARATE section, so it neither
    inflates nor satisfies the registered count.
    """
    rules = _live_rules()
    data = build()
    assert len(data["registered"]) == len(rules)
    # No EXPECTED_RULE_ID is referenced or introduced by this feature; the L3 key
    # is a record section key, never a registry id.
    assert L3_KEY not in data["registered"]


def test_registered_section_covers_exactly_the_live_rule_ids() -> None:
    """Registered section id set == live registered-rule-id set (SC-006, T015).

    Fails closed on a missing or stale rule. The L3 section is asserted SEPARATELY
    (next test); it is not a registered rule, so it neither satisfies nor breaks
    the registered-set equality.
    """
    live_ids = {r.id for r in _live_rules()}
    recorded_ids = set(build()["registered"])
    assert recorded_ids == live_ids


def test_l3_section_is_recorded_separately_with_error_and_warning() -> None:
    """L3 surface is its own named section -> [error, warning] (FR-010, T015)."""
    data = build()
    assert set(data["l3"]) == {L3_KEY}
    assert data["l3"][L3_KEY] == ["error", "warning"]


def test_multi_class_rule_records_both_error_and_warning() -> None:
    """Multi-class SQL guard-form rule S4b records BOTH classes (SC-001/FR-009).

    The set is never collapsed: dropping the last ERROR branch would remove ERROR
    from the set, which is exactly the drift the lock catches.
    """
    s4b = build()["registered"]["S4b"]
    assert s4b == ["error", "warning"]


def test_no_silent_no_finding_omission() -> None:
    """Every recorded entry is either a real class set or the EXPLICIT marker (FR-011).

    A rule that cannot be forced to fire records ``["<no-finding>"]`` rather than
    being silently omitted -- so the lock still fails closed if it later begins or
    ceases to emit a finding.
    """
    data = build()
    for entry in list(data["registered"].values()) + list(data["l3"].values()):
        assert entry, "an empty severity entry would be a silent blind spot"
        if entry == [NO_FINDING_MARKER]:
            continue
        assert all(c in ("error", "warning", "info") for c in entry), entry


def test_planted_fixtures_are_generic() -> None:
    """Planted fixture files carry NO example-domain identifier (SC-005/SC-007, T007).

    is_test_path exempts these from the live rules, so this lock test is the only
    thing that scans them. Scans every committed file under the severity fixture
    tree for example-domain tokens.
    """
    scanned = 0
    for path in _FIXTURE_DIR.rglob("*"):
        if not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for token in _EXAMPLE_DOMAIN_TOKENS:
            assert token not in text, (
                f"{path.relative_to(_REPO_ROOT)} contains example-domain token "
                f"{token!r}; fixtures must be generic (SC-007)"
            )
    assert scanned > 0, "no planted severity fixtures found to scan"


def test_committed_record_is_generic() -> None:
    """The committed record carries only generic rule ids + classes (SC-005)."""
    text = _RECORD_PATH.read_text(encoding="utf-8").lower()
    for token in _EXAMPLE_DOMAIN_TOKENS:
        assert token not in text, f"record contains example-domain token {token!r}"
    # Only the three severity class values + the marker may appear as leaf values.
    data = _load_committed()
    classes = set()
    for entry in list(data["registered"].values()) + list(data["l3"].values()):
        classes.update(entry)
    assert classes <= {"error", "warning", "info", NO_FINDING_MARKER}
