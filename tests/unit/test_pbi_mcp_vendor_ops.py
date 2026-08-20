"""Spec 149 / #660 -- the vendor's PER-TOOL (tool, operation) vocabulary.

Every pair asserted here comes from a `tools/list` description returned by the
real server on 2026-08-20 (@microsoft/powerbi-modeling-mcp@0.5.0-beta.12). A pair
absent from that evidence is refused rather than forwarded: npx will happily start
a server that does not implement what we ask, and a typo must fail closed.
"""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import vendor_ops

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# The shape of the evidence
# --------------------------------------------------------------------------


def test_all_twenty_one_tools_are_named():
    assert len(vendor_ops.VENDOR_TOOLS) == 21
    for name in ("measure_operations", "connection_operations", "database_operations"):
        assert name in vendor_ops.VENDOR_TOOLS
    # The invented names the old stub used must NOT be present.
    for invented in ("update_measure", "list_measures", "list_tables"):
        assert invented not in vendor_ops.VENDOR_TOOLS


def test_the_operation_map_is_per_tool_not_a_flat_set():
    """H4: a flat set + independent validation authorizes the cross-product."""
    assert isinstance(vendor_ops.TOOL_OPERATIONS, dict)
    assert len(vendor_ops.TOOL_OPERATIONS) == 20
    assert set(vendor_ops.TOOL_OPERATIONS) <= vendor_ops.VENDOR_TOOLS


def test_a_tool_with_no_evidenced_list_authorizes_nothing():
    """An absent entry must never read as 'anything goes'.

    `partition_operations` publishes no `Supported operations:` sentence, so no
    pair naming it can be derived -- and it must therefore be refused, not waved
    through.
    """
    assert "partition_operations" in vendor_ops.VENDOR_TOOLS
    assert "partition_operations" not in vendor_ops.TOOL_OPERATIONS
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("partition_operations.Create")


# --------------------------------------------------------------------------
# parse_operation_id -- the pair, validated together
# --------------------------------------------------------------------------


def test_parse_operation_id_splits_an_evidenced_pair():
    assert vendor_ops.parse_operation_id("measure_operations.Update") == (
        "measure_operations",
        "Update",
    )


def test_parse_operation_id_refuses_an_unknown_tool():
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("update_measure.Update")


def test_parse_operation_id_refuses_an_unpaired_id():
    """The pre-#660 single-token form must not silently become a tool name."""
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("update_measure")


def test_parse_operation_id_refuses_a_trailing_dot():
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("measure_operations.")


def test_parse_operation_id_refuses_an_unknown_operation():
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("measure_operations.Obliterate")


def test_a_verb_is_refused_for_a_tool_that_does_not_have_it():
    """THE H4 test: validating the halves independently is a fail-open.

    `Update` is real, and `dax_query_operations` is real, but the server never
    showed `Update` under that tool. Accepting the pair would authorize the whole
    cross-product.
    """
    assert "Update" in vendor_ops.TOOL_OPERATIONS["measure_operations"].all_verbs
    assert "dax_query_operations" in vendor_ops.TOOL_OPERATIONS
    with pytest.raises(vendor_ops.UnknownVendorOperation):
        vendor_ops.parse_operation_id("dax_query_operations.Update")


# --------------------------------------------------------------------------
# is_write -- per tool, failing closed
# --------------------------------------------------------------------------


def test_is_write_classifies_a_tools_own_verbs():
    tool = "measure_operations"
    for write in ("Create", "Update", "Delete", "Rename", "Move"):
        assert vendor_ops.is_write(write, tool) is True, write
    for read in ("Get", "List", "Help", "ExportTMDL"):
        assert vendor_ops.is_write(read, tool) is False, read


def test_an_unrecognised_operation_is_treated_as_a_write():
    """Fail closed: an unknown verb must never be assumed read-only."""
    assert vendor_ops.is_write("SomethingNew", "measure_operations") is True


def test_a_verb_read_under_one_tool_is_not_assumed_read_under_another():
    """The classification is per tool, so absence from THIS tool's reads wins."""
    assert vendor_ops.is_write("ExportTMDL", "measure_operations") is False
    assert vendor_ops.is_write("ExportTMDL", "transaction_operations") is True


def test_an_unmapped_tool_makes_every_verb_a_write():
    assert vendor_ops.is_write("List", "partition_operations") is True


def test_the_flush_verb_is_a_write_for_gate_purposes():
    """It rewrote 11 files, whatever the vendor's readOnlyHint says."""
    assert vendor_ops.is_write("ExportToTmdlFolder", "database_operations") is True


# --------------------------------------------------------------------------
# requires_payload -- the C2 refusal condition, server-stated
# --------------------------------------------------------------------------


def test_create_and_update_require_a_definitions_payload():
    """The server's own words: 'For Create and Update use Definitions'."""
    for tool in ("measure_operations", "column_operations", "table_operations"):
        assert vendor_ops.requires_payload(tool, "Create") is True, tool
        assert vendor_ops.requires_payload(tool, "Update") is True, tool


def test_a_read_never_requires_a_payload():
    for verb in ("List", "Get", "Help", "ExportTMDL"):
        assert vendor_ops.requires_payload("measure_operations", verb) is False


def test_a_payload_free_write_is_not_refused():
    """Rename uses RenameDefinitions, so it is a write we CAN honestly execute."""
    assert vendor_ops.is_write("Rename", "measure_operations") is True
    assert vendor_ops.requires_payload("measure_operations", "Rename") is False


def test_requires_payload_is_false_for_an_unmapped_tool():
    """No evidence of a payload requirement; the pair is refused earlier anyway."""
    assert vendor_ops.requires_payload("partition_operations", "Create") is False


# --------------------------------------------------------------------------
# Provenance -- the read sets are the safety-critical half
# --------------------------------------------------------------------------


def test_every_read_is_drawn_from_its_own_tools_verb_list():
    """A read must be one of that tool's evidenced operations, not a free verb."""
    for tool, verbs in vendor_ops.TOOL_OPERATIONS.items():
        assert verbs.reads <= verbs.all_verbs, tool
        assert verbs.needs_payload <= verbs.all_verbs, tool


def test_no_export_to_folder_verb_is_ever_classified_as_a_read():
    """The family that rewrote 11 files while self-reporting readOnlyHint: true."""
    for tool, verbs in vendor_ops.TOOL_OPERATIONS.items():
        for verb in verbs.reads:
            assert not verb.startswith("ExportTo"), f"{tool}.{verb}"


def test_the_evidence_is_broad_enough_to_be_derived_not_guessed():
    """A tiny map is the signature of hand-curation; the real surface is ~220."""
    pairs = sum(len(v.all_verbs) for v in vendor_ops.TOOL_OPERATIONS.values())
    assert pairs >= 200, f"only {pairs} pairs -- did the derivation regress?"


def test_the_real_operation_names_are_present_under_their_own_tools():
    """Regression: a hand-curated global subset rejected legitimate operations."""
    for tool, verb in (
        ("measure_operations", "Delete"),
        ("table_operations", "MarkAsDateTable"),
        ("table_operations", "GetSchema"),
        ("connection_operations", "ConnectFolder"),
        ("database_operations", "ExportToTmdlFolder"),
        ("trace_operations", "Start"),
    ):
        assert verb in vendor_ops.TOOL_OPERATIONS[tool].all_verbs, f"{tool}.{verb}"
