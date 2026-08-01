"""Parser-extension tests for the X-Ray model graph (Task 1)."""

from __future__ import annotations

import pytest

from seshat.tmdl import parse_relationships, parse_tmdl

pytestmark = pytest.mark.unit

REL = """relationship f4c82114
\tfromColumn: 'gold fct_sales'.customer_sk
\ttoColumn: 'gold dim_customer'.customer_sk

relationship inactive-one
\tisActive: false
\tfromColumn: Sales.date_alt
\ttoColumn: 'gold dim_date'.'date key'

relationship m2m
\tfromCardinality: many
\ttoCardinality: many
\tfromColumn: A.k
\ttoColumn: B.k
"""


def test_relationship_endpoints_parsed():
    rels = parse_relationships(REL)
    assert rels[0].from_table == "gold fct_sales"
    assert rels[0].from_column == "customer_sk"
    assert rels[0].to_table == "gold dim_customer"
    assert rels[0].to_column == "customer_sk"
    assert rels[0].is_active is True


def test_relationship_quoted_column_and_inactive():
    rels = parse_relationships(REL)
    assert rels[1].is_active is False
    assert rels[1].from_table == "Sales"
    assert rels[1].to_column == "date key"


def test_relationship_cardinality():
    rels = parse_relationships(REL)
    assert rels[2].from_cardinality == "many"
    assert rels[2].to_cardinality == "many"


TABLE = """table Sales
\tmeasure Revenue = SUM(Sales[amount])
\t\tformatString: #,0.00
\t\tdescription: Gross revenue before returns

\tcolumn month_name
\t\tdataType: string
\t\tsortByColumn: month_no
\t\tisHidden

\tcolumn month_no
\t\tdataType: int64
"""


def test_measure_format_and_description():
    table = parse_tmdl(TABLE)
    assert table is not None
    m = table.measures[0]
    assert m.format_string == "#,0.00"
    assert m.description == "Gross revenue before returns"


def test_column_sortby_and_hidden():
    table = parse_tmdl(TABLE)
    assert table is not None
    col = {c.name: c for c in table.columns}
    assert col["month_name"].sort_by_column == "month_no"
    assert col["month_name"].is_hidden is True
    assert col["month_no"].is_hidden is False
