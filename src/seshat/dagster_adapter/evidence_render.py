"""Validation + deterministic rendering of Dagster run evidence (spec 134 US3).

The code validator mirrors ``schemas/dagster-run-evidence.schema.json`` (the
machine-readable contract) so an invalid record set is REFUSED, never rendered.
The rendered markdown follows ``templates/dagster-run-evidence.md``: run header,
per-asset results, blocked/skipped table with named owners, and the
no-authored-truth attestation. No numeric score can appear (hard rule #9).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import ASSET_ORDER, OUTCOMES
from .evidence_digest import sha256_file
from .run_identity import contained_path, validate_run_id

_HALTED = {"failed", "skipped", "blocked", "deferred"}
_TRIGGERS = {"schedule", "sensor", "manual-CI"}
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SUMMARY_KEYS = {
    "run_id",
    "commit_sha",
    "started",
    "finished",
    "trigger",
    "tables",
    "run_status",
    "workspace_dirty",
    "records_sha256",
    "input_artifacts",
}
_RECORD_KEYS = {
    "run_id",
    "asset",
    "table",
    "gate_command",
    "exit_code",
    "measured",
    "outcome",
    "blocking_reason",
    "owner",
    "ts",
}
_HUMAN_SEAM_ASSETS = {"source_map", "semantic_model", "publish_execution_evidence"}


def evidence_out_path(root: Path, run_id: str) -> Path:
    return contained_path(
        Path(root),
        "orchestration",
        "dagster",
        "run-evidence",
        f"{validate_run_id(run_id)}.md",
    )


def _score_keys(payload: object) -> list[str]:
    if isinstance(payload, dict):
        found = [str(key) for key in payload if "score" in str(key).lower()]
        return found + [key for value in payload.values() for key in _score_keys(value)]
    if isinstance(payload, list):
        return [key for item in payload for key in _score_keys(item)]
    return []


def _is_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _summary_value_errors(summary: dict) -> list[str]:
    run_id = summary.get("run_id")
    commit_sha = summary.get("commit_sha")
    records_sha = summary.get("records_sha256")
    tables = summary.get("tables")
    invalid_values = (
        (
            summary.get("run_status") not in {"succeeded", "failed"},
            "summary: run_status must be succeeded|failed",
        ),
        (
            summary.get("trigger") not in _TRIGGERS,
            f"summary: trigger must be one of {sorted(_TRIGGERS)}",
        ),
        (
            not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id),
            "summary: run_id must match the run-id schema",
        ),
        (
            not isinstance(commit_sha, str) or not _SHA_RE.fullmatch(commit_sha),
            "summary: commit_sha must be a 7-40 char hex sha",
        ),
        (
            not isinstance(tables, list)
            or any(not isinstance(table, str) or not table for table in tables),
            "summary: tables must be an array of non-empty strings",
        ),
        (
            not isinstance(summary.get("workspace_dirty"), bool),
            "summary: workspace_dirty must be boolean",
        ),
        (
            not isinstance(records_sha, str) or not _SHA256_RE.fullmatch(records_sha),
            "summary: records_sha256 must be a 64 char lowercase hex sha",
        ),
    )
    errors = [message for invalid, message in invalid_values if invalid]
    errors.extend(
        f"summary: {field} must be an offset-aware date-time"
        for field in ("started", "finished")
        if not _is_datetime(summary.get(field))
    )
    return errors


def _input_artifact_errors(value: object) -> list[str]:
    if not isinstance(value, dict):
        return ["summary: input_artifacts must be a mapping"]
    errors: list[str] = []
    for relative, digest in value.items():
        if not isinstance(relative, str):
            errors.append("summary: input_artifacts paths must be repo-relative")
            continue
        path = Path(relative)
        if not relative or path.is_absolute() or ".." in path.parts:
            errors.append("summary: input_artifacts paths must be repo-relative")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            errors.append(f"summary: input_artifacts digest invalid for {relative!r}")
    return errors


def _summary_errors(summary: object) -> list[str]:
    if not isinstance(summary, dict):
        return ["summary: must be an object"]
    errors = [
        f"summary: missing key {key}" for key in sorted(_SUMMARY_KEYS - set(summary))
    ]
    errors += [
        f"summary: unknown key {key}" for key in sorted(set(summary) - _SUMMARY_KEYS)
    ]
    errors += _summary_value_errors(summary)
    errors += _input_artifact_errors(summary.get("input_artifacts"))
    return errors


def _vocabulary_errors(label: str, row: dict) -> list[str]:
    errors: list[str] = []
    if row.get("asset") not in ASSET_ORDER:
        errors.append(f"{label}: asset must be one of the spec-024 graph names")
    if row.get("outcome") not in OUTCOMES:
        errors.append(
            f"{label}: outcome must be an execution word "
            f"({'|'.join(sorted(OUTCOMES))}), got {row.get('outcome')!r}"
        )
    return errors


def _halted_field_errors(label: str, row: dict) -> list[str]:
    if row.get("outcome") not in _HALTED:
        return []
    if row.get("blocking_reason") and row.get("owner"):
        return []
    return [f"{label}: halted outcome requires blocking_reason + owner"]


def _run_id_error(label: str, row: dict) -> list[str]:
    run_id = row.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        return [f"{label}: run_id must match the run-id schema"]
    return []


def _required_string_errors(label: str, row: dict) -> list[str]:
    return [
        f"{label}: {field} must be a non-empty string"
        for field in ("table", "gate_command")
        if not (isinstance(row.get(field), str) and row.get(field))
    ]


def _optional_string_errors(label: str, row: dict) -> list[str]:
    return [
        f"{label}: {field} must be a string or null"
        for field in ("blocking_reason", "owner")
        if row.get(field) is not None and not isinstance(row.get(field), str)
    ]


def _exit_code_error(label: str, row: dict) -> list[str]:
    exit_code = row.get("exit_code")
    if exit_code is not None and type(exit_code) is not int:
        return [f"{label}: exit_code must be an integer or null"]
    return []


def _record_shape_errors(label: str, row: dict) -> list[str]:
    errors = _run_id_error(label, row)
    errors += _required_string_errors(label, row)
    errors += _exit_code_error(label, row)
    if not isinstance(row.get("measured"), dict):
        errors.append(f"{label}: measured must be an object")
    errors += _optional_string_errors(label, row)
    if not _is_datetime(row.get("ts")):
        errors.append(f"{label}: ts must be an offset-aware date-time")
    return errors


def _record_errors(index: int, row: object) -> list[str]:
    label = f"records[{index}]"
    if not isinstance(row, dict):
        return [f"{label}: must be an object"]
    errors = [f"{label}: missing key {key}" for key in sorted(_RECORD_KEYS - set(row))]
    errors += [f"{label}: unknown key {key}" for key in sorted(set(row) - _RECORD_KEYS)]
    errors += _record_shape_errors(label, row)
    errors += _vocabulary_errors(label, row)
    errors += _halted_field_errors(label, row)
    errors += [
        f"{label}: score-like key forbidden (hard rule #9): {key}"
        for key in _score_keys(row)
    ]
    return errors


def validate_records(summary: object, records: object) -> list[str]:
    """Errors that make a record set unrenderable. Mirrors the JSON schema."""
    errors = _summary_errors(summary)
    if not isinstance(records, list):
        return [*errors, "records: must be an array"]
    if not records:
        errors.append("records: empty")
    for index, row in enumerate(records):
        errors += _record_errors(index, row)
    return errors


def load_run(root: Path, run_id: str) -> tuple[dict, list[dict]]:
    safe_run_id = validate_run_id(run_id)
    summary_path = contained_path(
        Path(root), ".seshat", "dagster", "runs", safe_run_id, "summary.json"
    )
    records_path = contained_path(
        Path(root), ".seshat", "dagster", "runs", safe_run_id, "records.jsonl"
    )
    if not summary_path.is_file() or not records_path.is_file():
        raise FileNotFoundError(
            f"run {run_id} has no summary.json/records.jsonl "
            "under .seshat/dagster/runs/"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError(f"run {run_id} summary.json must contain an object")
    if summary.get("records_sha256") != sha256_file(records_path):
        raise ValueError(f"run {run_id} records_sha256 does not match records.jsonl")
    lines = records_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return summary, records


def list_runs(root: Path) -> list[dict]:
    root = Path(root)
    runs_root = contained_path(root, ".seshat", "dagster", "runs")
    if not runs_root.is_dir():
        return []
    summaries: list[Path] = []
    for directory in sorted(runs_root.iterdir()):
        try:
            summary_path = contained_path(
                root,
                ".seshat",
                "dagster",
                "runs",
                validate_run_id(directory.name),
                "summary.json",
            )
        except ValueError:
            continue
        if summary_path.is_file():
            summaries.append(summary_path)
    return [json.loads(path.read_text(encoding="utf-8")) for path in summaries]


def _measured_cell(measured: dict) -> str:
    if not measured:
        return "-"
    return "; ".join(f"{key}: {value}" for key, value in sorted(measured.items()))


def _header_lines(summary: dict) -> list[str]:
    return [
        f"# Dagster Run Evidence -- `{summary['run_id']}`",
        "",
        "> DERIVED EVIDENCE about one orchestrated run (template: "
        "`templates/dagster-run-evidence.md`; spec 024 / F030). Outcomes are "
        "execution words, never the readiness token `pass`; this record writes "
        "no readiness `status`, no `Gate status`, no `approvals[]`, and no "
        "numeric score.",
        "",
        "## Run header",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Run id | `{summary['run_id']}` |",
        f"| Commit sha | `{summary['commit_sha']}` |",
        f"| Started | `{summary['started']}` |",
        f"| Finished | `{summary['finished']}` |",
        f"| Triggered by | `{summary['trigger']}` |",
        f"| Table(s) in scope | `{', '.join(summary['tables'])}` |",
        f"| Workspace dirty | `{str(summary['workspace_dirty']).lower()}` |",
        f"| Records SHA-256 | `{summary['records_sha256']}` |",
        f"| Input artifacts | `{len(summary['input_artifacts'])}` tracked file(s) |",
        "| Connection | READ-ONLY for validation steps; credentials from the "
        "git-ignored `.env` only (never recorded here). |",
        f"| Run status | `{summary['run_status']}` |",
        "",
    ]


def _asset_table_lines(ordered: list[dict]) -> list[str]:
    lines = [
        "## Per-asset results",
        "",
        "| # | Table | Asset | Gate command | Exit code | Measured | Outcome |",
        "|---|-------|-------|--------------|-----------|----------|---------|",
    ]
    for number, row in enumerate(ordered, start=1):
        seam = " (HUMAN SEAM)" if row["asset"] in _HUMAN_SEAM_ASSETS else ""
        exit_cell = "n/a" if row["exit_code"] is None else str(row["exit_code"])
        lines.append(
            f"| {number} | `{row['table']}` | `{row['asset']}`{seam} "
            f"| `{row['gate_command']}` | {exit_cell} "
            f"| {_measured_cell(row['measured'])} | `{row['outcome']}` |"
        )
    lines.append("")
    return lines


def _blocked_lines(ordered: list[dict]) -> list[str]:
    halted = [row for row in ordered if row["outcome"] in _HALTED]
    lines = ["## Blocked / skipped assets", ""]
    if not halted:
        return [*lines, "None -- every reached asset materialized.", ""]
    lines += [
        "| Table | Asset | Blocking reason | Named owner who can clear it |",
        "|-------|-------|-----------------|------------------------------|",
    ]
    lines += [
        f"| `{row['table']}` | `{row['asset']}` | {row['blocking_reason']} "
        f"| {row['owner']} |"
        for row in halted
    ]
    lines.append("")
    return lines


_ATTESTATION_LINES = [
    "## What this run did NOT write (the no-authored-truth attestation)",
    "",
    "- [x] No `readiness-status.yaml` stage `status` was changed by this run.",
    "- [x] No `Gate status: CLEARED` was written by this run.",
    "- [x] No `approvals[]` entry was added by this run.",
    "- [x] No metric / mapping / grain / rollup / segment / PII disposition "
    "was defined by this run.",
    "- [x] No Power BI model was published and no Power BI connection was "
    "opened by this run (the terminal asset only TRIGGERS F016 when "
    "`publish_ready = pass`, and FAILS CLOSED while F016 is absent).",
    "- [x] No numeric health / confidence / maturity value appears anywhere "
    "in this record.",
    "",
]


def render_markdown(summary: dict, records: list[dict]) -> str:
    """Deterministic committed evidence per templates/dagster-run-evidence.md."""
    ordered = sorted(
        records, key=lambda row: (row["table"], ASSET_ORDER.index(row["asset"]))
    )
    lines = (
        _header_lines(summary)
        + _asset_table_lines(ordered)
        + _blocked_lines(ordered)
        + _ATTESTATION_LINES
    )
    return "\n".join(lines)


def write_run_evidence(root: Path, run_id: str) -> Path:
    """Validate the raw records and render the committed markdown. REFUSES an
    invalid record set (never renders around a contract violation)."""
    summary, records = load_run(root, run_id)
    errors = validate_records(summary, records)
    if errors:
        detail = "; ".join(errors[:10])
        raise ValueError(f"invalid run evidence for {run_id}: {detail}")
    out_path = evidence_out_path(root, run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_markdown(summary, records), encoding="utf-8", newline="\n"
    )
    return out_path
