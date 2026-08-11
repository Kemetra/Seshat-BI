"""`forbidden_scope` must come from the readiness state, not a handcrafted journey.

The Studio projection is the ONLY production construction site of `TableJourney`,
and it left `forbidden_scope` at its `()` default. Every other surface -- the CLI,
the governor, the shared readiness projection -- derives the list from
`agent_next`, so Studio was the one consumer that promised a forbidden-scope
section and then shipped an empty one. A table blocked at Mapping never told the
agent that authoring `silver.*` is prohibited.

The oracle here is deliberately NOT the code under test. `agent_next
.build_table_next_document` is the same function `readiness_projection` already
trusts for this field, so these tests compare Studio's output against the
established authority rather than against a fixture that was written to match it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit._studio_workspace_fixtures import (  # noqa: E402
    write_blocked_table,
    write_ready_table,
)


def _authority_scope(root: Path, directory_name: str) -> list[str]:
    """What the established readiness authority says is forbidden for this table."""
    from seshat.agent_next import build_table_next_document

    return list(build_table_next_document(root, directory_name)["forbidden_scope"])


def test_a_table_blocked_at_mapping_forbids_silver_authoring(tmp_path: Path) -> None:
    """The exact case that shipped empty: blocked at Mapping must name the gate."""
    from seshat.studio import projection

    write_blocked_table(tmp_path)
    journey = projection.build_workspace_snapshot(tmp_path).tables[0]

    assert journey.forbidden_scope, (
        "a table blocked at Mapping Ready projected an EMPTY forbidden_scope; the "
        "agent is never told that authoring silver.* is prohibited"
    )
    assert any("silver" in sentence.lower() for sentence in journey.forbidden_scope), (
        "the no-silver-before-Mapping gate is missing from the projected scope: "
        f"{journey.forbidden_scope}"
    )


def test_the_projected_scope_matches_the_readiness_authority(tmp_path: Path) -> None:
    """Studio must not derive its own gate list -- a second one would drift."""
    from seshat.studio import projection

    source_path = write_blocked_table(tmp_path)
    directory_name = source_path.parent.name
    journey = projection.build_workspace_snapshot(tmp_path).tables[0]

    assert list(journey.forbidden_scope) == _authority_scope(tmp_path, directory_name)


def test_a_ready_table_still_carries_the_always_forbidden_invariants(
    tmp_path: Path,
) -> None:
    """Advancing does not empty the list: the invariants hold at every stage.

    Pins the non-empty case too, so a fix that hardcoded the mapping sentence and
    returned `()` everywhere else would fail here rather than pass both tests.
    """
    from seshat.studio import projection

    source_path = write_ready_table(tmp_path)
    directory_name = source_path.parent.name
    journey = projection.build_workspace_snapshot(tmp_path).tables[0]

    assert list(journey.forbidden_scope) == _authority_scope(tmp_path, directory_name)
