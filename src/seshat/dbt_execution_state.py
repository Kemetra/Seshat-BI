"""Read the committed dbt execution evidence for one table (spec 150, Phase 7).

The dbt adapter parses dbt's own ``manifest.json``/``run_results.json``,
normalizes them into ``RunEvidence``, and commits a sanitized, schema-validated
record to ``mappings/<table>/dbt-evidence/<invocation_id>.json``. Until this
module, nothing read that record back: the evidence was produced for nobody.

This is the dbt analogue of ``portfolio_watch.live_validation_state`` -- a pure
classifier that opens committed files and returns a bare state string.

WHAT THIS MODULE MUST NEVER DO
------------------------------
It never reads ``readiness-status.yaml``, never imports the readiness spine, and
never returns a readiness four-status token other than ``blocked`` (which the
execution vocabulary independently owns). Execution success is EVIDENCE; it is
not readiness authority, and a stage's approval remains a named human action.
That guarantee is structural here: this module cannot reach readiness state, so
it cannot change it.

It also never opens a database, never invokes dbt, and never echoes arbitrary
record content -- only the named envelope fields below, which is what makes
read-time re-redaction unnecessary (records are already sanitized at write time
by ``seshat.dbt.redaction.sanitize`` and are schema-closed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from seshat.dbt import OUTCOME_TO_EXECUTION, UNKNOWN_EXECUTION

# No dbt evidence directory, or no records in it. A table that has never had a
# governed dbt build is NOT defective, so this state is reported and carries no
# caveat.
STATE_ABSENT = "absent"

# The selected record parsed and the build succeeded.
STATE_BUILT = "built"

# The selected record parsed and the build failed.
STATE_FAILED = "failed"

# The selected record parsed and the build was blocked, unavailable, or reported
# an outcome this Seshat version does not recognize. Unknown is never a pass.
STATE_BLOCKED = "blocked"

# The selected record is not valid JSON, or is missing the envelope fields this
# reader names. A defect to be surfaced -- never silence, never a pass.
STATE_UNREADABLE = "unreadable"

_CAVEAT_STATES = (STATE_FAILED, STATE_BLOCKED, STATE_UNREADABLE)

# Only these fields are read, and only these are ever echoed outward.
_REQUIRED_FIELDS = ("invocation_id", "outcome", "readiness_effect")


@dataclass(frozen=True)
class DbtExecutionEvidence:
    """What the governance surface is allowed to say about a dbt build."""

    state: str
    invocation_id: str | None = None
    readiness_effect: str | None = None
    evidence_path: str | None = None
    blocking_reasons: tuple[str, ...] = ()

    @property
    def warrants_caveat(self) -> bool:
        """A clean build and an absent build are both quiet; the rest are not."""
        return self.state in _CAVEAT_STATES


def _evidence_directory(repo_root: Path, mapping_scope: str) -> Path:
    return repo_root / "mappings" / mapping_scope / "dbt-evidence"


def _latest_record(directory: Path) -> Path | None:
    """The newest record by filename sort.

    ``invocation_id`` is locked to ``^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$``, whose
    zero-padded timestamp prefix makes lexicographic order chronological. Sorting
    on NAMES rather than parsed content is deliberate: a corrupt record must not
    be skipped in favour of an older, more flattering one, so selection happens
    before any parse can fail.
    """
    try:
        candidates = sorted(
            path for path in directory.iterdir() if path.suffix == ".json"
        )
    except OSError:
        return None
    return candidates[-1] if candidates else None


def _blocking_reasons(payload: object) -> tuple[str, ...]:
    """Flatten the record's blocking reasons to plain strings.

    Reasons are written as mappings by the dbt adapter; they are already
    sanitized at write time, so this only renders them.
    """
    if not isinstance(payload, list):
        return ()
    reasons: list[str] = []
    for entry in payload:
        if isinstance(entry, dict):
            reasons.append("; ".join(f"{key}={value}" for key, value in entry.items()))
        elif isinstance(entry, str):
            reasons.append(entry)
    return tuple(reasons)


def read_dbt_execution_evidence(
    repo_root: Path | str, mapping_scope: str
) -> DbtExecutionEvidence:
    """Classify the latest committed dbt evidence record; never opens a database."""
    root = Path(repo_root).resolve()
    directory = _evidence_directory(root, mapping_scope)
    if not directory.is_dir():
        return DbtExecutionEvidence(state=STATE_ABSENT)

    record_path = _latest_record(directory)
    if record_path is None:
        return DbtExecutionEvidence(state=STATE_ABSENT)

    relative = record_path.relative_to(root).as_posix()
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return DbtExecutionEvidence(
            state=STATE_UNREADABLE,
            evidence_path=relative,
            blocking_reasons=(f"dbt evidence record is not readable: {relative}",),
        )

    if not isinstance(payload, dict) or any(
        field not in payload for field in _REQUIRED_FIELDS
    ):
        return DbtExecutionEvidence(
            state=STATE_UNREADABLE,
            evidence_path=relative,
            blocking_reasons=(
                f"dbt evidence record is missing required fields: {relative}",
            ),
        )

    outcome = payload.get("outcome")
    state = OUTCOME_TO_EXECUTION.get(
        outcome if isinstance(outcome, str) else "", UNKNOWN_EXECUTION
    )
    invocation_id = payload.get("invocation_id")
    readiness_effect = payload.get("readiness_effect")
    return DbtExecutionEvidence(
        state=state,
        invocation_id=invocation_id if isinstance(invocation_id, str) else None,
        readiness_effect=(
            readiness_effect if isinstance(readiness_effect, str) else None
        ),
        evidence_path=relative,
        blocking_reasons=_blocking_reasons(payload.get("blocking_reasons")),
    )


def dbt_execution_state(repo_root: Path | str, mapping_scope: str) -> str:
    """The bare state string, mirroring ``live_validation_state``'s shape."""
    return read_dbt_execution_evidence(repo_root, mapping_scope).state
