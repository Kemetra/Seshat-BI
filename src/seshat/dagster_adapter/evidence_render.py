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
from pathlib import Path

from . import ASSET_ORDER, OUTCOMES

_HALTED = {"failed", "skipped", "blocked", "deferred"}
_TRIGGERS = {"schedule", "sensor", "manual-CI"}
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_SUMMARY_KEYS = {
    "run_id",
    "commit_sha",
    "started",
    "finished",
    "trigger",
    "tables",
    "run_status",
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
    return Path(root) / "orchestration" / "dagster" / "run-evidence" / f"{run_id}.md"


def _score_keys(payload: object) -> list[str]:
    if isinstance(payload, dict):
        found = [str(key) for key in payload if "score" in str(key).lower()]
        return found + [key for value in payload.values() for key in _score_keys(value)]
    if isinstance(payload, list):
        return [key for item in payload for key in _score_keys(item)]
    return []


def _summary_errors(summary: dict) -> list[str]:
    errors = [
        f"summary: missing key {key}" for key in sorted(_SUMMARY_KEYS - set(summary))
    ]
    errors += [
        f"summary: unknown key {key}" for key in sorted(set(summary) - _SUMMARY_KEYS)
    ]
    if summary.get("run_status") not in {"succeeded", "failed"}:
        errors.append(
            "summary: run_status must be succeeded|failed, "
            f"got {summary.get('run_status')!r}"
        )
    if summary.get("trigger") not in _TRIGGERS:
        errors.append(f"summary: trigger must be one of {sorted(_TRIGGERS)}")
    if not _SHA_RE.match(str(summary.get("commit_sha", ""))):
        errors.append("summary: commit_sha must be a 7-40 char hex sha")
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


def _record_errors(index: int, row: dict) -> list[str]:
    label = f"records[{index}]"
    errors = [f"{label}: missing key {key}" for key in sorted(_RECORD_KEYS - set(row))]
    errors += [f"{label}: unknown key {key}" for key in sorted(set(row) - _RECORD_KEYS)]
    errors += _vocabulary_errors(label, row)
    errors += _halted_field_errors(label, row)
    errors += [
        f"{label}: score-like key forbidden (hard rule #9): {key}"
        for key in _score_keys(row)
    ]
    return errors


def validate_records(summary: dict, records: list[dict]) -> list[str]:
    """Errors that make a record set unrenderable. Mirrors the JSON schema."""
    errors = _summary_errors(summary)
    if not records:
        errors.append("records: empty")
    for index, row in enumerate(records):
        errors += _record_errors(index, row)
    return errors


def load_run(root: Path, run_id: str) -> tuple[dict, list[dict]]:
    directory = Path(root) / ".seshat" / "dagster" / "runs" / run_id
    summary_path = directory / "summary.json"
    records_path = directory / "records.jsonl"
    if not summary_path.is_file() or not records_path.is_file():
        raise FileNotFoundError(
            f"run {run_id} has no summary.json/records.jsonl "
            "under .seshat/dagster/runs/"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    lines = records_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return summary, records


def list_runs(root: Path) -> list[dict]:
    runs_root = Path(root) / ".seshat" / "dagster" / "runs"
    if not runs_root.is_dir():
        return []
    summaries = (
        directory / "summary.json" for directory in sorted(runs_root.iterdir())
    )
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in summaries
        if path.is_file()
    ]


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
