"""Shared disclosure-safe projection over existing readiness authorities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .agent_next import build_agent_next_document, build_table_next_document
from .disclosure import scan_disclosure
from .status_surface import build_status_projection

SCHEMA_VERSION = "1.0"
_STAGE_ORDER = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _source_revision(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _projection_invariant_findings(
    tables: list[dict[str, Any]],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for table in tables:
        source = table["source_path"]
        for stage, block in table["stages"].items():
            if block["status"] == "pass" and not block["evidence"]:
                findings.append(
                    {
                        "rule": "projection_pass_without_evidence",
                        "locator": f"{source}#stages.{stage}",
                        "message": "pass stage has no inspectable evidence",
                    }
                )
            if block["status"] == "blocked" and not block["blocking_reasons"]:
                findings.append(
                    {
                        "rule": "projection_blocked_without_reason",
                        "locator": f"{source}#stages.{stage}",
                        "message": "blocked stage has no concrete blocking reason",
                    }
                )
    return findings


def _table_projection(root: Path, table: dict[str, Any]) -> dict[str, Any]:
    source_path = table["source_path"]
    directory_name = source_path.rsplit("/", 2)[-2]
    # Per-table document (no portfolio summaries): keeps this projection
    # linear in table count instead of quadratic (spec 120 scale target).
    next_document = build_table_next_document(root, directory_name)
    stages = {
        stage: table["stages"][stage]
        for stage in _STAGE_ORDER
        if stage in table["stages"]
    }
    return {
        "table_id": table["table"],
        "source_path": source_path,
        "current_stage": table["current_stage"],
        "stages": stages,
        "blocking_reasons": table["blocking_reasons"],
        "next_action": next_document["next_allowed_action"],
        "forbidden_scope": next_document["forbidden_scope"],
        "stop_point": next_document["stop_point"],
        "required_authority": next_document["required_authority"],
        "read_only_proof": True,
    }


def build_readiness_projection(repo_root: Path | str = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    status = build_status_projection(root)
    tables = [_table_projection(root, table) for table in status["tables"]]
    portfolio_next = build_agent_next_document(root)
    safe_body = {
        "schema_version": SCHEMA_VERSION,
        "workspace": {"label": root.name, "source_revision": _source_revision(root)},
        "tables": tables,
        "portfolio_next": portfolio_next,
        "lineage": {"nodes": [], "edges": []},
        "generated_at": None,
    }
    disclosure = scan_disclosure(safe_body)
    invariant_findings = _projection_invariant_findings(tables)
    if invariant_findings:
        disclosure = {
            **disclosure,
            "status": "blocked",
            "findings": [*disclosure["findings"], *invariant_findings],
        }
    return {**safe_body, "disclosure": disclosure}
