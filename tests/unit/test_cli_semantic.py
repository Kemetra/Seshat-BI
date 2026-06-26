"""Tests for `retail semantic-check` subcommand + its stdlib-purity guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.cli import main

pytestmark = pytest.mark.unit


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# A minimal repo: one measure in TMDL + one matching contract with a definition.
# The measure stays one logical TMDL line at runtime; the source is concatenated
# across physical lines only to satisfy the 88-col lint (E501).
_MEASURE_LINE = (
    "\tmeasure AvgTransactionValue = DIVIDE([TotalSales], "
    "CALCULATE([TransactionCount], "
    "NOT(ISBLANK('gold fct_sales_rss'[total_spent]))))"
)
_TMDL = f"table 'gold fct_sales_rss'\n\n{_MEASURE_LINE}\n\t\tdisplayFolder: Sales\n"

_CONTRACT_CLEAN = """\
name: "AvgTransactionValue"
definition:
  additive: false
  numerator: {aggregation: sum, filter: []}
  denominator:
    aggregation: count_rows
    filter:
      - column: total_spent
        op: is_not_null
"""

_CONTRACT_DRIFT = """\
name: "AvgTransactionValue"
definition:
  additive: false
  numerator: {aggregation: sum, filter: []}
  denominator:
    aggregation: count_rows
    filter:
      - column: discount_applied
        op: is_not_null
"""


def _make_repo(tmp_path: Path, contract: str) -> Path:
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        _TMDL,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    return tmp_path


def test_semantic_check_clean_exits_zero(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])
    assert code == 0


def test_semantic_check_drift_exits_one(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_DRIFT)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])
    assert code == 1
    out = capsys.readouterr().out
    assert "L3" in out
    assert "AvgTransactionValue" in out


def test_cli_does_not_import_yaml_or_metric_drift_at_module_scope() -> None:
    """cli.py must keep yaml + L3 modules out of its module scope (stdlib core)."""
    import retail.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.lstrip()
        is_top_level = line == stripped  # column 0 == module scope
        if is_top_level and (
            stripped.startswith("import yaml")
            or stripped.startswith("from yaml")
            or stripped.startswith("from .metric_drift")
            or stripped.startswith("from .semantic")
            or stripped.startswith("import retail.metric_drift")
            or stripped.startswith("import retail.semantic")
        ):
            raise AssertionError(f"cli.py imports L3/yaml at module scope: {line!r}")
