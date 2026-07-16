"""Raw run-evidence records (research D3).

Assets append one JSONL ``AssetRecord`` per outcome to the git-ignored
``.seshat/dagster/runs/<run-id>/records.jsonl``; ``finalize_run`` back-fills
``skipped`` records for assets a STOP edge prevented from running and writes
``summary.json``. The COMMITTED record is rendered later by
``seshat dagster evidence`` per ``templates/dagster-run-evidence.md``.

DERIVED EVIDENCE ONLY: outcomes are execution words, never the readiness token
``pass``; no numeric score field exists (hard rule #9); every string passes
through redaction before it is written (Principle IX).
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from seshat.dagster_adapter import ASSET_ORDER, OUTCOMES
from seshat.dagster_adapter.redaction import redact_payload

_HALTED = {"failed", "skipped", "blocked", "deferred"}


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


class EvidenceWriter:
    """Append-only writer for one run's raw records."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.directory = run_dir(self.root, run_id)
        self.directory.mkdir(parents=True, exist_ok=True)

    @property
    def records_path(self) -> Path:
        return self.directory / "records.jsonl"

    def record(
        self,
        *,
        asset: str,
        table: str,
        gate_command: str,
        exit_code: int | None,
        measured: dict,
        outcome: str,
        blocking_reason: str | None = None,
        owner: str | None = None,
    ) -> dict:
        if asset not in ASSET_ORDER:
            raise ValueError(f"unknown asset name: {asset}")
        if outcome not in OUTCOMES:
            raise ValueError(f"outcome must be an execution word, got: {outcome}")
        if outcome in _HALTED and not (blocking_reason and owner):
            raise ValueError(f"halted outcome {outcome} requires blocking_reason + owner")
        row = redact_payload(
            {
                "run_id": self.run_id,
                "asset": asset,
                "table": table,
                "gate_command": gate_command,
                "exit_code": exit_code,
                "measured": measured,
                "outcome": outcome,
                "blocking_reason": blocking_reason,
                "owner": owner,
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


def finalize_run(
    root: Path,
    run_id: str,
    tables: list[str],
    *,
    started: str,
    trigger: str = "manual-CI",
) -> dict:
    """Back-fill ``skipped`` records for never-ran assets and write summary.json.

    A STOP edge means downstream assets never execute, so they cannot record
    themselves; the back-fill cites the first halted upstream asset (concrete
    reason + its named owner), which is exactly what the committed evidence
    table must show (US1/US3).
    """
    writer = EvidenceWriter(root, run_id)
    existing = writer.records()
    by_table: dict[str, dict[str, dict]] = {}
    for row in existing:
        by_table.setdefault(row["table"], {})[row["asset"]] = row

    for table in tables:
        rows = by_table.get(table, {})
        halted_upstream: dict | None = None
        for asset in ASSET_ORDER:
            row = rows.get(asset)
            if row is not None:
                if row["outcome"] in {"failed", "blocked"}:
                    halted_upstream = halted_upstream or row
                continue
            if halted_upstream is None:
                # Never ran and nothing upstream halted: the run itself ended
                # early (e.g. a direct partial selection) -- still a skip.
                reason = "not selected / run ended before this asset"
                owner = "orchestration owner"
            else:
                reason = (
                    f"upstream STOP edge: {halted_upstream['asset']} "
                    f"{halted_upstream['outcome']} -- {halted_upstream['blocking_reason']}"
                )
                owner = halted_upstream["owner"] or "orchestration owner"
            writer.record(
                asset=asset,
                table=table,
                gate_command="n/a -- did not run",
                exit_code=None,
                measured={},
                outcome="skipped",
                blocking_reason=reason,
                owner=owner,
            )

    final_records = writer.records()
    run_status = (
        "failed"
        if any(row["outcome"] in {"failed", "blocked"} for row in final_records)
        else "succeeded"
    )
    summary = {
        "run_id": run_id,
        "commit_sha": commit_sha(root),
        "started": started,
        "finished": _utc_now(),
        "trigger": trigger,
        "tables": sorted(tables),
        "run_status": run_status,
    }
    (writer.directory / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
