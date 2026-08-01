"""Regression pins for the three PR #551 review findings.

All three were regressions introduced BY this PR's own fixes, so each pin
guards a fix against its own follow-on defect.
"""

from __future__ import annotations

import pytest

from seshat.tmdl import parse_tmdl
from seshat.xray.audit import run_audit
from seshat.xray.bindings import read_bindings
from seshat.xray.diff import diff_models
from seshat.xray.graph import build_graph

pytestmark = pytest.mark.unit

_M = "m/X.SemanticModel/definition"
NO_REPORT = read_bindings([])
_T = f"{_M}/tables/T.tmdl"


# --- comment-only edits must stay non-semantic ------------------------------


def test_quoted_text_inside_a_line_comment_is_not_semantic():
    base = 'table T\n\tmeasure M = SUM(T[a]) // "old"\n\tcolumn a\n'
    head = 'table T\n\tmeasure M = SUM(T[a]) // "new"\n\tcolumn a\n'
    assert not [
        c for c in diff_models([(_T, base)], [(_T, head)]) if c.bucket == "semantic"
    ]


def test_quoted_text_inside_a_block_comment_is_not_semantic():
    base = 'table T\n\tmeasure M = SUM(T[a]) /* "old" */\n\tcolumn a\n'
    head = 'table T\n\tmeasure M = SUM(T[a]) /* "new" */\n\tcolumn a\n'
    assert not [
        c for c in diff_models([(_T, base)], [(_T, head)]) if c.bucket == "semantic"
    ]


def test_a_real_literal_change_is_still_semantic():
    base = 'table T\n\tmeasure M = "OK" // note\n'
    head = 'table T\n\tmeasure M = "ok" // note\n'
    assert [
        c for c in diff_models([(_T, base)], [(_T, head)]) if c.bucket == "semantic"
    ]


def test_comment_marker_inside_a_literal_is_not_a_comment():
    """``"a // b"`` is a literal containing slashes, not code plus a comment."""
    base = 'table T\n\tmeasure M = "a // b"\n'
    head = 'table T\n\tmeasure M = "a // c"\n'
    assert [
        c for c in diff_models([(_T, base)], [(_T, head)]) if c.bucket == "semantic"
    ]


# --- multiline calculated columns ------------------------------------------

MULTILINE_CALC = (
    "table T\n\tcolumn Margin =\n\t\t[Price] - [Cost]\n\t\tdataType: double\n"
)


def test_multiline_calculated_column_expression_is_captured():
    table = parse_tmdl(MULTILINE_CALC)
    assert table is not None
    assert "[Price]" in (table.columns[0].expression or "")
    assert table.columns[0].data_type == "double", "properties still parse"


def test_multiline_calculated_column_logic_change_is_semantic():
    head = MULTILINE_CALC.replace("[Price] - [Cost]", "[Price] - [Cost] - [Tax]")
    changes = diff_models([(_T, MULTILINE_CALC)], [(_T, head)])
    assert any(c.bucket == "semantic" and c.subject == "T[Margin]" for c in changes)


def test_multiline_calculated_column_inputs_are_not_falsely_unused():
    text = (
        "table T\n\tcolumn Margin =\n\t\t[Price] - [Cost]\n"
        "\tcolumn Price\n\t\tdataType: double\n"
        "\tcolumn Cost\n\t\tdataType: double\n"
    )
    graph = build_graph([(_T, text)])
    unused = {f.locator for f in run_audit(graph, NO_REPORT) if f.finding_id == "X1"}
    assert "T[Price]" not in unused and "T[Cost]" not in unused


# --- calculated columns are not measures ----------------------------------


def _long_chain_with_calc_column() -> str:
    chain = "".join(f"\tmeasure M{i} = [M{i + 1}] + 1\n" for i in range(5))
    return "table T\n" + chain + "\tmeasure M5 = 1\n\tcolumn C = [M0] + 1\n"


def test_calc_column_never_yields_a_measure_depth_finding():
    graph = build_graph([(_T, _long_chain_with_calc_column())])
    x3 = [f for f in run_audit(graph, NO_REPORT) if f.finding_id == "X3"]
    assert not [f for f in x3 if f.locator.startswith("?[")], (
        "a calculated column must not be analyzed as a measure"
    )
    assert [f for f in x3 if f.locator == "T[M0]"], "the real chain still reports"


def test_calc_column_edges_still_count_as_inbound_references():
    """The edge must be RETAINED for reference accounting -- only the
    depth/cycle FINDING is measure-only."""
    text = "table T\n\tmeasure Solo = 1\n\tcolumn C = [Solo] + 1\n"
    graph = build_graph([(_T, text)])
    assert "Solo" in graph.measure_refs["T[C]"]
    orphans = {f.locator for f in run_audit(graph, NO_REPORT) if f.finding_id == "X1"}
    assert "T[Solo]" not in orphans, "referenced by a calc column, so not orphaned"
