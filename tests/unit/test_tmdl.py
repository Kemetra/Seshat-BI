import json
from pathlib import Path

import pytest

from retail.tmdl import (
    normalize_measure_body,
    parse_relationships,
    parse_tmdl,
    top_level_blocks,
)

GOLDEN_PBIP_ROOT = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_pbip"
)
_MODEL = GOLDEN_PBIP_ROOT / "RetailGold.SemanticModel" / "definition" / "model.tmdl"
_RELS = (
    GOLDEN_PBIP_ROOT / "RetailGold.SemanticModel" / "definition" / "relationships.tmdl"
)
_PBIR = GOLDEN_PBIP_ROOT / "RetailGold.Report" / "definition.pbir"

# ---------------------------------------------------------------------------
# M0 regression anchors (golden fixture smoke tests — do NOT modify)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parser_reads_model_top_level_blocks() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    blocks = top_level_blocks(text)
    assert "table Sales" in blocks
    assert "table Date" in blocks


@pytest.mark.unit
def test_model_pins_measure_and_displayfolder_and_no_slash() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    assert "measure 'TotalSales' = SUM(Sales[Amount])" in text
    assert "displayFolder: Sales" in text
    assert "summarizeBy: sum" in text  # D5 warning anchor
    # D4 anchor: the measure body uses SUM, not a "/" division operator.
    assert "/" not in "measure 'TotalSales' = SUM(Sales[Amount])"


@pytest.mark.unit
def test_model_pins_gold_schema_and_parameterized_source() -> None:
    text = _MODEL.read_text(encoding="utf-8")
    assert 'Schema="gold"' in text  # D8 anchor
    assert "PostgreSQL.Database(Server, Database)" in text  # C1 anchor (identifiers)


@pytest.mark.unit
def test_model_pins_provisional_date_table_marker() -> None:
    # PROVISIONAL marker (spec §5.2 D7 / §13). Re-verify against the real PBIP from
    # Task M0.3 before M4 builds D7; if the real literal differs, update fixture +
    # assert.
    text = _MODEL.read_text(encoding="utf-8")
    assert "annotation PBI_DateTable = true" in text


@pytest.mark.unit
def test_relationships_pins_bothdirections() -> None:
    # Intentional D6 VIOLATION used as the crossFilteringBehavior anchor.
    text = _RELS.read_text(encoding="utf-8")
    assert "crossFilteringBehavior: bothDirections" in text


@pytest.mark.unit
def test_pbir_is_bom_tolerant_and_uses_relative_bypath() -> None:
    # Contract: PBIR opened encoding="utf-8-sig" (BOM-tolerant). R1 anchor: byPath
    # relative.
    data = json.loads(_PBIR.read_text(encoding="utf-8-sig"))
    path = data["datasetReference"]["byPath"]["path"]
    assert path == "../RetailGold.SemanticModel"
    assert not path[:1].isalpha() or path[1:2] != ":"  # not absolute "C:\..."


# ---------------------------------------------------------------------------
# M4 parser tests — structured parse
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.unit

SALES_TMDL = """table Sales
\tmeasure Revenue = SUM(Sales[Amount])
\t\tdisplayFolder: KPIs

\tmeasure Margin = DIVIDE([Revenue], [Cost])
\t\tdisplayFolder: KPIs

\tcolumn Amount
\t\tdataType: decimal
\t\tsummarizeBy: sum

\tcolumn ProductKey
\t\tdataType: int64
\t\tsummarizeBy: none
"""


def test_parse_tmdl_reads_table_name_and_measures() -> None:
    table = parse_tmdl(SALES_TMDL)
    assert table is not None
    assert table.name == "Sales"
    names = [m.name for m in table.measures]
    assert names == ["Revenue", "Margin"]
    revenue = table.measures[0]
    assert revenue.expression == "SUM(Sales[Amount])"
    assert revenue.display_folder == "KPIs"
    assert revenue.line == 2


