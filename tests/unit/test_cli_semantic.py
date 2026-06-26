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

# An escalate DAX: uses LEN() predicate rather than ISBLANK/NOT, which the drift
# checker cannot confidently compare (escalates to WARNING, exit 0).
_MEASURE_LINE_ESCALATE = (
    "\tmeasure AvgTransactionValue = DIVIDE([TotalSales], "
    "CALCULATE([TransactionCount], "
    "LEN('gold fct_sales_rss'[total_spent]) <> 0))"
)
_TMDL_ESCALATE = (
    "table 'gold fct_sales_rss'\n\n"
    + _MEASURE_LINE_ESCALATE
    + "\n\t\tdisplayFolder: Sales\n"
)

# Contract matching the escalate DAX numerically (correct filter column),
# so the only reason for escalation is the predicate form.
_CONTRACT_ESCALATE = """\
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


def _make_repo(tmp_path: Path, contract: str) -> Path:
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        _TMDL,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    return tmp_path


def _make_repo_tmdl(tmp_path: Path, tmdl: str, contract: str) -> Path:
    """Like _make_repo but lets the caller inject a custom TMDL string."""
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        tmdl,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    return tmp_path


def test_semantic_check_clean_exits_zero(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])
    assert code == 0
    # #47: capsys was taken but never read; assert the "no drift" message is printed
    err = capsys.readouterr().err
    assert "no drift" in err


def test_semantic_check_drift_exits_one(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_DRIFT)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])
    assert code == 1
    out = capsys.readouterr().out
    assert "L3" in out
    assert "AvgTransactionValue" in out


def test_semantic_check_rejects_metrics_dir_escaping_repo(
    tmp_path: Path, capsys
) -> None:
    """A `--metrics-dir` that traverses OUT of the repo (`../...`) must be rejected,
    not silently globbed outside the repo tree (audit #26 path traversal)."""
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    # Plant a contract OUTSIDE the repo; a traversal must not reach it.
    _write(tmp_path.parent / "evil/metrics/AvgTransactionValue.yaml", _CONTRACT_DRIFT)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "../evil"])
    assert code == 1
    err = capsys.readouterr().err
    assert "metrics-dir" in err or "outside" in err or "escap" in err.lower()


def test_semantic_check_escalate_exits_zero_and_prints_l3_warning(
    tmp_path: Path, capsys
) -> None:
    """#18: escalate-verdict measure exits 0 and prints L3 WARNING.

    The escalate DAX uses an LEN() predicate the drift engine cannot match
    deterministically, so it escalates to WARNING. The gate must still exit 0
    (WARNING does not fail the gate) and must surface the L3 finding on stdout.
    """
    repo = _make_repo_tmdl(tmp_path, _TMDL_ESCALATE, _CONTRACT_ESCALATE)
    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])
    assert code == 0, "escalate (WARNING) must not fail the semantic-check gate"
    out = capsys.readouterr().out
    assert "L3" in out, "L3 WARNING finding must be printed on stdout"
    assert "AvgTransactionValue" in out


def test_semantic_check_measure_without_contract_is_skipped(
    tmp_path: Path, capsys
) -> None:
    """#50: a measure with no matching contract YAML produces no L3 finding; exits 0.

    The CLI pairs measures only when the YAML stem matches the measure name (line
    327 of cli.py: `if measure.name in definitions`). An unmatched measure is
    silently skipped -- it is NOT flagged as drift.
    """
    # Write a repo with a measure (AvgTransactionValue) but NO contract YAML for it.
    # The mappings dir exists so the path-traversal guard doesn't fire, but it holds
    # no file matching the measure name.
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        _TMDL,
    )
    _write(
        tmp_path / "mappings/ds/metrics/OtherMeasure.yaml",
        'name: "OtherMeasure"\n',
    )
    code = main(
        ["semantic-check", "--repo", str(tmp_path), "--metrics-dir", "mappings"]
    )
    assert code == 0, "a measure with no contract must be skipped, not flagged"
    out = capsys.readouterr().out
    assert "AvgTransactionValue" not in out
    assert "L3" not in out


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
