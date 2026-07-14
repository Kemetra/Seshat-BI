"""Generic (Principle VII) test-fixture builders for Portfolio Watch (spec 131).

No worked-example specifics (billing codes, segments, PII column names, real
per-table grain keys) -- every scope/column/table name here is a generic
placeholder (``scope_alpha``, ``widget_id``, ...), never a C086/pharmacy
literal.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

DEFAULT_STAGES = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def init_git_repo(root: Path) -> str:
    """Initialize a real git repo at ``root`` with one commit, so
    ``git rev-parse HEAD`` (the source_revision seam) succeeds. Returns the
    HEAD sha. ``root`` must already exist."""
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (root / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit_all(root: Path, message: str = "update") -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message], cwd=root, check=True, capture_output=True
    )


def _blocking_reasons_lines(reasons: list[str], *, indent: str) -> list[str]:
    if not reasons:
        return [f"{indent}blocking_reasons: []"]
    return [f"{indent}blocking_reasons:"] + [
        f'{indent}  - "{reason}"' for reason in reasons
    ]


def _stage_lines(
    stage_status: dict[str, str], stage_blocking_reasons: dict[str, list[str]]
) -> list[str]:
    lines: list[str] = []
    for stage in DEFAULT_STAGES:
        status = stage_status.get(stage, "not_started")
        reasons = stage_blocking_reasons.get(stage, [])
        lines.append(f"  {stage}:")
        lines.append(f'    status: "{status}"')
        lines.append("    evidence: []")
        lines.extend(_blocking_reasons_lines(reasons, indent="    "))
    return lines


def _approval_lines(approvals: list[dict[str, str]] | None) -> list[str]:
    if not approvals:
        return ["approvals: []"]
    lines = ["approvals:"]
    for entry in approvals:
        lines.append(f'  - stage: "{entry["stage"]}"')
        lines.append(f'    owner: "{entry["owner"]}"')
        lines.append(f'    at: "{entry.get("at", "2026-01-01")}"')
    return lines


def write_readiness_status(root: Path, scope_dir: str, **overrides: object) -> Path:
    """Write a minimal, valid ``readiness-status.yaml`` for one scope. Every
    stage defaults to ``not_started`` with no evidence/blockers; override via
    ``stage_status`` / ``stage_blocking_reasons``. Collapsed to ``**overrides``
    purely to keep the declared parameter count low -- every existing call
    site is unaffected since Python resolves keyword arguments into
    ``overrides`` transparently.

    Recognized overrides: ``table``, ``current_stage`` (default
    ``"mapping_ready"``), ``stage_status``, ``stage_blocking_reasons``,
    ``top_blocking_reasons``, ``next_action`` (default
    ``"do the next thing"``), ``approvals``.
    """
    current_stage = overrides.get("current_stage", "mapping_ready")
    stage_status = overrides.get("stage_status") or {}
    stage_blocking_reasons = overrides.get("stage_blocking_reasons") or {}
    top_blocking_reasons = overrides.get("top_blocking_reasons") or []
    next_action = overrides.get("next_action", "do the next thing")
    approvals = overrides.get("approvals")
    table_name = overrides.get("table") or scope_dir

    lines = [f'table: "{table_name}"', f'current_stage: "{current_stage}"', "stages:"]
    lines.extend(_stage_lines(stage_status, stage_blocking_reasons))
    lines.append("evidence: []")
    lines.extend(_blocking_reasons_lines(top_blocking_reasons, indent=""))
    lines.extend(_approval_lines(approvals))
    lines.append(f'next_action: "{next_action}"')

    path = root / "mappings" / scope_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_json_artifact(root: Path, scope_dir: str, filename: str, data: dict) -> Path:
    path = root / "mappings" / scope_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_source_profile(root: Path, scope_dir: str) -> Path:
    path = root / "mappings" / scope_dir / "source-profile.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# baseline source profile\n", encoding="utf-8")
    return path


def drift_artifact(**overrides: object) -> dict:
    defaults = {
        "schema_version": "1.0",
        "captured_at_revision": None,
        "live_leg_available": True,
        "class_": "no_drift",
        "measured": "0 findings",
        "owner": None,
        "items": None,
    }
    merged = {**defaults, **overrides}
    doc: dict = {
        "schema_version": merged["schema_version"],
        "captured_at_revision": merged["captured_at_revision"],
        "live_leg_available": merged["live_leg_available"],
        "class": merged["class_"],
        "measured": merged["measured"],
    }
    if merged["owner"] is not None:
        doc["owner"] = merged["owner"]
    if merged["items"] is not None:
        doc["items"] = merged["items"]
    return doc


def generic_artifact(**overrides: object) -> dict:
    """A committed artifact for a dimension with no ``live_leg_available``
    concept (everything except ``source_drift``): reuses ``drift_artifact``'s
    defaults/merge logic via delegation and drops the drift-only field,
    rather than re-declaring the same shape a second time."""
    merged_overrides = {"class_": "pass", "measured": "1 item checked", **overrides}
    doc = drift_artifact(**merged_overrides)
    doc.pop("live_leg_available", None)
    return doc
