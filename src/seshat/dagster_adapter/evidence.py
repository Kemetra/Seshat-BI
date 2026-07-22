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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from seshat.gitutil import git_output
from seshat.metric_contract_inventory import load_contract_inventory

from . import ASSET_ORDER, OUTCOMES
from .evidence_digest import sha256_file
from .evidence_render import (  # noqa: F401  (stable public re-exports)
    evidence_out_path,
    list_runs,
    load_run,
    render_markdown,
    validate_records,
    write_run_evidence,
)
from .redaction import redact_payload
from .run_identity import contained_path, validate_run_id

HALTED_OUTCOMES = frozenset({"failed", "skipped", "blocked", "deferred"})


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_dir(root: Path, run_id: str) -> Path:
    return contained_path(
        Path(root), ".seshat", "dagster", "runs", validate_run_id(run_id)
    )


def commit_sha(root: Path) -> str:
    """The repo state the run executed against; '0000000' when git is absent
    (a fixture repo) -- recorded honestly, never fabricated as a real sha."""
    try:
        sha = git_output(Path(root), "rev-parse", "HEAD").strip()
    except (RuntimeError, OSError):
        return "0000000"
    if sha:
        return sha
    return "0000000"


def records_sha256(path: Path) -> str:
    """Return the SHA-256 digest of the exact JSONL bytes written for a run."""
    return sha256_file(path)


def _tracked_paths(root: Path) -> set[str]:
    """Git-tracked, repository-relative POSIX paths; empty outside a Git repo."""
    try:
        raw = git_output(root, "ls-files", "-z")
    except (RuntimeError, OSError):
        return set()
    return {path for path in raw.split("\0") if path}


def _is_workspace_dirty(root: Path) -> bool:
    """Record Git dirtiness as execution context, never as an approval signal."""
    try:
        # Raw per-run records are deliberately local runtime output.  Exclude the
        # directory this run just wrote, otherwise every otherwise-clean run
        # would report itself dirty before the user changed a governed input.
        return bool(
            git_output(
                root,
                "status",
                "--porcelain",
                "--",
                ".",
                ":(exclude).seshat/dagster",
            )
        )
    except (RuntimeError, OSError):
        return False


def _contained_tracked_path(root: Path, relative: str) -> Path | None:
    """Resolve one Git path only when it remains a safe, regular input file."""
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    try:
        candidate = contained_path(root, *path.parts)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _metric_candidates(
    root: Path, tracked: set[str], tables: list[str]
) -> list[tuple[str, Path]]:
    prefixes = tuple(f"mappings/{table}/metrics/" for table in sorted(set(tables)))
    relatives = (
        relative
        for relative in tracked
        if relative.startswith(prefixes) and relative.endswith((".yaml", ".yml"))
    )
    candidates = (
        (relative, _contained_tracked_path(root, relative)) for relative in relatives
    )
    return [(relative, path) for relative, path in candidates if path is not None]


def _static_input_paths(tracked: set[str], tables: list[str]) -> set[str]:
    selected = {
        f"mappings/{table}/{filename}"
        for table in set(tables)
        for filename in ("source-map.yaml", "readiness-status.yaml")
    }
    selected.update(
        relative
        for relative in tracked
        if relative.startswith("warehouse/migrations/") and relative.endswith(".sql")
    )
    selected.update(
        relative
        for relative in tracked
        if relative.startswith("powerbi/") and relative.endswith(".tmdl")
    )
    return selected


def _digest_paths(root: Path, paths: set[str]) -> dict[str, str]:
    candidates = (
        (relative, _contained_tracked_path(root, relative))
        for relative in sorted(paths)
    )
    return {
        PurePosixPath(relative).as_posix(): records_sha256(path)
        for relative, path in candidates
        if path is not None
    }


