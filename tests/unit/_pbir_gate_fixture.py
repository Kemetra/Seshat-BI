from __future__ import annotations

import json
from pathlib import Path

from tests.unit._gitfix import commit_all, make_git_repo

_CONTRACT = """\
name: "OrdersCount"
owner: metric_owner
binds_to:
  gold_table: "gold.orders"
definition: {kind: base, aggregation: count, filter: []}
readiness:
  status: pass
  evidence: ["approved by the named metric owner"]
  blocking_reasons: []
"""

MODEL = "Orders.SemanticModel"


def _write_model(repo: Path, name: str = MODEL, table: str = "gold orders") -> Path:
    model = repo / name
    tables = model / "definition" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    (tables / "orders.tmdl").write_text(f"table '{table}'\n", encoding="utf-8")
    return model


def pbir_gate_repo(tmp_path: Path, *, approved: bool = True) -> Path:
    """A committed repo whose ``orders`` table may be PBIR-authored: semantic
    pass, an approved contract bound to ``gold.orders``, a model holding that
    table, and (when ``approved``) a named report_owner dashboard_ready approval."""
    repo = make_git_repo(tmp_path)
    scope = repo / "mappings" / "orders"
    (scope / "metrics").mkdir(parents=True)
    (scope / "metrics" / "OrdersCount.yaml").write_text(_CONTRACT, encoding="utf-8")
    dashboard = (
        '  - stage: "dashboard_ready"\n'
        '    owner: "A Person (report_owner)"\n'
        '    at: "2026-08-10"\n'
        '    note: "Approved report design"\n'
        if approved
        else ""
    )
    (scope / "readiness-status.yaml").write_text(
        'stages:\n  semantic_model_ready:\n    status: "pass"\napprovals:\n'
        '  - stage: "semantic_model_ready"\n'
        '    owner: "M Owner (metric_owner)"\n'
        '    at: "2026-08-10"\n'
        "    contracts: [OrdersCount]\n" + dashboard,
        encoding="utf-8",
    )
    _write_model(repo)
    commit_all(repo, "record PBIR authoring evidence")
    return repo


def bind_report(report: Path, model_path: str = f"../{MODEL}") -> Path:
    """Point a copied report's definition.pbir at a model (relative path)."""
    report.mkdir(parents=True, exist_ok=True)
    (report / "definition.pbir").write_text(
        json.dumps({"datasetReference": {"byPath": {"path": model_path}}}),
        encoding="utf-8",
    )
    return report


def report_home(tmp_path: Path) -> Path:
    """Where tests place copied reports: inside the gate repo."""
    return tmp_path / "repo"


def gate_args(repo: Path) -> list[str]:
    return ["--repo", str(repo), "--table", "orders"]
