"""Dagster run evidence: raw records and run finalization.

ONE implementation for both environments (research D3/D4): the orchestration
package's assets append records through :class:`EvidenceWriter`; the parent
``seshat dagster`` CLI finalizes a run and renders the committed markdown --
neither side imports dagster here (stdlib + PyYAML only). Validation and
rendering live in :mod:`.evidence_render` and are re-exported here so the
public import path is stable.

DERIVED EVIDENCE ONLY: outcomes are execution words, never the readiness token
``pass``; no numeric score key is accepted anywhere (hard rule #9); every
string passes redaction before it is written (Principle IX).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import ASSET_ORDER, OUTCOMES
from .evidence_render import (  # noqa: F401  (stable public re-exports)
    evidence_out_path,
    list_runs,
    load_run,
    render_markdown,
    validate_records,
    write_run_evidence,
)
from .redaction import redact_payload

HALTED_OUTCOMES = frozenset({"failed", "skipped", "blocked", "deferred"})


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_dir(root: Path, run_id: str) -> Path:
    return Path(root) / ".seshat" / "dagster" / "runs" / run_id


def commit_sha(root: Path) -> str:
    """The repo state the run executed against; '0000000' when git is absent
    (a fixture repo) -- recorded honestly, never fabricated as a real sha."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        sha = proc.stdout.strip()
        if proc.returncode == 0 and sha:
            return sha
    except OSError:
        pass
    return "0000000"


@dataclass(frozen=True)
class AssetOutcome:
    """One asset's execution outcome -- the unit every record call carries."""

    asset: str
    table: str
    gate_command: str
    exit_code: int | None
    measured: dict
    outcome: str
    blocking_reason: str | None = None
    owner: str | None = None

    def validate(self) -> None:
        if self.asset not in ASSET_ORDER:
            raise ValueError(f"unknown asset name: {self.asset}")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be an execution word, got: {self.outcome}")
        halted = self.outcome in HALTED_OUTCOMES
        if halted and not (self.blocking_reason and self.owner):
            raise ValueError(
                f"halted outcome {self.outcome} requires blocking_reason + owner"
            )


@dataclass(frozen=True)
class RunMeta:
    """When a run started and what triggered it (never a per-run human ruling)."""

    started: str
    trigger: str = "manual-CI"


class EvidenceWriter:
    """Append-only writer for one run's raw records (git-ignored area)."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.directory = run_dir(self.root, run_id)
        self.directory.mkdir(parents=True, exist_ok=True)

    @property
    def records_path(self) -> Path:
        return self.directory / "records.jsonl"

    def record(self, outcome: AssetOutcome) -> dict:
        outcome.validate()
        row = redact_payload(
            {
                "run_id": self.run_id,
                "asset": outcome.asset,
                "table": outcome.table,
                "gate_command": outcome.gate_command,
                "exit_code": outcome.exit_code,
                "measured": outcome.measured,
                "outcome": outcome.outcome,
                "blocking_reason": outcome.blocking_reason,
                "owner": outcome.owner,
                "ts": _utc_now(),
            }
        )
        with self.records_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def records(self) -> list[dict]:
        if not self.records_path.is_file():
            return []
        return [
            json.loads(line)
            for line in self.records_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


def _skip_outcome(asset: str, table: str, halted_upstream: dict | None) -> AssetOutcome:
    """The back-filled ``skipped`` record for an asset a STOP edge prevented
    from running -- cites the first halted upstream asset + its named owner."""
    if halted_upstream is None:
        reason = "not selected / run ended before this asset"
        owner = "orchestration owner"
    else:
        reason = (
            f"upstream STOP edge: {halted_upstream['asset']} "
            f"{halted_upstream['outcome']} -- "
            f"{halted_upstream['blocking_reason']}"
        )
        owner = halted_upstream["owner"] or "orchestration owner"
    return AssetOutcome(
        asset=asset,
        table=table,
        gate_command="n/a -- did not run",
        exit_code=None,
        measured={},
        outcome="skipped",
        blocking_reason=reason,
        owner=owner,
    )


def _backfill_skipped(writer: EvidenceWriter, tables: list[str]) -> None:
    by_table: dict[str, dict[str, dict]] = {}
    for row in writer.records():
        by_table.setdefault(row["table"], {})[row["asset"]] = row
    for table in tables:
        rows = by_table.get(table, {})
        halted_upstream: dict | None = None
        for asset in ASSET_ORDER:
            row = rows.get(asset)
            if row is None:
                writer.record(_skip_outcome(asset, table, halted_upstream))
            elif row["outcome"] in {"failed", "blocked"}:
                halted_upstream = halted_upstream or row


def finalize_run(root: Path, run_id: str, tables: list[str], meta: RunMeta) -> dict:
    """Back-fill ``skipped`` records for never-ran assets and write summary.json.

    Computes ``run_status``: failed when anything failed or blocked (the CI
    signal), else succeeded. A skipped back-fill is what the committed evidence
    table must show for a STOP-edge halt (US1/US3).
    """
    writer = EvidenceWriter(root, run_id)
    _backfill_skipped(writer, tables)
    halted = any(row["outcome"] in {"failed", "blocked"} for row in writer.records())
    summary = {
        "run_id": run_id,
        "commit_sha": commit_sha(root),
        "started": meta.started,
        "finished": _utc_now(),
        "trigger": meta.trigger,
        "tables": sorted(tables),
        "run_status": "failed" if halted else "succeeded",
    }
    (writer.directory / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
