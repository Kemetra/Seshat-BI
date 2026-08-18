"""Spec 149 -- derived run evidence for the Power BI MCP write adapter.

Evidence is proof of what ran. It is **never** an approval: writing a record
moves no readiness stage and never touches ``approvals[]`` (FR-018). A green
write is not a sign-off, before or after.

Three review findings shaped this module:

* **Redaction is two layers, not one.** ``redaction_core`` is libpq/DSN-shaped:
  its derive helpers decompose a URI or conninfo string, so for a tenant GUID or
  a ``C:\\Users\\...`` path they derive *nothing* and ``replace_fragments`` has
  nothing to replace (measured, not assumed). Those classes are covered by
  ``pbi_mcp.scan``, which is the shipped chokepoint every pbi-mcp writer already
  calls -- and which **refuses** rather than silently replacing. So: derive-then-
  replace for DSN-shaped values, then ``refuse_if_secret_shaped`` as the final
  gate before anything is emitted.
* **``blocked`` alone conflates two very different endings.** "Refused, nothing
  was touched" and "executed, state indeterminate" are both ``blocked`` in the
  five-value vocabulary, which is closed and must not grow. ``mutation_attempted``
  separates them for anyone auditing records rather than exit codes.
* **A record written only at the end is lost to a crash.** The mirrored adapter
  writes its summary at finalize, so a process killed between the mutation and
  the write leaves a mutated artifact and no evidence -- the untraceable mutation
  this feature exists to eliminate. :func:`write_intent` lands a ``deferred``
  record *before* the mutation; :func:`finalize` atomically replaces it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from seshat.dagster_adapter import OUTCOMES
from seshat.pbi_mcp.scan import refuse_if_secret_shaped
from seshat.redaction_core import (
    conninfo_component_values,
    replace_fragments,
    uri_component_values,
)

#: The fixed authority label. Never computed, never elevated, never parameterized
#: -- a label a caller could set would let a record claim more authority than the
#: run had. Matches the shipped read-only family's posture.
AUTHORITY = "derived-evidence-only"

#: What reading this record does to readiness: nothing.
READINESS_EFFECT = "none; named-human approval required"

SCHEMA_VERSION = 1
ARTIFACT_NAME = "pbi-mcp-write-evidence"
ARTIFACT_RELPATH = ".seshat/pbi-mcp-write-evidence.json"

#: The redaction placeholder.
REDACTED = "[REDACTED]"


class EvidenceRefused(RuntimeError):
    """Raised when a record cannot be emitted safely."""


def _derive_dsn_forms(text: str) -> tuple[str, ...]:
    """Every scrubbable form of a DSN-shaped secret in ``text``.

    Derive-then-replace (research R5): ``replace_fragments`` is a blunt substring
    applier, so handing it a raw secret replaces only that exact spelling and
    leaves the decomposed components behind. Both helpers are tried because a
    DSN may be URI-shaped or keyword-shaped.
    """
    forms: list[str] = []
    for derive in (uri_component_values, conninfo_component_values):
        try:
            forms.extend(derive(text))
        except Exception:  # noqa: BLE001 - a helper that cannot parse derives nothing
            continue
    # Longest first: replacing "db.example.com" before "db" avoids leaving a
    # partially-scrubbed token behind.
    return tuple(sorted({form for form in forms if form}, key=len, reverse=True))


def redact(text: str) -> str:
    """Scrub DSN-shaped values from ``text``.

    This is layer ONE only. It cannot see a tenant GUID or a user path -- those
    are not URI components -- so it must never be the last thing a writer calls.
    :func:`_emit` applies the refusing chokepoint afterwards.
    """
    return replace_fragments(text, _derive_dsn_forms(text), REDACTED)


@dataclass(frozen=True)
class RunEvidence:
    """One run's derived, score-free record.

    Carries no numeric, maturity, or confidence field of any kind (FR-017, hard
    rule #9). ``schema_version`` is deliberately NOT a field here -- it is added
    at serialization time, so no caller can mistake it for a score.
    """

    tool: str
    mode: str
    target_id: str
    operation_id: str
    timestamp: str
    outcome: str
    mutation_attempted: bool
    blockers: tuple[str, ...] = field(default_factory=tuple)
    rollback_guidance: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise EvidenceRefused(
                f"outcome {self.outcome!r} is not in the shipped vocabulary "
                f"{sorted(OUTCOMES)}"
            )
        # "pass" is a readiness verdict, not an execution outcome. It is already
        # excluded by the vocabulary above; this asserts the reason explicitly so
        # a future vocabulary edit cannot quietly admit it.
        if self.outcome == "pass":
            raise EvidenceRefused(
                "'pass' is a readiness token, never an execution outcome (hard rule #9)"
            )

    def to_payload(self) -> dict[str, object]:
        """The serializable record, with every string field redacted."""
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact": ARTIFACT_NAME,
            "authority": AUTHORITY,
            "readiness_effect": READINESS_EFFECT,
            "tool": redact(self.tool),
            "mode": self.mode,
            "target_id": redact(self.target_id),
            "operation_id": redact(self.operation_id),
            "timestamp": self.timestamp,
            "outcome": self.outcome,
            "mutation_attempted": self.mutation_attempted,
            "blockers": [redact(blocker) for blocker in self.blockers],
            "rollback_guidance": [redact(line) for line in self.rollback_guidance],
        }


def _payload_strings(payload: dict[str, object]) -> list[tuple[str, str]]:
    """Every string in the record, paired with the field it came from.

    Flattened here so the scan is a single loop rather than a nested walk.
    """
    found: list[tuple[str, str]] = []
    for key, value in payload.items():
        if isinstance(value, str):
            found.append((key, value))
        elif isinstance(value, list):
            found.extend(
                (f"{key}[{index}]", item)
                for index, item in enumerate(value)
                if isinstance(item, str)
            )
    return found


def _scan_payload_values(payload: dict[str, object]) -> None:
    """Refuse on any secret-shaped RAW field value, before JSON encoding.

    Scanning only the serialized text is a fail-open, measured not theorized:
    JSON encoding doubles each backslash, so a Windows user path arrives in the
    output with doubled separators and the scanner's user-path pattern no longer
    matches. The secret is present and invisible.

    So each value is scanned in its raw form first. The rendered text is scanned
    too (defense in depth) -- it catches anything that only becomes
    secret-shaped once fields are concatenated.
    """
    for field_name, text in _payload_strings(payload):
        refuse_if_secret_shaped(text, context=f"{ARTIFACT_RELPATH}:{field_name}")


def render(record: RunEvidence) -> str:
    """Deterministic JSON for one record, refused if secret-shaped.

    ``sort_keys`` and a fixed indent keep the output byte-comparable between
    runs, which is what lets a test assert an artifact did not change.
    """
    payload = record.to_payload()
    # Layer TWO: the shipped chokepoint. Covers tenant GUIDs, Windows and macOS
    # user paths, credential assignments and managed-database endpoints -- the
    # classes derive-then-replace cannot see. It REFUSES rather than replacing,
    # so a leak fails the run instead of shipping a half-scrubbed record.
    # Raw values FIRST (JSON escaping would hide a Windows path from the scanner).
    _scan_payload_values(payload)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return refuse_if_secret_shaped(text, context=ARTIFACT_RELPATH)


def _write_atomically(path: Path, text: str) -> None:
    """Replace ``path`` only once the full record has been rendered."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def evidence_path(repo_root: Path) -> Path:
    return Path(repo_root) / ARTIFACT_RELPATH


@dataclass(frozen=True)
class RunIdentity:
    """Who/what/when a run is about -- bundled so callers pass ONE thing.

    Six positional parameters on a writer is the shape that invites a caller to
    mis-order them; a frozen value object makes the pairing explicit and lets the
    correctness fix (a public dataclass) also satisfy the argument-count rule.
    """

    tool: str
    mode: str
    target_id: str
    operation_id: str
    timestamp: str


def write_intent(repo_root: Path, identity: RunIdentity) -> Path:
    """Record the INTENT to mutate, before the mutation runs.

    Outcome is ``deferred`` with ``mutation_attempted`` true: if the process dies
    mid-write, this record survives and names what was being attempted. Without
    it a crash between mutation and finalize leaves a changed artifact and no
    trace of who changed it.
    """
    record = RunEvidence(
        tool=identity.tool,
        mode=identity.mode,
        target_id=identity.target_id,
        operation_id=identity.operation_id,
        timestamp=identity.timestamp,
        outcome="deferred",
        mutation_attempted=True,
        blockers=("PBIMCP-EV-01",),
    )
    path = evidence_path(repo_root)
    _write_atomically(path, render(record))
    return path


def finalize(repo_root: Path, record: RunEvidence) -> Path:
    """Write the terminal record, replacing any intent record.

    Called on BOTH the success and failure paths (FR-015): exactly one record
    per run, and a refusal is a run.
    """
    path = evidence_path(repo_root)
    _write_atomically(path, render(record))
    return path


def refusal_record(
    *,
    target_id: str,
    operation_id: str,
    timestamp: str,
    blockers: tuple[str, ...],
    tool: str = "none",
    mode: str = "readonly",
) -> RunEvidence:
    """The record for a run that never reached the runtime.

    ``mutation_attempted`` is false, which is the whole point of the field: an
    auditor reading records rather than exit codes can tell this apart from a
    run that executed and left state indeterminate.
    """
    if not blockers:
        raise EvidenceRefused("a refusal record must name at least one blocker")
    return RunEvidence(
        tool=tool,
        mode=mode,
        target_id=target_id,
        operation_id=operation_id,
        timestamp=timestamp,
        outcome="blocked",
        mutation_attempted=False,
        blockers=blockers,
    )
