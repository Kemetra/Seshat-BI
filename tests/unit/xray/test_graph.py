"""ModelGraph construction tests (Task 2)."""

from __future__ import annotations

import pytest

from seshat.xray.graph import build_graph

pytestmark = pytest.mark.unit

SALES = """table Sales
\tmeasure Revenue = SUM(Sales[amount])
\tmeasure Margin = [Revenue] - SUM(Sales[cost])
\tmeasure Junk = [Revenue] / 'Dim Product'[list_price] // uses [NotAThing]
\tcolumn amount
\t\tdataType: double
\tcolumn cost
\t\tdataType: double
"""

PRODUCT = """table 'Dim Product'
\tcolumn list_price
\t\tdataType: double
"""

RELS = """relationship r1
\tfromColumn: Sales.product_sk
\ttoColumn: 'Dim Product'.product_sk
"""

ROLE = "role Readers\n\tfilter Sales = Sales[amount] > 0\n"

FILES = [
    ("m/X.SemanticModel/definition/tables/Sales.tmdl", SALES),
    ("m/X.SemanticModel/definition/tables/Dim Product.tmdl", PRODUCT),
    ("m/X.SemanticModel/definition/relationships.tmdl", RELS),
    ("m/X.SemanticModel/definition/roles/Readers.tmdl", ROLE),
]


def test_measure_to_measure_edge():
    g = build_graph(FILES)
    assert "Revenue" in g.measure_refs["Margin"]


def test_measure_to_column_edges_same_and_other_table():
    g = build_graph(FILES)
    assert ("Sales", "amount") in g.column_refs["Revenue"]
    assert ("Dim Product", "list_price") in g.column_refs["Junk"]


def test_comment_tokens_are_not_references():
    g = build_graph(FILES)
    # [NotAThing] sits in a // comment -- must not appear anywhere
    assert "NotAThing" not in g.unresolved.get("Junk", frozenset())
    assert "NotAThing" not in g.measure_refs.get("Junk", frozenset())


def test_bare_token_resolves_measure_first_then_same_table_column():
    g = build_graph(FILES)
    # [Revenue] is a measure; Sales[cost] inside Margin resolves to the column
    assert "Revenue" in g.measure_refs["Margin"]
    assert ("Sales", "cost") in g.column_refs["Margin"]


def test_unresolved_token_recorded_not_dropped():
    files = FILES + [
        (
            "m/X.SemanticModel/definition/tables/T.tmdl",
            "table T\n\tmeasure Bad = [Ghost] + 1\n",
        )
    ]
    g = build_graph(files)
    assert "Ghost" in g.unresolved["Bad"]


def test_role_text_scan_counts_as_column_reference():
    g = build_graph(FILES)
    assert ("Sales", "amount") in g.text_referenced_columns


def test_unparseable_table_file_becomes_notice():
    files = FILES + [("m/X.SemanticModel/definition/tables/broken.tmdl", "@@@ nope")]
    g = build_graph(files)
    assert "m/X.SemanticModel/definition/tables/broken.tmdl" in g.parse_notices