def test_parse_tmdl_reads_columns() -> None:
    table = parse_tmdl(SALES_TMDL)
    assert table is not None
    amount = next(c for c in table.columns if c.name == "Amount")
    assert amount.data_type == "decimal"
    assert amount.summarize_by == "sum"
    pk = next(c for c in table.columns if c.name == "ProductKey")
    assert pk.summarize_by == "none"


REL_TMDL = """relationship Sales_Date
\tfromColumn: Sales.DateKey
\ttoColumn: Date.DateKey
\tcrossFilteringBehavior: bothDirections

relationship Sales_Product
\tfromColumn: Sales.ProductKey
\ttoColumn: Product.ProductKey
"""

PARTITION_TMDL = """table Sales
\tpartition Sales = m
\t\tsource =
\t\t\tlet
\t\t\t\tSrc = PostgreSQL.Database(Server, DB),
\t\t\t\tData = Value.NativeQuery(Src, "SELECT * FROM gold.fct_sales")
\t\t\tin
\t\t\t\tData
\tannotation PBI_DateTable = true
"""


def test_parse_relationships_captures_crossfilter() -> None:
    rels = parse_relationships(REL_TMDL)
    assert [r.name for r in rels] == ["Sales_Date", "Sales_Product"]
    assert rels[0].cross_filtering_behavior == "bothDirections"
    assert rels[1].cross_filtering_behavior is None


def test_parse_tmdl_captures_partition_source_and_annotation() -> None:
    table = parse_tmdl(PARTITION_TMDL)
    assert table is not None
    assert len(table.partition_sources) == 1
    assert "gold.fct_sales" in table.partition_sources[0]
    assert "annotation PBI_DateTable = true" in table.annotations


def test_normalize_measure_body_strips_comments_and_case() -> None:
    body = "SUM ( Sales[Amount] ) // total\n/* note */"
    # Spaces around punctuation are stripped so SUM( x ) and SUM(x) match.
    assert normalize_measure_body(body) == "sum(sales[amount])"


def test_parse_tmdl_returns_none_for_relationships_file() -> None:
    # A relationships file has no ``table`` block -> returns None.
    table = parse_tmdl(REL_TMDL)
    assert table is None


def test_parse_tmdl_golden_fixture_smoke() -> None:
    """Parse the M0 golden fixture — confirms the real-world format is handled."""
    text = _MODEL.read_text(encoding="utf-8-sig")
    table = parse_tmdl(text)
    assert table is not None
    assert table.name == "Sales"
    # The fixture has one measure: TotalSales (single-quoted name in TMDL)
    assert any(m.name == "TotalSales" for m in table.measures)
    # Should capture the partition source body
    assert len(table.partition_sources) >= 1


SOURCE_LIKE_PROPERTY_TMDL = """table Sales
\tsource.alias = legacy_value

\tpartition Sales = m
\t\tsource =
\t\t\tlet
\t\t\t\tData = Value.NativeQuery(Src, "SELECT * FROM gold.fct_sales")
\t\t\tin
\t\t\t\tData
"""


def test_parse_tmdl_does_not_capture_source_like_property() -> None:
    """A table-level line that merely starts with 'source' followed by a
    non-word char (e.g. ``source.alias = ...``) is NOT a partition source
    block; only a real ``source =`` / ``partition <name> =`` header is
    captured (m-2 regex tightening — the old ``\\b``-anchored form wrongly
    matched ``source.alias = ...``).
    """
    table = parse_tmdl(SOURCE_LIKE_PROPERTY_TMDL)
    assert table is not None
    # Exactly one partition source captured (the real ``source =`` block),
    # not the ``source.alias = legacy_value`` property line.
    assert len(table.partition_sources) == 1
    assert "gold.fct_sales" in table.partition_sources[0]
    assert "legacy_value" not in table.partition_sources[0]
