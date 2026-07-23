"""CLI-level tests for `seshat pbir-validate-bindings` (#454).

Mirrors ``test_pbir_validate_blueprint_cli.py``: exercises the wired
``_DISPATCH`` entry through ``seshat.cli.main``, not the library directly.
Read-only -- exit code communicates resolution (0 = pass/warning, 1 = blocked);
the CLI never writes a file and never grants approval.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

_MODEL_TMDL = (
    "table Sales\n"
    "\tcolumn Amount\n"
    "\t\tdataType: decimal\n"
    "\n"
    "\tmeasure 'Total Amount' = SUM(Sales[Amount])\n"
    "\n"
    "table dim_date\n"
    "\tcolumn year\n"
    "\t\tdataType: int64\n"
)


def _field(kind: str, entity: str, prop: str) -> dict:
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def _setup(tmp_path: Path, *fields: dict) -> tuple[Path, Path]:
    model_dir = tmp_path / "Demo.SemanticModel"
    (model_dir / "definition").mkdir(parents=True)
    (model_dir / "definition" / "model.tmdl").write_text(_MODEL_TMDL, encoding="utf-8")
    report_dir = tmp_path / "Demo.Report"
    visual = (
        report_dir / "definition" / "pages" / "pg" / "visuals" / "v1" / "visual.json"
    )
    visual.parent.mkdir(parents=True)
    visual.write_text(
        json.dumps(
            {
                "name": "v1",
                "visual": {
                    "visualType": "lineChart",
                    "query": {
                        "queryState": {
                            "Y": {
                                "projections": [
                                    {"field": f, "queryRef": f"q{i}"}
                                    for i, f in enumerate(fields)
                                ]
                            }
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return report_dir, model_dir


def _run(report_dir: Path, model_dir: Path) -> int:
    return main(
        [
            "pbir-validate-bindings",
            "--report",
            str(report_dir),
            "--model",
            str(model_dir),
        ]
    )


def test_cli_resolving_report_exit_zero(tmp_path: Path, capsys):
    report_dir, model_dir = _setup(
        tmp_path,
        _field("Column", "dim_date", "year"),
        _field("Measure", "Sales", "Total Amount"),
    )
    assert _run(report_dir, model_dir) == 0
    out = capsys.readouterr().out
    assert "status: pass" in out
    assert "grants no approval" in out


def test_cli_unresolved_binding_exit_one(tmp_path: Path, capsys):
    report_dir, model_dir = _setup(
        tmp_path, _field("Column", "dim_staff", "person_name")
    )
    assert _run(report_dir, model_dir) == 1
    out = capsys.readouterr().out
    assert "status: blocked" in out
    assert "[unresolved]" in out


def test_cli_kind_mismatch_warns_exit_zero(tmp_path: Path, capsys):
    # The #456 shape: a dimension attribute projected as Measure. Semantically
    # wrong (warned) but not an error card -- the authoring fix lives in the
    # generator, so the validator reports without blocking.
    report_dir, model_dir = _setup(tmp_path, _field("Measure", "dim_date", "year"))
    assert _run(report_dir, model_dir) == 0
    out = capsys.readouterr().out
    assert "status: warning" in out
    assert "[kind]" in out


def test_cli_fails_closed_on_missing_model(tmp_path: Path):
    report_dir, _ = _setup(tmp_path, _field("Column", "dim_date", "year"))
    assert _run(report_dir, tmp_path / "no-such.SemanticModel") == 1


def test_cli_fails_closed_on_empty_report(tmp_path: Path):
    _, model_dir = _setup(tmp_path, _field("Column", "dim_date", "year"))
    empty = tmp_path / "Empty.Report"
    (empty / "definition" / "pages").mkdir(parents=True)
    assert _run(empty, model_dir) == 1
