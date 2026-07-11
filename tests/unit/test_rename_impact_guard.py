"""Unit tests for HR9 (rename-impact orphaned-reference guard)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.rename_impact_guard import check_hr9

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]

_TMDL_DIR = "powerbi/M.SemanticModel/definition/tables"


def _tmdl(tmp_path: Path, fname: str, text: str) -> str:
    rel = f"{_TMDL_DIR}/{fname}"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return rel


def _metric(tmp_path: Path, table: str, fname: str, text: str) -> str:
    rel = f"mappings/{table}/metrics/{fname}"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return rel


def _binding(tmp_path: Path, table: str, text: str) -> str:
    rel = f"mappings/{table}/design/visual-contract-binding-map.md"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return rel


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


_FCT_TMDL = """\
table 'gold fct'
\tmeasure TotalSales = SUM('gold fct'[total_spent])
\tmeasure AvgValue = DIVIDE([TotalSales], [TxnCount])
\tmeasure TxnCount = COUNTROWS('gold fct')
\tcolumn total_spent
\t\tdataType: double
\tcolumn quantity
\t\tdataType: int64
"""


# --- FR-007: no TMDL -> no engagement ---


def test_hr9_no_tmdl_no_finding(tmp_path: Path) -> None:
    m = _metric(
        tmp_path,
        "t1",
        "Total.yaml",
        "binds_to:\n  gold_table: gold.fct\n  columns:\n    - total_spent\n",
    )
    ctx = _ctx(tmp_path, m)  # no TMDL tracked
    assert list(check_hr9(ctx)) == []


# --- FR-003: metric contract binds_to column resolution ---


def test_hr9_metric_contract_resolving_column_clean(tmp_path: Path) -> None:
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    m = _metric(
        tmp_path,
        "t1",
        "Total.yaml",
        "binds_to:\n  gold_table: gold.fct\n  columns:\n    - total_spent\n",
    )
    ctx = _ctx(tmp_path, t, m)
    assert list(check_hr9(ctx)) == []


def test_hr9_metric_contract_orphaned_column_fails_closed(tmp_path: Path) -> None:
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    m = _metric(
        tmp_path,
        "t1",
        "Total.yaml",
        "binds_to:\n  gold_table: gold.fct\n  columns:\n    - renamed_amount\n",
    )
    ctx = _ctx(tmp_path, t, m)
    findings = list(check_hr9(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR9"
    assert "renamed_amount" in findings[0].message


def test_hr9_metric_contract_checked_regardless_of_status(tmp_path: Path) -> None:
    # FR-008: referential integrity is independent of readiness.status
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    m = _metric(
        tmp_path,
        "t1",
        "Total.yaml",
        "readiness:\n  status: not_started\n"
        "binds_to:\n  gold_table: gold.fct\n  columns:\n    - gone_col\n",
    )
    ctx = _ctx(tmp_path, t, m)
    findings = list(check_hr9(ctx))
    assert any("gone_col" in f.message for f in findings)


# --- FR-004: TMDL DAX reference resolution ---


def test_hr9_tmdl_dax_all_refs_resolve_clean(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL))
    assert list(check_hr9(ctx)) == []


def test_hr9_tmdl_dax_orphaned_measure_ref_fails_closed(tmp_path: Path) -> None:
    tmdl = (
        "table 'gold fct'\n"
        "\tmeasure A = SUM('gold fct'[total_spent])\n"
        "\tmeasure B = DIVIDE([A], [DeletedMeasure])\n"
        "\tcolumn total_spent\n\t\tdataType: double\n"
    )
    ctx = _ctx(tmp_path, _tmdl(tmp_path, "fct.tmdl", tmdl))
    findings = list(check_hr9(ctx))
    assert any("DeletedMeasure" in f.message for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_hr9_tmdl_dax_orphaned_qualified_column_fails_closed(tmp_path: Path) -> None:
    tmdl = (
        "table 'gold fct'\n"
        "\tmeasure A = SUM('gold fct'[renamed_col])\n"
        "\tcolumn total_spent\n\t\tdataType: double\n"
    )
    ctx = _ctx(tmp_path, _tmdl(tmp_path, "fct.tmdl", tmdl))
    findings = list(check_hr9(ctx))
    assert any("renamed_col" in f.message for f in findings)


# --- FR-005: dashboard binding map reference resolution ---


def test_hr9_binding_map_orphaned_measure_fails_closed(tmp_path: Path) -> None:
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    b = _binding(
        tmp_path,
        "t1",
        "| visual | field |\n|---|---|\n| card | [RemovedMeasure] |\n",
    )
    ctx = _ctx(tmp_path, t, b)
    findings = list(check_hr9(ctx))
    assert any("RemovedMeasure" in f.message for f in findings)


def test_hr9_binding_map_resolving_measure_clean(tmp_path: Path) -> None:
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    b = _binding(
        tmp_path,
        "t1",
        "| visual | field |\n|---|---|\n| card | [TotalSales] |\n",
    )
    ctx = _ctx(tmp_path, t, b)
    assert list(check_hr9(ctx)) == []


def test_hr9_ignores_partition_source_m_block(tmp_path: Path) -> None:
    """Regression: a partition ... source = let ... in M block carries [Field] /
    [Schema = ...] accessors that are M syntax, NOT DAX measure refs -- HR9 must
    NOT flag them (FR-004 scopes to a measure's own DAX)."""
    tmdl = (
        "table 'gold fct'\n"
        "\tmeasure TotalSales = SUM('gold fct'[total_spent])\n"
        "\tcolumn total_spent\n\t\tdataType: double\n"
        "\tpartition 'gold fct' = m\n"
        "\t\tmode: import\n"
        "\t\tsource =\n"
        "\t\t\t\tlet\n"
        "\t\t\t\t  Source = PostgreSQL.Database(Server, Database),\n"
        '\t\t\t\t  #"Navigation 1" = Source{[Schema = "gold", Item = "fct"]}[Data]\n'
        "\t\t\t\tin\n"
        '\t\t\t\t  #"Navigation 1"\n'
    )
    ctx = _ctx(tmp_path, _tmdl(tmp_path, "fct.tmdl", tmdl))
    assert list(check_hr9(ctx)) == []


def test_hr9_measure_with_child_properties_does_not_leak(tmp_path: Path) -> None:
    """Regression (review Important): a measure with its own \\t\\t child props
    (formatString, lineageTag) must be scoped correctly, and a following partition
    block must still be excluded -- the block terminator must be airtight."""
    tmdl = (
        "table 'gold fct'\n"
        "\tmeasure TotalSales = SUM('gold fct'[total_spent])\n"
        "\t\tformatString: #,0\n"
        "\t\tlineageTag: abc-123\n"
        "\tcolumn total_spent\n\t\tdataType: double\n"
        "\tpartition 'gold fct' = m\n"
        "\t\tsource =\n"
        '\t\t\t\tlet S = Source{[Schema = "gold", Item = "fct"]}[Data] in S\n'
    )
    ctx = _ctx(tmp_path, _tmdl(tmp_path, "fct.tmdl", tmdl))
    assert list(check_hr9(ctx)) == []


def test_hr9_binding_map_unquoted_qualified_orphan_fails_closed(tmp_path: Path) -> None:
    """Regression (review Important, FR-005): an UNQUOTED table[column] ref in a
    binding map that no longer resolves must be caught (the committed binding-map
    idiom is dim_x[col], not 'dim_x'[col])."""
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    b = _binding(
        tmp_path,
        "t1",
        "| visual | field |\n|---|---|\n| bar | [TotalSales] by gold fct[gone_col] |\n",
    )
    ctx = _ctx(tmp_path, t, b)
    findings = list(check_hr9(ctx))
    assert any("gone_col" in f.message for f in findings)


# --- landing: clean on the real committed tree ---


def test_hr9_clean_on_real_committed_tree() -> None:
    tracked = tuple(
        subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=_REPO
        ).stdout.split()
    )
    ctx = RuleContext(repo_root=_REPO, tracked_files=tracked)
    assert list(check_hr9(ctx)) == []


# --- polish: static-only, no numeric score ---


def test_hr9_module_imports_no_database_driver() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "rename_impact_guard.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_hr9_messages_have_no_numeric_score(tmp_path: Path) -> None:
    t = _tmdl(tmp_path, "fct.tmdl", _FCT_TMDL)
    m = _metric(
        tmp_path,
        "t1",
        "Total.yaml",
        "binds_to:\n  gold_table: gold.fct\n  columns:\n    - bad\n",
    )
    ctx = _ctx(tmp_path, t, m)
    for f in check_hr9(ctx):
        assert "%" not in f.message
