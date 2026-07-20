"""scaffold-source self-consistency (issues #374, #380).

* #374 -- the `next_action` scaffold-source writes tripped `seshat next`'s own
  `next_action_disagreement` caveat (the exact caveat a code comment says it is
  avoiding), and the computed source_ready action wrongly said "No readiness file
  found" when a file was present.
* #380 -- scaffold-source materialized only 3 of the 5 sister artifacts its own
  source-map.yaml declares a reviewer reads as a set; assumptions.md and
  reconciliation-report.md were never emitted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# #374 -- scaffolded next_action agrees with seshat next (no self-contradiction)
# ---------------------------------------------------------------------------


def test_scaffolded_next_action_does_not_trip_disagreement(tmp_path: Path) -> None:
    # scaffold, then compute the run-next answer: the stored next_action must MATCH
    # the computed source_ready action, so no next_action_disagreement caveat fires.
    from seshat.run_next import build_run_next_response
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "sales_raw")
    result = build_run_next_response(tmp_path, "sales_raw")

    kinds = {c.get("kind") for c in result.get("caveats", [])}
    assert "next_action_disagreement" not in kinds, result.get("caveats")


def test_source_ready_action_for_existing_file_is_not_no_file_wording(
    tmp_path: Path,
) -> None:
    # When a readiness file EXISTS at source_ready, the computed action must not
    # claim "No readiness file found" -- that wording belongs only to the genuine
    # no-file case.
    from seshat.run_next import build_run_next_response
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "sales_raw")
    result = build_run_next_response(tmp_path, "sales_raw")

    assert result["stage"] == "source_ready"
    assert "no readiness file found" not in (result["action_text"] or "").lower()
    assert "Source Ready" in (result["action_text"] or "")


def test_missing_file_still_says_no_readiness_file(tmp_path: Path) -> None:
    # The genuine no-file case keeps its accurate message (the split preserves it).
    from seshat.run_next import build_run_next_response

    result = build_run_next_response(tmp_path, "never_scaffolded")
    assert result["stage"] == "source_ready"
    assert "no readiness file found" in (result["action_text"] or "").lower()


# ---------------------------------------------------------------------------
# #380 -- scaffold-source emits all five declared sister artifacts
# ---------------------------------------------------------------------------


def test_scaffold_emits_assumptions_and_reconciliation(tmp_path: Path) -> None:
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "sales_raw")
    mapping = tmp_path / "mappings" / "sales_raw"
    assert (mapping / "assumptions.md").is_file()
    assert (mapping / "reconciliation-report.md").is_file()
    # The original three are still emitted.
    assert (mapping / "source-profile.md").is_file()
    assert (mapping / "readiness-status.yaml").is_file()
    assert (mapping / "source-map.yaml").is_file()
