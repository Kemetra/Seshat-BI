"""Governed measure sync into an adopted PBIP model (issue #457).

Battery mirrors the fail-closed guard style of test_dax_gen.py and the
no-disclosure posture of test_pbip_adoption_safety.py: every governance gap is
a distinct refusal, every write is atomic and partition-preserving, and no
partition/M-source content ever reaches any output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.pbip_adoption import MANIFEST_PATH
from seshat.pbip_measure_sync import (
    MeasureSyncRequest,
    measure_sync_exit_code,
    render_measure_sync_text,
    sync_measures,
)
from seshat.tmdl import parse_tmdl

pytestmark = pytest.mark.unit

TABLE = "gold fct_sales"
PARTITION_TOKEN = "do-not-echo-partition-token"

TABLE_TMDL = (
    "table 'gold fct_sales'\n"
    "\tlineageTag: 6cb37fcf-1111-4444-8888-aaaaaaaaaaaa\n"
    "\n"
    "\tcolumn amount\n"
    "\t\tdataType: double\n"
    "\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: amount\n"
    "\n"
    "\tcolumn qty\n"
    "\t\tdataType: double\n"
    "\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: qty\n"
    "\n"
    "\tpartition 'gold fct_sales' = m\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\tlet\n"
    "\t\t\t\t  Source = PostgreSQL.Database(Server, Database),\n"
    '\t\t\t\t  Nav = Source{[Schema = "gold", Item = "'
    + PARTITION_TOKEN
    + '"]}[Data]\n'
    "\t\t\t\tin\n"
    "\t\t\t\t  Nav\n"
    "\n"
    "\tannotation PBI_ResultType = Table\n"
)


def _contract_yaml(name: str, column: str, **overrides: str) -> str:
    aggregation = overrides.pop("aggregation", "sum")
    table = overrides.pop("table", "gold.fct_sales")
    status = overrides.pop("status", "pass")
    assert not overrides, f"unknown contract override(s): {sorted(overrides)}"
    return (
        f'name: "{name}"\n'
        'owner: "data_owner"\n'
        f'formula_intent: "Governed measure {name}."\n'
        "binds_to:\n"
        f'  gold_table: "{table}"\n'
        "definition:\n"
        "  kind: base\n"
        f"  aggregation: {aggregation}\n"
        "  source:\n"
        f'    table: "{table}"\n'
        f'    column: "{column}"\n'
        "readiness:\n"
        f'  status: "{status}"\n'
        "  evidence:\n"
        '    - "approved for tests"\n'
        "  blocking_reasons: []\n"
    )


def _readiness_yaml(names: list[str]) -> str:
    joined = ", ".join(names)
    return (
        "approvals:\n"
        '  - stage: "semantic_model_ready"\n'
        '    owner: "Test Owner (metric_owner)"\n'
        '    at: "2026-07-24"\n'
        f'    note: "metric_owner sign-off naming {joined}"\n'
    )


def _make_repo(tmp_path: Path, contracts: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    metrics = repo / "mappings" / "sales" / "metrics"
    metrics.mkdir(parents=True)
    for name, body in contracts.items():
        (metrics / f"{name}.yaml").write_text(body, encoding="utf-8")
    (repo / "mappings" / "sales" / "readiness-status.yaml").write_text(
        _readiness_yaml(sorted(contracts)), encoding="utf-8"
    )
    return repo


def _make_project(
    tmp_path: Path,
    table_text: str = TABLE_TMDL,
    *,
    manifest_model: str | None = "Model.SemanticModel",
    table_filename: str = "gold fct_sales.tmdl",
) -> Path:
    project = tmp_path / "project"
    model_dir = project / "Model.SemanticModel"
    tables = model_dir / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / table_filename).write_text(table_text, encoding="utf-8", newline="")
    if manifest_model is not None:
        manifest = project / Path(MANIFEST_PATH)
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            'schema_version: "1.0"\n'
            "target:\n"
            "  kind: pbip_project\n"
            "  label: project\n"
            "  components:\n"
            "    - kind: semantic_model\n"
            "      identity: Model\n"
            f"      artifact: {manifest_model}/definition/model.tmdl\n",
            encoding="utf-8",
        )
    return model_dir


def _table_path(model_dir: Path) -> Path:
    return model_dir / "definition" / "tables" / "gold fct_sales.tmdl"


def _partition_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    start = text.index("partition 'gold fct_sales'")
    end = text.index("annotation PBI_ResultType")
    return text[start:end].rstrip()


def _sync(repo: Path, model_dir: Path, **kwargs: object) -> dict:
    return sync_measures(MeasureSyncRequest(repo, model_dir, TABLE, **kwargs))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Governance gates
# ---------------------------------------------------------------------------


def test_refuses_without_adoption_manifest(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path, manifest_model=None)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any("adopt-pbip assess" in reason for reason in result["blocking_reasons"])
    assert any("scaffold" in reason for reason in result["blocking_reasons"])
    assert _table_path(model_dir).read_bytes() == before
    assert measure_sync_exit_code(result) == 1


def test_refuses_when_manifest_records_a_different_model(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path, manifest_model="Other.SemanticModel")
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any(
        "does not record this semantic model" in reason
        for reason in result["blocking_reasons"]
    )
    assert _table_path(model_dir).read_bytes() == before


def test_refuses_with_zero_approved_contracts_and_writes_nothing(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, {})
    model_dir = _make_project(tmp_path)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any(
        "No approved metric contract" in reason for reason in result["blocking_reasons"]
    )
    assert _table_path(model_dir).read_bytes() == before


def test_contract_failing_inventory_is_excluded_with_reason(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        {"TotalSales": _contract_yaml("TotalSales", "amount", status="blocked")},
    )
    model_dir = _make_project(tmp_path)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any("TotalSales" in reason for reason in result["excluded"])
    assert any("not owner-approved" in reason for reason in result["excluded"])
    assert _table_path(model_dir).read_bytes() == before


def test_refuses_when_table_file_absent(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(
        tmp_path,
        table_text=TABLE_TMDL.replace("'gold fct_sales'", "'gold other_table'"),
    )
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any(
        "No table definition matching" in reason
        for reason in result["blocking_reasons"]
    )


# ---------------------------------------------------------------------------
# Upsert behavior
# ---------------------------------------------------------------------------


def test_insert_new_measure_before_first_column(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    result = _sync(repo, model_dir)
    assert result["outcome"] == "synced"
    assert result["actions"] == [{"measure": "TotalSales", "action": "insert"}]
    assert result["counts"] == {"insert": 1, "update": 0, "skip": 0}
    text = _table_path(model_dir).read_text(encoding="utf-8-sig")
    parsed = parse_tmdl(text)
    assert parsed is not None
    assert [m.name for m in parsed.measures] == ["TotalSales"]
    measure = parsed.measures[0]
    assert measure.expression == "SUM('gold fct_sales'[amount])"
    # New measures carry NO lineageTag: Desktop assigns one on next open.
    assert "lineageTag" not in text.split("measure TotalSales")[1].split("column")[0]
    # Inserted before the first column header.
    assert text.index("measure TotalSales") < text.index("column amount")


def test_update_changed_measure_preserves_lineage_tag(tmp_path: Path) -> None:
    stale_block = (
        "\t/// stale doc\n"
        "\tmeasure TotalSales = SUM('gold fct_sales'[amount]) + 0\n"
        "\t\tformatString: #,0.00\n"
        "\t\tdisplayFolder: Old\n"
        "\t\tlineageTag: f8a7ec1c-0000-4000-8000-000000000000\n"
        "\n"
    )
    table_text = TABLE_TMDL.replace("\tcolumn amount", stale_block + "\tcolumn amount")
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path, table_text=table_text)
    result = _sync(repo, model_dir)
    assert result["outcome"] == "synced"
    assert result["actions"] == [{"measure": "TotalSales", "action": "update"}]
    text = _table_path(model_dir).read_text(encoding="utf-8-sig")
    assert "stale doc" not in text
    assert "SUM('gold fct_sales'[amount]) + 0" not in text
    assert "lineageTag: f8a7ec1c-0000-4000-8000-000000000000" in text
    parsed = parse_tmdl(text)
    assert parsed is not None
    assert parsed.measures[0].expression == "SUM('gold fct_sales'[amount])"


def test_second_run_skips_everything_and_file_is_byte_identical(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        {
            "TotalSales": _contract_yaml("TotalSales", "amount"),
            "TotalQty": _contract_yaml("TotalQty", "qty"),
        },
    )
    model_dir = _make_project(tmp_path)
    first = _sync(repo, model_dir)
    assert first["outcome"] == "synced"
    assert {a["action"] for a in first["actions"]} == {"insert"}
    after_first = _table_path(model_dir).read_bytes()
    second = _sync(repo, model_dir)
    assert second["outcome"] == "synced"
    assert {a["action"] for a in second["actions"]} == {"skip"}
    assert second["counts"] == {"insert": 0, "update": 0, "skip": 2}
    assert _table_path(model_dir).read_bytes() == after_first


# ---------------------------------------------------------------------------
# Case-insensitive measure identity (issue #476)
# ---------------------------------------------------------------------------

_LINEAGE = "f8a7ec1c-0000-4000-8000-000000000000"


def _measure_block(name: str, *, lineage: str = _LINEAGE) -> str:
    """One existing measure declaration, spelled exactly as given."""
    return (
        f"\tmeasure {name} = SUM('gold fct_sales'[amount])\n"
        "\t\tformatString: #,0.00\n"
        f"\t\tlineageTag: {lineage}\n"
        "\n"
    )


def _with_measures(*blocks: str) -> str:
    joined = "".join(blocks)
    return TABLE_TMDL.replace("\tcolumn amount", joined + "\tcolumn amount")


def _project_with(tmp_path: Path, *blocks: str) -> Path:
    return _make_project(tmp_path, table_text=_with_measures(*blocks))


def test_case_only_contract_match_refuses_instead_of_inserting_duplicate(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _project_with(tmp_path, _measure_block("totalsales"))
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert result["actions"] == []
    assert any("case-insensitive" in reason for reason in result["blocking_reasons"])
    assert any(
        "TotalSales" in reason and "totalsales" in reason
        for reason in result["blocking_reasons"]
    )
    assert _table_path(model_dir).read_bytes() == before
    assert measure_sync_exit_code(result) == 1
    parsed = parse_tmdl(_table_path(model_dir).read_text(encoding="utf-8-sig"))
    assert parsed is not None
    assert [measure.name for measure in parsed.measures] == ["totalsales"]


@pytest.mark.parametrize(
    "spellings",
    [("TotalSales", "TotalSales"), ("totalsales", "TotalSales")],
    ids=["exact", "case-only"],
)
def test_duplicate_measure_declarations_refuse_before_planning(
    tmp_path: Path, spellings: tuple[str, str]
) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    blocks = [
        _measure_block(name, lineage=_LINEAGE[:-1] + str(index))
        for index, name in enumerate(spellings)
    ]
    model_dir = _project_with(tmp_path, *blocks)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any("more than once" in reason for reason in result["blocking_reasons"])
    assert _table_path(model_dir).read_bytes() == before


def test_dry_run_case_only_collision_refuses_and_plans_nothing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _project_with(tmp_path, _measure_block("totalsales"))
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir, dry_run=True)
    assert result["outcome"] == "refused"
    assert result["actions"] == []
    assert result["counts"] == {"insert": 0, "update": 0, "skip": 0}
    assert _table_path(model_dir).read_bytes() == before


def test_case_only_collision_leaves_partition_region_byte_identical(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _project_with(tmp_path, _measure_block("totalsales"))
    before = _partition_text(_table_path(model_dir))
    assert PARTITION_TOKEN in before
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert _partition_text(_table_path(model_dir)) == before


def test_two_approved_contracts_differing_only_by_case_are_refused() -> None:
    """Two approved contracts colliding by case alone can never both be written.

    Proven directly: an end-to-end fixture needs a case-sensitive filesystem,
    because a contract's name must equal its file stem -- so ``TotalSales.yaml``
    and ``totalsales.yaml`` are ONE file on Windows. The inventory dedupes on
    exact name and on semantic binding, so a differently-cased pair over
    different columns still reaches the sync planner on Linux/CI.
    """
    from seshat.pbip_measure_sync import _contract_case_clashes

    clashes = _contract_case_clashes({"TotalSales": "block", "totalsales": "block"})
    assert len(clashes) == 1
    assert "TotalSales" in clashes[0]
    assert "totalsales" in clashes[0]
    assert "case-insensitive" in clashes[0]


def test_distinctly_named_contracts_are_not_reported_as_case_clashes() -> None:
    from seshat.pbip_measure_sync import _contract_case_clashes

    assert _contract_case_clashes({"TotalSales": "b", "TotalQty": "b"}) == []


def test_partition_region_is_byte_identical_after_every_write(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    before = _partition_text(_table_path(model_dir))
    assert PARTITION_TOKEN in before
    result = _sync(repo, model_dir)
    assert result["outcome"] == "synced"
    assert _partition_text(_table_path(model_dir)) == before


def test_refuses_when_edit_would_touch_partition_region(tmp_path: Path) -> None:
    # Crafted: the partition block is nested INSIDE the stale measure block, so
    # replacing the measure would rewrite source bindings. Must refuse.
    crafted = (
        "table 'gold fct_sales'\n"
        "\n"
        "\t/// stale doc\n"
        "\tmeasure TotalSales = SUM('gold fct_sales'[amount]) + 0\n"
        "\t\tformatString: #,0.00\n"
        "\t\tdisplayFolder: Old\n"
        "\t\tpartition 'gold fct_sales' = m\n"
        "\t\t\tsource =\n"
        "\t\t\t\tlet X = 1 in X\n"
    )
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path, table_text=crafted)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any("partition" in reason for reason in result["blocking_reasons"])
    assert _table_path(model_dir).read_bytes() == before


def test_dry_run_reports_plan_and_writes_nothing(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir, dry_run=True)
    assert result["outcome"] == "planned"
    assert result["dry_run"] is True
    assert result["actions"] == [{"measure": "TotalSales", "action": "insert"}]
    assert _table_path(model_dir).read_bytes() == before
    assert measure_sync_exit_code(result) == 0


def test_one_unrenderable_contract_refuses_the_whole_run(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        {
            "TotalSales": _contract_yaml("TotalSales", "amount"),
            "BadAgg": _contract_yaml("BadAgg", "amount", aggregation="median"),
        },
    )
    model_dir = _make_project(tmp_path)
    before = _table_path(model_dir).read_bytes()
    result = _sync(repo, model_dir)
    assert result["outcome"] == "refused"
    assert any("BadAgg" in reason for reason in result["blocking_reasons"])
    # Atomic: the renderable TotalSales must NOT have been written either.
    assert _table_path(model_dir).read_bytes() == before


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def _cli_args(repo: Path, model_dir: Path, *extra: str) -> list[str]:
    return [
        "adopt-pbip",
        "measure-sync",
        "--repo",
        str(repo),
        "--model",
        str(model_dir),
        "--table",
        TABLE,
        *extra,
    ]


def test_cli_measure_sync_json_success(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    code = main(_cli_args(repo, model_dir, "--format", "json"))
    document = json.loads(capsys.readouterr().out)
    assert code == 0
    assert document["outcome"] == "synced"
    assert document["actions"] == [{"measure": "TotalSales", "action": "insert"}]
    assert document["counts"] == {"insert": 1, "update": 0, "skip": 0}
    assert document["table_file"] == "definition/tables/gold fct_sales.tmdl"


def test_cli_measure_sync_refusal_exit_code_and_text(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path, manifest_model=None)
    code = main(_cli_args(repo, model_dir))
    output = capsys.readouterr().out
    assert code == 1
    assert "refused" in output
    assert "adopt-pbip assess" in output


def test_cli_measure_sync_input_defect_exit_code(tmp_path: Path, capsys) -> None:
    code = main(
        [
            "adopt-pbip",
            "measure-sync",
            "--repo",
            str(tmp_path / "missing-repo"),
            "--model",
            str(tmp_path / "missing.SemanticModel"),
            "--table",
            TABLE,
        ]
    )
    capsys.readouterr()
    assert code == 2


def test_cli_text_output_suggests_value_check_via_prog_seam(
    tmp_path: Path, capsys
) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    code = main(_cli_args(repo, model_dir))
    output = capsys.readouterr().out
    assert code == 0
    assert "value-check" in output
    # Branding flows through the _prog seam (main defaults to `seshat`).
    assert "seshat value-check" in output


# ---------------------------------------------------------------------------
# Disclosure safety (mirrors test_pbip_adoption_safety.py)
# ---------------------------------------------------------------------------


def test_no_partition_content_in_any_output(tmp_path: Path, capsys) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    runs = (
        _cli_args(repo, model_dir, "--dry-run", "--format", "json"),
        _cli_args(repo, model_dir, "--format", "text"),
        _cli_args(repo, model_dir, "--format", "json"),
    )
    for argv in runs:
        main(argv)
        captured = capsys.readouterr()
        for stream in (captured.out, captured.err):
            assert PARTITION_TOKEN not in stream
            assert "PostgreSQL.Database" not in stream
            assert "Traceback" not in stream


def test_render_text_never_carries_partition_content(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, {"TotalSales": _contract_yaml("TotalSales", "amount")})
    model_dir = _make_project(tmp_path)
    result = _sync(repo, model_dir)
    rendered = render_measure_sync_text(result, "seshat")
    assert PARTITION_TOKEN not in rendered
    assert PARTITION_TOKEN not in json.dumps(result)
