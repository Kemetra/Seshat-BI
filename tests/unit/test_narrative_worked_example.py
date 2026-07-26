"""The NON-SYNTHETIC proof of the Stage-6 narrative gate (issue #514).

Every other narrative test builds its own fixture and checks the schema against
it. That is necessary but circular-adjacent: a fixture the test authored will
naturally have the shape the code expects. These two tests are the anchor against
that -- they run BOTH checker modes over the ONE real committed worked example
(`mappings/retail_store_sales/`), whose brief, binding map, metric contracts and
source profile were all authored for their own sake, not for a test.

THE DELIBERATE FLIP. This file's map test SUPERSEDES
``test_real_worked_example_map_still_needs_phase_b_migration`` (formerly in
``test_narrative_check.py``), which asserted the fail-closed state while the real
map was still the F011 two-way pipe table with no
``seshat.binding-map/v1`` front section. Its own comment said: "when the map is
migrated, this test flips and must be updated deliberately." The map IS now
migrated, so this is that deliberate update -- and it is a SEPARATE FILE because
asserting against a real committed artifact is a different concern from the
fixture-built unit checks next door.

Assertions here are deliberately STRONGER than a bare ``status == "pass"``, which
would still hold if someone gutted the artifact to zero visuals to make it green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.narrative_check import check_binding_map, check_narrative

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TABLE = "retail_store_sales"
_REAL_MAP = (
    _REPO_ROOT / "mappings" / _TABLE / "design" / "visual-contract-binding-map.md"
)
_REAL_BRIEF = _REPO_ROOT / "mappings" / _TABLE / "narrative-brief.md"

# A map+brief this small would be a hollowed-out artifact, not a worked example.
_MIN_SUBSTANTIVE_COUNT = 5


def test_real_worked_example_map_is_migrated_and_blocked_only_on_v10():
    """The map IS migrated to `seshat.binding-map/v1` -- so the OLD fail-closed
    reason (`no_front_section`) is gone -- and the three-way gate now resolves 9
    of its 10 visuals cleanly.

    It reports `blocked` on EXACTLY ONE remaining defect: v10 (the customer
    visual) names no decision-question, because no customer question may exist
    while `source-profile.md` records the `customer_id` PII question as open. That
    is an HONEST block on a real defect, not a curated pass: declaring only the 9
    bindable visuals would have produced `status: pass` over an artifact that
    really carries 10 (raised in review of PR #519).

    This test therefore pins BOTH halves -- the migration happened, AND the one
    open item is exactly the owner decision W3/D4, no more and no less. It flips
    to a clean pass when the owner rules.
    """
    assert _REAL_MAP.is_file(), f"expected the real worked-example map at {_REAL_MAP}"

    result = check_binding_map(table=_TABLE, repo_root=_REPO_ROOT)

    # The migration really happened: the pre-migration reason is gone.
    dimensions = {f.dimension for f in result.findings}
    assert "no_front_section" not in dimensions, (
        "the map should be migrated to seshat.binding-map/v1 by now"
    )

    # Exactly one finding, and it is the v10 orphan -- nothing else regressed.
    assert result.status == "blocked"
    assert len(result.findings) == 1, [f._asdict() for f in result.findings]
    only = result.findings[0]
    assert only.dimension == "orphan_visual"
    assert only.locator == "v10"

    # The check ran over real content -- all ten visuals, not a curated subset.
    evidence = " ".join(result.evidence)
    counts = [int(n) for n in re.findall(r"(\d+) (?:visual|declared brief)", evidence)]
    assert counts, f"expected resolved counts in the evidence, got {evidence!r}"
    assert min(counts) >= _MIN_SUBSTANTIVE_COUNT, (
        f"expected a substantive map+brief (>= {_MIN_SUBSTANTIVE_COUNT} visuals and "
        f"questions), got counts {counts} from evidence: {evidence!r}"
    )
    assert "10 visual(s)" in evidence, (
        f"all ten committed visuals must be checked, got: {evidence!r}"
    )

    # Read-only posture is unchanged by the migration (Principle VIII).
    assert result.grants_approval is False


def test_real_worked_example_brief_passes_and_grants_nothing():
    """The brief half of the same proof: the committed narrative-brief.md conforms
    to the frozen v1 schema over the REAL approved contracts -- so the
    stale-revision guard is exercised against real blob shas, not fixture ones --
    and still grants no approval."""
    assert _REAL_BRIEF.is_file(), f"expected the real brief at {_REAL_BRIEF}"

    result = check_narrative(table=_TABLE, repo_root=_REPO_ROOT)

    assert result.status == "pass", [f._asdict() for f in result.findings]
    assert result.grants_approval is False
