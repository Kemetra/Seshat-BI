"""PBIR binding-walk tests (Task 3)."""

from __future__ import annotations

import pytest

from seshat.xray.bindings import read_bindings

pytestmark = pytest.mark.unit

VISUAL = """
{"visual": {"query": {"queryState": {"Values": {"projections": [
  {"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Sales"}},
             "Property": "amount"}}, "queryRef": "Sales.amount"},
  {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}},
             "Property": "Revenue"}}, "queryRef": "Sales.Revenue"}
]}}}}}
"""


def test_column_and_measure_bindings_collected():
    b = read_bindings(
        [("r/X.Report/definition/pages/p1/visuals/v1/visual.json", VISUAL)]
    )
    assert b.report_scanned is True
    assert ("Sales", "amount") in b.bound_columns
    assert "Revenue" in b.bound_measures


def test_no_report_files_means_not_scanned():
    b = read_bindings([])
    assert b.report_scanned is False
    assert not b.bound_columns and not b.bound_measures


def test_malformed_json_is_skipped_not_fatal():
    b = read_bindings(
        [
            ("r/X.Report/definition/report.json", "{not json"),
            ("r/X.Report/definition/pages/p1/visuals/v1/visual.json", VISUAL),
        ]
    )
    assert b.report_scanned is True
    assert "Revenue" in b.bound_measures


def test_all_malformed_means_not_scanned():
    b = read_bindings([("r/X.Report/definition/report.json", "{not json")])
    assert b.report_scanned is False


def test_hierarchy_level_is_recorded_as_a_triple_not_a_column():
    """A level name is not a column name, so the triple is recorded RAW.

    The audit resolves it against the model's parsed hierarchy membership;
    recording ``(entity, level)`` in ``bound_columns`` here used to leave the
    real backing column falsely reported as unused.
    """
    doc = """
    {"field": {"HierarchyLevel": {"Expression": {"Hierarchy": {"Expression":
      {"SourceRef": {"Entity": "Dates"}}, "Hierarchy": "Calendar"}},
      "Level": "Month"}}}
    """
    b = read_bindings([("r/X.Report/definition/pages/p/visuals/v/visual.json", doc)])
    assert ("Dates", "Calendar", "Month") in b.bound_hierarchy_levels
    assert ("Dates", "Month") not in b.bound_columns
