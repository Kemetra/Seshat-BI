"""Unit tests for the DAX Generator (src/seshat/dax_gen.py).

Phase 1: kind:base + kind:ratio, generate -> verify -> refuse. The headline
property is the round-trip: every emitted measure re-verifies as `pass`.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.dax_gen import (
    GenResult,
    _emit_base,
    _emit_ratio,
    generate_measure,
    load_contract,
)
from seshat.metric_drift import check_measure_drift

pytestmark = pytest.mark.unit


def test_genresult_success_populates_outputs_only():
    r = GenResult.success(dax="SUM(T[c])", tmdl_block="measure X = SUM(T[c])")
    assert r.ok is True
    assert r.dax == "SUM(T[c])"
    assert r.tmdl_block == "measure X = SUM(T[c])"
    assert r.reason is None


def test_genresult_refuse_has_none_outputs():
    r = GenResult.refuse("unsupported kind 'foo'")
    assert r.ok is False
    assert r.dax is None
    assert r.tmdl_block is None
    assert r.reason == "unsupported kind 'foo'"


def test_genresult_rejects_ok_without_dax():
    with pytest.raises(ValueError):
        GenResult(ok=True, dax=None, tmdl_block=None)


def test_genresult_rejects_refusal_with_dax():
    with pytest.raises(ValueError):
        GenResult(ok=False, dax="SUM(T[c])", reason="x")


def test_emit_base_sum_no_filter():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "sum",
            "source": {"table": "gold.fct_sales_rss", "column": "total_spent"},
        }
    )
    assert reason is None
    assert dax == "SUM('gold fct_sales_rss'[total_spent])"


def test_emit_base_count_rows_no_column():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.fct_sales_rss"},
        }
    )
    assert reason is None
    assert dax == "COUNTROWS('gold fct_sales_rss')"


def test_emit_base_with_filter_wraps_calculate():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.fct_sales_rss"},
            "filter": [{"column": "discount_applied", "op": "is_true"}],
        }
    )
    assert reason is None
    assert dax == (
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE())"
    )


def test_emit_base_sum_without_column_refuses():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "sum",
            "source": {"table": "gold.fct_sales_rss"},
        }
    )
    assert dax is None
    assert "column" in reason


def test_emit_base_count_rows_with_column_refuses():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.fct_sales_rss", "column": "x"},
        }
    )
    assert dax is None
    assert "count_rows" in reason


def test_emit_base_non_gold_table_refuses():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "sum",
            "source": {"table": "silver.fct", "column": "c"},
        }
    )
    assert dax is None
    assert "gold" in reason


def test_emit_base_unknown_aggregation_refuses():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "median",
            "source": {"table": "gold.t", "column": "c"},
        }
    )
    assert dax is None
    assert "aggregation" in reason


def test_emit_base_unknown_filter_op_refuses():
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.t"},
            "filter": [{"column": "c", "op": "is_weird"}],
        }
    )
    assert dax is None
    assert "op" in reason or "filter" in reason


def test_emit_base_filter_scalar_refuses_not_raises() -> None:
    # I1: a scalar `filter` is a malformed contract -> refuse, NEVER raise.
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.t"},
            "filter": "discount_applied",
        }
    )
    assert dax is None
    assert "filter must be a list" in reason


def test_emit_base_filter_single_dict_refuses_not_raises() -> None:
    # I1: a single dict (not a list of dicts) is malformed -> refuse, NEVER raise.
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.t"},
            "filter": {"column": "c", "op": "is_true"},
        }
    )
    assert dax is None
    assert "filter must be a list" in reason


def test_emit_base_filter_element_not_object_refuses() -> None:
    # I1: a list whose element is not a dict is malformed -> refuse, NEVER raise.
    dax, reason = _emit_base(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.t"},
            "filter": ["discount_applied"],
        }
    )
    assert dax is None
    assert "not an object" in reason


def test_generate_measure_malformed_filter_returns_refusal_not_raise() -> None:
    # I1 at the engine boundary: a malformed-filter base contract is a fail-closed
    # refusal (ok=False, dax/tmdl None), not an exception.
    r = generate_measure(
        {
            "kind": "base",
            "aggregation": "count_rows",
            "source": {"table": "gold.t"},
            "filter": "discount_applied",
        },
        name="X",
    )
    assert r.ok is False
    assert r.dax is None and r.tmdl_block is None


BASE_REVENUE = {
    "kind": "base",
    "aggregation": "sum",
    "source": {"table": "gold.fct_sales_rss", "column": "total_spent"},
}
RATIO_DISC = {
    "kind": "ratio",
    "numerator": {
        "aggregation": "count_rows",
        "source": {"table": "gold.fct_sales_rss"},
        "filter": [{"column": "discount_applied", "op": "is_true"}],
    },
    "denominator": {
        "aggregation": "count_rows",
        "source": {"table": "gold.fct_sales_rss"},
        "filter": [{"column": "discount_applied", "op": "is_not_null"}],
    },
}


@pytest.mark.parametrize(
    "name,defn",
    [
        ("TotalRevenue", BASE_REVENUE),
        ("DiscountedRate", RATIO_DISC),
    ],
)
def test_generate_roundtrips_to_pass(name, defn):
    r = generate_measure(defn, name=name, doc_intent="meaning of the measure")
    assert r.ok is True, r.reason
    # THE CORE PROPERTY: the emitted DAX re-verifies as pass against the same contract
    assert check_measure_drift(r.dax, defn).status == "pass"


def test_generated_tmdl_passes_d_rules():
    r = generate_measure(BASE_REVENUE, name="TotalRevenue", doc_intent="total money")
    assert r.ok is True
    # PascalCase name (D1), has displayFolder (D2), has /// doc (D11),
    # uses DIVIDE not / where relevant
    assert "/// " in r.tmdl_block
    assert "displayFolder" in r.tmdl_block
    assert "measure TotalRevenue" in r.tmdl_block


def test_generate_refuses_unknown_kind():
    r = generate_measure({"kind": "wormhole"}, name="X")
    assert r.ok is False
    assert r.dax is None and r.tmdl_block is None
    assert "kind" in r.reason


def test_generate_refuses_bad_pascalcase_name():
    r = generate_measure(BASE_REVENUE, name="total_revenue")  # D1 ERROR
    assert r.ok is False
    assert r.dax is None and r.tmdl_block is None


def test_doc_intent_isolation_same_dax_diff_comment():
    a = generate_measure(BASE_REVENUE, name="Rev", doc_intent="intent A")
    b = generate_measure(BASE_REVENUE, name="Rev", doc_intent="intent B")
    assert a.dax == b.dax  # identical semantics
    assert a.tmdl_block != b.tmdl_block  # differ only in the /// comment
    assert "intent A" in a.tmdl_block and "intent B" in b.tmdl_block


def test_emit_ratio_inline_count_rows():
    dax, reason = _emit_ratio(
        {
            "kind": "ratio",
            "numerator": {
                "aggregation": "count_rows",
                "source": {"table": "gold.fct_sales_rss"},
                "filter": [{"column": "discount_applied", "op": "is_true"}],
            },
            "denominator": {
                "aggregation": "count_rows",
                "source": {"table": "gold.fct_sales_rss"},
                "filter": [{"column": "discount_applied", "op": "is_not_null"}],
            },
        }
    )
    assert reason is None
    assert dax == (
        "DIVIDE("
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "'gold fct_sales_rss'[discount_applied] = TRUE()), "
        "CALCULATE(COUNTROWS('gold fct_sales_rss'), "
        "NOT(ISBLANK('gold fct_sales_rss'[discount_applied]))))"
    )


def test_emit_ratio_refuses_bad_side():
    dax, reason = _emit_ratio(
        {
            "kind": "ratio",
            "numerator": {
                "aggregation": "sum",
                "source": {"table": "gold.t"},
            },  # no column
            "denominator": {"aggregation": "count_rows", "source": {"table": "gold.t"}},
        }
    )
    assert dax is None
    assert "column" in reason


def test_load_contract_reads_definition(tmp_path: Path):
    p = tmp_path / "c.yaml"
    p.write_text(
        'name: "Rev"\nformula_intent: "money"\n'
        "definition:\n  kind: base\n  aggregation: sum\n"
        "  source:\n    table: gold.t\n    column: c\n",
        encoding="utf-8",
    )
    data = load_contract(str(p))
    assert data["name"] == "Rev"
    assert data["definition"]["kind"] == "base"


def test_dax_gen_import_is_stdlib_only():
    # importing dax_gen must NOT pull yaml at import time (lazy in load_contract)
    import os

    code = (
        "import sys; import seshat.dax_gen; "
        "assert 'yaml' not in sys.modules, 'yaml imported at module scope'"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert r.returncode == 0, r.stderr


CONTRACTS = Path(__file__).parent.parent / "fixtures" / "contracts"
_WORKTREE_SRC = str(Path(__file__).parent.parent.parent / "src")


def _run_cli(*argv: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = _WORKTREE_SRC
    return subprocess.run(
        [sys.executable, "-m", "seshat.cli", *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def test_cli_generate_success_stdout_tmdl() -> None:
    r = _run_cli("generate", "--contract", str(CONTRACTS / "base_revenue.yaml"))
    assert r.returncode == 0
    assert "measure TotalRevenue" in r.stdout
    assert r.stderr.strip() == ""


def test_cli_generate_refusal_stdout_empty_stderr_reason() -> None:
    r = _run_cli("generate", "--contract", str(CONTRACTS / "refuse_no_column.yaml"))
    assert r.returncode == 1
    assert r.stdout.strip() == ""  # stdout = verified-only
    assert "refused" in r.stderr.lower()


def test_cli_generate_json_format() -> None:
    r = _run_cli(
        "generate", "--contract", str(CONTRACTS / "ratio_disc.yaml"), "--format", "json"
    )
    assert r.returncode == 0
    import json

    obj = json.loads(r.stdout)
    assert obj["ok"] is True and obj["dax"].startswith("DIVIDE(")


_REPO_ROOT = Path(__file__).parents[2]


def test_cli_out_refuses_powerbi_path(tmp_path: Path) -> None:
    # an --out whose resolved path has a `powerbi` component is refused.
    # Run from a tmp cwd so the component guard -- not a cwd-relative accident --
    # is what fires; assert the REFUSAL line, not just the word "powerbi".
    target = "powerbi/Model.SemanticModel/x.tmdl"
    r = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        target,
        cwd=str(tmp_path),
    )
    assert r.returncode == 1
    assert "refused" in r.stderr.lower()
    assert r.stdout.strip() == ""
    assert not (tmp_path / target).exists()


def test_cli_out_refuses_traversal_into_powerbi(tmp_path: Path) -> None:
    # `../powerbi/...` resolves to a path with a `powerbi` component -> refused.
    r = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        "../powerbi/sneak.tmdl",
        cwd=str(tmp_path),
    )
    assert r.returncode == 1
    assert "refused" in r.stderr.lower()
    assert r.stdout.strip() == ""
    assert not (tmp_path.parent / "powerbi" / "sneak.tmdl").exists()


def test_cli_out_refuses_absolute_into_powerbi(tmp_path: Path) -> None:
    # REGRESSION TEST FOR C1: an ABSOLUTE --out into the REAL repo's powerbi/
    # tree, run from a DIFFERENT cwd, must be refused -- never written.
    # Pre-fix (cwd-anchored guard) this BYPASSED the guard and wrote into the
    # model; post-fix the cwd-independent component guard refuses it.
    sneak = (
        _REPO_ROOT
        / "powerbi"
        / "Model.SemanticModel"
        / "definition"
        / "tables"
        / "SNEAK.tmdl"
    )
    r = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        str(sneak),
        cwd=str(tmp_path),
    )
    assert r.returncode == 1
    assert "refused" in r.stderr.lower()
    assert r.stdout.strip() == ""
    assert not sneak.exists()  # the model must be untouched


def test_cli_out_refuses_nonexistent_parent_dir(tmp_path: Path) -> None:
    # M3: --out does NOT silently create parent dirs -- refuse cleanly (no traceback).
    out = tmp_path / "does_not_exist" / "m.tmdl"
    r = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        str(out),
    )
    assert r.returncode == 1
    assert "refused" in r.stderr.lower()
    assert r.stdout.strip() == ""
    assert not out.exists()


def test_cli_out_writes_then_refuses_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "m.tmdl"
    r1 = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        str(out),
    )
    assert r1.returncode == 0 and out.exists()
    r2 = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        str(out),
    )
    assert r2.returncode == 1
    assert "exist" in r2.stderr.lower()


def test_cli_out_refuses_symlink_into_powerbi(tmp_path: Path):
    # a symlink whose target resolves under powerbi/ must be refused.
    # Skip ONLY the symlink case where the OS denies symlink creation
    # (Windows without privilege) -- the ../powerbi and absolute cases never skip.
    powerbi = Path.cwd() / "powerbi"
    powerbi.mkdir(exist_ok=True)
    link = tmp_path / "link.tmdl"
    try:
        os.symlink(powerbi / "real.tmdl", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform/CI")
    r = _run_cli(
        "generate",
        "--contract",
        str(CONTRACTS / "base_revenue.yaml"),
        "--out",
        str(link),
    )
    assert r.returncode == 1
    assert "refused" in r.stderr.lower()
    assert "powerbi" in r.stderr.lower()
