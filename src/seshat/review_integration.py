"""Stable change-review result derived from existing governance findings."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .core import Finding, Severity

SCHEMA_VERSION = "1.0"
_STAGE_HINTS = {
    "bronze": "source_ready",
    "source-map": "mapping_ready",
    "mapping": "mapping_ready",
    "silver": "silver_ready",
    "gold": "gold_ready",
    "metric": "semantic_model_ready",
    "tmdl": "semantic_model_ready",
    "powerbi": "dashboard_ready",
    "publish": "publish_ready",
}


def _changed_files(repo_root: Path, commit_range: str | None) -> list[str]:
    if not commit_range:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-only", commit_range],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ValueError("commit range could not be inspected")
    return sorted(
        {line.replace("\\", "/") for line in result.stdout.splitlines() if line}
    )


def _affected_stages(paths: Iterable[str], findings: Iterable[Finding]) -> list[str]:
    material = [*paths, *(finding.locator for finding in findings)]
    stages = {
        stage
        for value in material
        for hint, stage in _STAGE_HINTS.items()
        if hint in value.lower()
    }
    return sorted(stages)


def _digest(result: dict[str, Any]) -> str:
    material = {
        "findings": result["findings"],
        "changed_files": result["changed_files"],
        "affected_stages": result["affected_stages"],
        "next_actions": result["next_actions"],
        "run_boundary": result["run_boundary"],
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_review_result(
    findings: Iterable[Finding],
    *,
    repo_root: Path,
    commit_range: str | None = None,
    next_actions: Iterable[str] = (),
) -> dict[str, Any]:
    ordered = sorted(
        findings,
        key=lambda finding: (
            finding.rule_id,
            finding.severity.value,
            finding.locator,
            finding.message,
        ),
    )
    changed_files = _changed_files(repo_root, commit_range)
    blocking = [finding for finding in ordered if finding.severity is Severity.ERROR]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "outcome": "blocked" if blocking else "ok",
        "checks_run": sorted({finding.rule_id for finding in ordered}),
        "changed_files": changed_files,
        "changed_readiness_state": [
            path for path in changed_files if path.endswith("readiness-status.yaml")
        ],
        "affected_stages": _affected_stages(changed_files, ordered),
        "findings": [finding.to_dict() for finding in ordered],
        "blocking_findings": [finding.to_dict() for finding in blocking],
        "next_actions": sorted(set(next_actions)),
        "run_boundary": {
            "static_checks": "blocked" if blocking else "pass",
            "live_validation": "not_run",
            "semantic_correctness_claimed": False,
        },
    }
    result["result_digest"] = _digest(result)
    return result


def markdown_summary(result: dict[str, Any]) -> str:
    outcome = str(result["outcome"]).upper()
    lines = [f"## Seshat BI review: {outcome}", ""]
    lines.append(f"Digest: `{result['result_digest']}`")
    lines.append(
        "Boundary: static governance only; live validation and semantic correctness "
        "were not claimed."
    )
    if result["affected_stages"]:
        lines.append("Affected stages: " + ", ".join(result["affected_stages"]))
    if result["blocking_findings"]:
        lines.extend(("", "### Blocking findings"))
        for finding in result["blocking_findings"]:
            lines.append(
                f"- `{finding['rule_id']}` {finding['message']} "
                f"(`{finding['locator']}`)"
            )
    if result["next_actions"]:
        lines.extend(("", "### Next allowed actions"))
        lines.extend(f"- {action}" for action in result["next_actions"])
    return "\n".join(lines) + "\n"