def _input_artifact_digests(root: Path, tables: list[str]) -> dict[str, str]:
    """Digest tracked, contained inputs relevant to one governed run."""
    root = Path(root)
    tracked = _tracked_paths(root)
    metric_candidates = _metric_candidates(root, tracked, tables)
    inventory = load_contract_inventory(
        (candidate for _, candidate in metric_candidates), root
    )
    approved_paths = {
        contract.path.resolve() for contract in inventory.approved.values()
    }
    selected = _static_input_paths(tracked, tables)
    selected.update(
        relative
        for relative, candidate in metric_candidates
        if candidate.resolve() in approved_paths
    )
    return _digest_paths(root, selected & tracked)


def _write_summary_atomically(path: Path, summary: dict) -> None:
    """Replace summary only after its record digest and input binding are complete."""
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


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

    def _missing_halt_fields(self) -> bool:
        if self.outcome not in HALTED_OUTCOMES:
            return False
        return not self.blocking_reason or not self.owner

    def validate(self) -> None:
        if self.asset not in ASSET_ORDER:
            raise ValueError(f"unknown asset name: {self.asset}")
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be an execution word, got: {self.outcome}")
        if self._missing_halt_fields():
            raise ValueError(
                f"halted outcome {self.outcome} requires blocking_reason + owner"
            )


@dataclass(frozen=True)
class RunMeta:
    """When a run started, what triggered it, and how the child process exited
    (never a per-run human ruling). ``child_exit_code`` keeps the run
    fail-closed even when the orchestration child dies before writing a single
    asset record -- a crash must never finalize as ``succeeded``."""

    started: str
    trigger: str = "manual-CI"
    child_exit_code: int | None = None

    @property
    def child_failed(self) -> bool:
        return self.child_exit_code not in (None, 0)


class EvidenceWriter:
    """Append-only writer for one run's raw records (git-ignored area)."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.directory = run_dir(self.root, run_id)
        self.directory.mkdir(parents=True, exist_ok=True)

    @property
    def records_path(self) -> Path:
        return contained_path(
            self.root,
            ".seshat",
            "dagster",
            "runs",
            validate_run_id(self.run_id),
            "records.jsonl",
        )

    @property
    def summary_path(self) -> Path:
        return contained_path(
            self.root,
            ".seshat",
            "dagster",
            "runs",
            validate_run_id(self.run_id),
            "summary.json",
        )

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
    """Back-fill ``skipped`` records and atomically bind their evidence summary.

    Computes ``run_status``: failed when anything failed or blocked (the CI
    signal), else succeeded. A skipped back-fill is what the committed evidence
    table must show for a STOP-edge halt (US1/US3). The summary records the
    exact raw-record digest plus safely contained, tracked inputs; none of these
    execution facts decides a readiness state or human approval.
    """
    if not tables:
        raise ValueError("cannot finalize a Dagster run without mapped tables")
    writer = EvidenceWriter(root, run_id)
    _backfill_skipped(writer, tables)
    halted = any(row["outcome"] in {"failed", "blocked"} for row in writer.records())
    # Fail closed on the CHILD's exit too: a run whose process died before
    # recording anything must never read as succeeded (review finding, spec
    # 024 FR-013 -- the failed run status is the CI signal).
    halted = halted or meta.child_failed
    summary = {
        "run_id": run_id,
        "commit_sha": commit_sha(root),
        "started": meta.started,
        "finished": _utc_now(),
        "trigger": meta.trigger,
        "tables": sorted(tables),
        "run_status": "failed" if halted else "succeeded",
        "workspace_dirty": _is_workspace_dirty(Path(root)),
        "records_sha256": records_sha256(writer.records_path),
        "input_artifacts": _input_artifact_digests(Path(root), tables),
    }
    redacted = redact_payload(summary)
    if not isinstance(redacted, dict):  # pragma: no cover - fixed summary shape
        raise TypeError("evidence summary must remain a mapping after redaction")
    _write_summary_atomically(writer.summary_path, redacted)
    return redacted
