"""Spec 149 / #660 -- the vendor's (tool, operation) vocabulary.

Tool names are the 21 probed from the live server on 2026-08-20. A name absent
from that set is refused rather than forwarded: npx will happily start a server
that does not implement what we ask, and a typo must fail closed.
"""

from __future__ import annotations

import pytest

from seshat.pbi_mcp_adapter import vendor_ops

pytestmark = pytest.mark.unit


def test_the_probed_tool_set_is_closed_and_complete():
    assert len(vendor_ops.VENDOR_TOOLS) == 21
    assert "measure_operations" in vendor_ops.VENDOR_TOOLS
    assert "connection_operations" in vendor_ops.VENDOR_TOOLS
    assert "database_operations" in vendor_ops.VENDOR_TOOLS
    # The invented names the old stub used must NOT be present.
    assert "update_measure" not in vendor_ops.VENDOR_TOOLS
    assert "list_measures" not in vendor_ops.VENDOR_TOOLS
    assert "list_tables" not in vendor_ops.VENDOR_TOOLS


def test_parse_operation_id_splits_a_dotted_pair():
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


def test_is_write_classifies_the_mutating_operations():
    assert vendor_ops.is_write("Create") is True
    assert vendor_ops.is_write("Update") is True
    assert vendor_ops.is_write("Delete") is True
    assert vendor_ops.is_write("List") is False
    assert vendor_ops.is_write("Help") is False
    assert vendor_ops.is_write("Get") is False


def test_an_unrecognised_operation_is_treated_as_a_write():
    """Fail closed: an unknown verb must never be assumed read-only."""
    assert vendor_ops.is_write("SomethingNew") is True


def test_the_flush_verb_is_a_write_for_gate_purposes():
    """It rewrote 11 files, whatever the vendor's readOnlyHint says."""
    assert vendor_ops.is_write("ExportToTmdlFolder") is True
    assert "ExportToTmdlFolder" in vendor_ops.WRITE_OPERATIONS


def test_read_and_write_sets_do_not_overlap():
    """An operation classified both ways would make is_write order-dependent."""
    assert vendor_ops.READ_OPERATIONS & vendor_ops.WRITE_OPERATIONS == frozenset()


def test_the_vocabulary_covers_the_real_operation_names():
    """Regression: a hand-curated subset rejected legitimate vendor operations.

    These names come from the probed tool descriptions (2026-08-20). Before the
    derivation, parse_operation_id refused every one of them, so an approval for
    a perfectly normal measure add would have been unusable.
    """
    known = vendor_ops.READ_OPERATIONS | vendor_ops.WRITE_OPERATIONS
    for name in (
        "AddMeasures",
        "RemoveMeasures",
        "CreateItems",
        "UpdateTables",
        "ListColumns",
        "GetSchema",
        "MarkAsDateTable",
        "ReorderLevels",
    ):
        assert name in known, f"{name} is a real vendor operation but unclassified"


def test_the_vocabulary_is_large_enough_to_be_derived_not_guessed():
    """A tiny set is the signature of hand-curation; the real surface is ~100."""
    total = len(vendor_ops.READ_OPERATIONS | vendor_ops.WRITE_OPERATIONS)
    assert total >= 100, f"only {total} verbs classified -- did the derivation regress?"
