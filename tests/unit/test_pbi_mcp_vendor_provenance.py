"""Spec 149 / #660 -- the vocabulary is DERIVABLE from a committed capture.

Round 3 of review found two defects this module exists to make impossible:

1. **A CRITICAL coverage gap.** ``requires_payload`` was derived with a regex
   matching one phrasing of the server's requirement. Three tools state it
   differently, so eight (tool, verb) pairs that need a ``Definitions`` payload
   were NOT refused -- and a hollow no-op executed reporting success.
2. **Unverifiable provenance.** The module claimed "220 evidenced pairs" from a
   dated capture that was never committed, so no reader could re-derive or
   falsify it.

The fix for both is the same: commit the capture, and RE-DERIVE the map from it
here. A shipped map that disagrees with the fixture fails. A fourth phrasing the
derivation misses fails the COVERAGE test, which keys on the presence of the word
``Definitions`` rather than on any sentence shape.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import vendor_ops

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "pbi_mcp"
    / "vendor_tools_0.5.0-beta.12.json"
)

#: Prefixes that mark a non-mutating verb. ``ExportTo*`` is excluded: the server
#: annotates ``ExportToTmdlFolder`` as ``readOnlyHint: true`` and it rewrote all
#: 11 TMDL files (research.md R8).
READ_PREFIXES = (
    "Get",
    "List",
    "Find",
    "Help",
    "Validate",
    "Export",
    "CheckStatus",
    "Fetch",
)


def _capture() -> dict[str, dict[str, str]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _is_read(verb: str) -> bool:
    return verb.startswith(READ_PREFIXES) and not verb.startswith("ExportTo")


def _declared_verbs(description: str) -> list[str]:
    """The tool's own operation list, from EITHER phrasing the server uses.

    Matching only ``Supported operations:`` silently dropped 7 of 21 tools.
    """
    match = re.search(r"Supported operations:\s*(.+?)\.\s", description) or re.search(
        r"Use the Operation parameter to specify:\s*(.+?)\.\s", description
    )
    if match is None:
        return []
    verbs = []
    for raw in match.group(1).split(","):
        verb = re.sub(r"\s*\(.*?\)", "", raw).strip()
        if verb and re.fullmatch(r"[A-Za-z]+", verb):
            verbs.append(verb)
    return verbs


def test_the_capture_is_committed_and_complete():
    """Provenance must be checkable, not asserted."""
    assert FIXTURE.is_file(), f"the vendor capture is missing: {FIXTURE}"
    assert len(_capture()) == 21


def test_every_tool_in_the_capture_declares_its_operations():
    """No tool may be dropped by a phrasing accident -- that shipped once."""
    undeclared = [
        name
        for name, rec in _capture().items()
        if not _declared_verbs(rec["description"])
    ]
    assert undeclared == [], f"no operation list derivable for: {undeclared}"


def test_the_shipped_map_matches_a_fresh_derivation():
    """The map is DERIVED, so a hand-edit that drifts from the server fails."""
    for name, rec in _capture().items():
        declared = set(_declared_verbs(rec["description"]))
        shipped = vendor_ops.TOOL_OPERATIONS.get(name)
        assert shipped is not None, f"{name} is missing from TOOL_OPERATIONS"
        assert shipped.all_verbs == declared, (
            f"{name}: shipped {sorted(shipped.all_verbs)} != "
            f"declared {sorted(declared)}"
        )


def test_the_shipped_read_split_matches_the_prefix_rule():
    for name, rec in _capture().items():
        declared = _declared_verbs(rec["description"])
        expected = {verb for verb in declared if _is_read(verb)}
        assert vendor_ops.TOOL_OPERATIONS[name].reads == expected, name


# --------------------------------------------------------------------------
# THE coverage test -- what round 3's CRITICAL needed and nothing had
# --------------------------------------------------------------------------


def test_every_tool_mentioning_Definitions_declares_needs_payload():
    """Coverage, not instance: keyed on the WORD, not on a sentence shape.

    The round-3 defect was a derivation matching only "For Create and Update use
    Definitions". Three tools say it as "Use Definitions for ..." or
    "..., provide Definitions", so their Create/Update executed hollow.

    This asserts the invariant instead of the instance: if a tool's description
    mentions ``Definitions`` as an INPUT it must supply, then that tool must
    declare a non-empty ``needs_payload``. A fourth phrasing therefore fails here
    rather than shipping a silent fail-open.
    """
    offenders = []
    for name, rec in _capture().items():
        description = rec["description"]
        # `RenameDefinitions` / `MoveDefinitions` are different parameters, and
        # `TmdlSerializationOptions` style names must not match either.
        mentions = re.search(
            r"(?<!Rename)(?<!Move)(?<!Tmdl)\bDefinitions\b", description
        )
        if not mentions:
            continue
        shipped = vendor_ops.TOOL_OPERATIONS.get(name)
        if shipped is None or not shipped.needs_payload:
            offenders.append(name)
    assert offenders == [], (
        "these tools require a Definitions payload but declare none, so a write "
        f"would execute as a hollow no-op: {offenders}"
    )


def test_the_three_tools_missed_in_round_two_are_now_covered():
    """The specific regression, named so it cannot quietly come back."""
    for tool, verb in (
        ("function_operations", "Update"),
        ("function_operations", "Create"),
        ("named_expression_operations", "Update"),
        ("named_expression_operations", "UpdateParameter"),
        ("query_group_operations", "Create"),
        ("query_group_operations", "Update"),
    ):
        assert vendor_ops.requires_payload(tool, verb) is True, f"{tool}.{verb}"


def test_no_read_operation_is_ever_marked_as_needing_a_payload():
    """A read needing a Definitions block would mean the derivation misfired."""
    for name, verbs in vendor_ops.TOOL_OPERATIONS.items():
        overlap = verbs.needs_payload & verbs.reads
        assert overlap == frozenset(), f"{name}: {sorted(overlap)}"


def test_needs_payload_only_names_verbs_the_tool_actually_has():
    for name, verbs in vendor_ops.TOOL_OPERATIONS.items():
        assert verbs.needs_payload <= verbs.all_verbs, name
