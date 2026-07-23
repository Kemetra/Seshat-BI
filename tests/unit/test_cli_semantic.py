"""Tests for `retail semantic-check` subcommand + its stdlib-purity guard."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.cli import main

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

_APPROVED_READINESS = """\
owner: metric_owner
binds_to:
  gold_table: "gold.fct_sales_rss"
readiness:
  status: pass
  evidence: ["approved by Metric Owner on 2026-07-22"]
  blocking_reasons: []
"""

_CONTRACT_CLEAN = (
    """\
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
    + _APPROVED_READINESS
)

_CONTRACT_DRIFT = (
    """\
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
    + _APPROVED_READINESS
)

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
_CONTRACT_ESCALATE = (
    """\
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
    + _APPROVED_READINESS
)


def _make_repo(tmp_path: Path, contract: str) -> Path:
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        _TMDL,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    _write_semantic_approval(tmp_path, "ds")
    return tmp_path


def _make_repo_tmdl(tmp_path: Path, tmdl: str, contract: str) -> Path:
    """Like _make_repo but lets the caller inject a custom TMDL string."""
    _write(
        tmp_path / "powerbi/M.SemanticModel/definition/tables/gold fct_sales_rss.tmdl",
        tmdl,
    )
    _write(tmp_path / "mappings/ds/metrics/AvgTransactionValue.yaml", contract)
    _write_semantic_approval(tmp_path, "ds")
    return tmp_path


def _write_semantic_approval(
    root: Path,
    scope: str,
    contracts: tuple[str, ...] = ("AvgTransactionValue",),
) -> None:
    approved_names = ", ".join(contracts)
    _write(
        root / "mappings" / scope / "readiness-status.yaml",
        "approvals:\n"
        "  - stage: semantic_model_ready\n"
        '    owner: "Ada Lovelace (metric_owner)"\n'
        '    at: "2026-07-22"\n'
        f'    note: "approved metric contracts: {approved_names}"\n',
    )


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


def test_semantic_check_measure_without_contract_is_an_error(
    tmp_path: Path, capsys
) -> None:
    """A TMDL measure without an approved contract blocks semantic readiness."""
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
    assert code == 1
    out = capsys.readouterr().out
    assert "AvgTransactionValue" in out
    assert "no approved metric contract" in out


def test_semantic_check_approved_contract_without_measure_is_an_error(
    tmp_path: Path, capsys
) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    _write(
        repo / "mappings/ds/metrics/UnusedMeasure.yaml",
        _CONTRACT_CLEAN.replace("AvgTransactionValue", "UnusedMeasure"),
    )
    _write_semantic_approval(repo, "ds", ("AvgTransactionValue", "UnusedMeasure"))

    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])

    assert code == 1
    assert "UnusedMeasure" in capsys.readouterr().out


def test_same_measure_name_in_different_tables_binds_by_scope(
    tmp_path: Path, capsys
) -> None:
    contract = """\
name: TotalSales
owner: metric_owner
binds_to: {gold_table: GOLD_TABLE}
definition: {kind: base, aggregation: sum, filter: []}
readiness:
  status: pass
  evidence: [approved by named metric owner]
  blocking_reasons: []
    """
    for scope, gold_table in (("sales", "gold.sales"), ("returns", "gold.returns")):
        _write_semantic_approval(tmp_path, scope, ("TotalSales",))
        _write(
            tmp_path / "mappings" / scope / "metrics" / "TotalSales.yaml",
            contract.replace("GOLD_TABLE", gold_table),
        )
        _write(
            tmp_path
            / "powerbi"
            / f"{scope}.SemanticModel"
            / "definition"
            / "tables"
            / f"gold {scope}.tmdl",
            f"table 'gold {scope}'\n\tmeasure TotalSales = SUM({scope}[amount])\n",
        )

    code = main(
        ["semantic-check", "--repo", str(tmp_path), "--metrics-dir", "mappings"]
    )

    assert code == 0
    assert "no drift" in capsys.readouterr().err


def test_semantic_check_rejects_duplicate_contract_bindings(
    tmp_path: Path, capsys
) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    _write(
        repo / "mappings/other/metrics/AvgTransactionValue.yaml",
        _CONTRACT_CLEAN,
    )
    _write_semantic_approval(repo, "other")

    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])

    assert code == 1
    assert "duplicate semantic binding" in capsys.readouterr().out


def test_semantic_check_rejects_unapproved_and_invalid_contracts(
    tmp_path: Path, capsys
) -> None:
    repo = _make_repo(
        tmp_path,
        _CONTRACT_CLEAN.replace("status: pass", "status: blocked"),
    )

    code = main(["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"])

    assert code == 1
    out = capsys.readouterr().out
    assert "not owner-approved pass" in out
    assert "AvgTransactionValue" in out


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_semantic_check_ignores_untracked_inputs_unless_requested(
    tmp_path: Path, capsys
) -> None:
    repo = _make_repo(tmp_path, _CONTRACT_CLEAN)
    _git(repo, "init")
    _git(repo, "add", "powerbi", "mappings")
    _write(
        repo / "powerbi/M.SemanticModel/definition/tables/untracked.tmdl",
        "table untracked\n\n\tmeasure UntrackedMeasure = 1\n",
    )

    default_code = main(
        ["semantic-check", "--repo", str(repo), "--metrics-dir", "mappings"]
    )
    default_out = capsys.readouterr().out
    included_code = main(
        [
            "semantic-check",
            "--repo",
            str(repo),
            "--metrics-dir",
            "mappings",
            "--include-untracked",
        ]
    )
    included_out = capsys.readouterr().out

    assert default_code == 0
    assert "UntrackedMeasure" not in default_out
    assert included_code == 1
    assert "UntrackedMeasure" in included_out


# Import prefixes cli.py must NOT carry at module scope (yaml + L3 modules).
_FORBIDDEN_MODULE_SCOPE_IMPORTS = (
    "import yaml",
    "from yaml",
    "from .metric_drift",
    "from .semantic",
    "import seshat.metric_drift",
    "import seshat.semantic",
)


def _imports_forbidden_module(stripped: str) -> bool:
    return any(stripped.startswith(p) for p in _FORBIDDEN_MODULE_SCOPE_IMPORTS)


def test_cli_does_not_import_yaml_or_metric_drift_at_module_scope() -> None:
    """cli.py must keep yaml + L3 modules out of its module scope (stdlib core)."""
    import seshat.cli as cli_mod

    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.lstrip()
        is_top_level = line == stripped  # column 0 == module scope
        if is_top_level and _imports_forbidden_module(stripped):
            raise AssertionError(f"cli.py imports L3/yaml at module scope: {line!r}")
