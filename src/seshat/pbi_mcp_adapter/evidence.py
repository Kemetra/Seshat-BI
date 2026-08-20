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
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from seshat.dagster_adapter import OUTCOMES
from seshat.pbi_mcp.scan import SECRET_PATTERNS, refuse_if_secret_shaped
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

#: The append-only history sibling (issue #657). The latest-run file above is
#: atomically REPLACED every run, so before this existed a second run destroyed
#: the first run's only trace -- including the ``deferred`` intent record that
#: exists precisely so a crashed run stays attributable.
#:
#: JSONL rather than per-run files so the two consumers that must name this
#: artifact by a FIXED literal keep working: the CLI emits a fixed repo-relative
#: path (a per-run path is absolute whenever ``--repo`` is, which leaked the
#: operator's home directory -- PR #659), and the git-cleanliness probe excludes
#: the adapter's own artifacts by exact match.
HISTORY_RELPATH = ".seshat/pbi-mcp-write-evidence.jsonl"

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
    #: (check, reason) for every validator that did NOT run. A record showing
    #: only what passed invites a reader to assume everything was checked
    #: (issue #661).
    checks_skipped: tuple[tuple[str, str], ...] = field(default_factory=tuple)

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
            "checks_skipped": [
                {"check": redact(check), "reason": redact(reason)}
                for check, reason in self.checks_skipped
            ],
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
            found.extend(_list_strings(key, value))
    return found


def _list_strings(key: str, value: list) -> list[tuple[str, str]]:
    """Strings inside a list, including those one level down in a dict.

    ``checks_skipped`` serializes as a list of ``{check, reason}`` objects, and
    a scan that only saw top-level strings would let a secret in a reason reach
    the record unscanned -- the same fail-open shape as scanning only the
    rendered JSON.
    """
    found: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            found.append((f"{key}[{index}]", item))
        elif isinstance(item, dict):
            found.extend(
                (f"{key}[{index}].{sub_key}", sub_value)
                for sub_key, sub_value in item.items()
                if isinstance(sub_value, str)
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


def scrub_secret_shaped(text: str) -> tuple[str, tuple[str, ...]]:
    """Replace every secret-shaped span in ``text``, naming what was replaced.

    PUBLIC because two surfaces need it: this module's terminal records and the
    CLI's ``--json`` verdict. :func:`redact` is layer ONE (DSN/URI components)
    and cannot see a bare tenant GUID, so a writer that calls only ``redact``
    leaks one -- measured, not assumed (PR #667).

    Uses the shipped :data:`SECRET_PATTERNS` table so this cannot drift from what
    the refusing chokepoint detects. Returns the scrubbed text and the labels that
    matched -- the labels are what makes the substitution AUDITABLE rather than a
    silent swap.
    """
    applied: list[str] = []
    scrubbed = text
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(scrubbed):
            scrubbed = pattern.sub(REDACTED, scrubbed)
            applied.append(label)
    return scrubbed, tuple(applied)


def _redact_payload(payload: dict[str, object]) -> tuple[str, ...]:
    """Scrub every string field IN PLACE; return the labels that matched.

    Only reached on the post-mutation path -- see :func:`render`.
    """
    applied: set[str] = set()

    def scrub(value: object) -> object:
        """Scrub one value, recursing through every container shape we emit.

        The container branches are delegated so this stays one decision per
        line: ``checks_skipped`` added dicts-inside-lists (issue #661), and a
        walker that grew a branch per shape would drift past the complexity
        gate exactly where it must stay easy to audit.
        """
        if isinstance(value, str):
            cleaned, labels = scrub_secret_shaped(value)
            applied.update(labels)
            return cleaned
        return _scrub_container(value, scrub)

    for key, value in list(payload.items()):
        payload[key] = scrub(value)
    return tuple(sorted(applied))


def _scrub_container(value: object, scrub: Callable[[object], object]) -> object:
    """Rebuild a container with every member scrubbed, preserving its type.

    A non-container is returned unchanged. Type is preserved rather than
    normalized to a list because the payload is compared byte-for-byte between
    runs, and a tuple silently becoming a list would change the rendered JSON.
    """
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub(item) for item in value)
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    return value


def render(record: RunEvidence) -> str:
    """Deterministic JSON for one record, refused if secret-shaped.

    ``sort_keys`` and a fixed indent keep the output byte-comparable between
    runs, which is what lets a test assert an artifact did not change.
    """
    payload = record.to_payload()
    # Layer TWO: the shipped chokepoint. Covers tenant GUIDs, Windows and macOS
    # user paths, credential assignments and managed-database endpoints -- the
    # classes derive-then-replace cannot see.
    #
    # It REFUSES rather than replacing, so a leak fails the run instead of
    # shipping a half-scrubbed record -- but ONLY where refusing is the safe
    # outcome. Once a mutation has been attempted the artifact has already
    # changed, and suppressing the terminal record leaves the operator with no
    # rollback guidance and a stale `deferred` intent: a mutated model with no
    # trace, which is the untraceable mutation this feature exists to eliminate.
    # A legitimate value can be secret-SHAPED (a backup tag whose name is a
    # GUID), so refusal there is a real outcome, not a hypothetical.
    #
    # Post-mutation therefore REDACTS and records which patterns matched, so the
    # substitution is auditable rather than silent (Codex review, PR #659).
    # Raw values FIRST (JSON escaping would hide a Windows path from the scanner).
    if record.mutation_attempted:
        applied = _redact_payload(payload)
        if applied:
            payload["redactions_applied"] = list(applied)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        scrubbed, _ = scrub_secret_shaped(text)
        return scrubbed
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


def history_path(repo_root: Path) -> Path:
    return Path(repo_root) / HISTORY_RELPATH


def _append_history(repo_root: Path, text: str) -> None:
    """Append one already-rendered record to the history log.

    ``text`` is the output of :func:`render`, so it has already been through
    BOTH redaction layers -- this adds no new redaction path of its own, which
    is what keeps a ``redact``-only leak impossible on this surface.

    The record is collapsed to a single line and opened in append mode, so each
    write lands after the existing content and never rewrites an earlier line:
    an audit log that can be rewritten is not evidence.

    This is NOT a concurrency guarantee. ``O_APPEND`` gives atomic
    seek-then-write for a single ``write(2)`` on POSIX, but the Windows CRT's
    ``_O_APPEND`` provides no cross-process atomicity -- and win32 is this
    repo's primary platform. Concurrent runs against one repo remain an open
    gap (`build-review.md`: "all runs share one evidence path"), untouched by
    this change; the sequential retention property above is what is proved.

    The path is built from FIXED constants only; no caller-supplied value
    (``target_id`` above all) ever reaches it, so there is nothing to traverse
    with.
    """
    path = history_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


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

    def with_tool(self, tool: str) -> RunIdentity:
        """The same run, attributed to a different tool.

        ``tool`` is the one field that varies per terminal state ("none" for a
        refusal, the vendor package once the runtime is reached) while the other
        four are fixed for the whole run. Returning a new frozen value keeps the
        identity immutable rather than letting a caller mutate it late.
        """
        return replace(self, tool=tool)


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
    text = render(record)
    _write_atomically(path, text)
    _append_history(repo_root, text)
    return path


def finalize(repo_root: Path, record: RunEvidence) -> Path:
    """Write the terminal record, replacing any intent record.

    Called on BOTH the success and failure paths (FR-015): exactly one record
    per run, and a refusal is a run.
    """
    path = evidence_path(repo_root)
    text = render(record)
    _write_atomically(path, text)
    _append_history(repo_root, text)
    return path


def refusal_record(identity: RunIdentity, *, blockers: tuple[str, ...]) -> RunEvidence:
    """The record for a run that never reached the runtime.

    ``mutation_attempted`` is false, which is the whole point of the field: an
    auditor reading records rather than exit codes can tell this apart from a run
    that executed and left state indeterminate.
    """
    if not blockers:
        raise EvidenceRefused("a refusal record must name at least one blocker")
    return RunEvidence(
        tool=identity.tool,
        mode=identity.mode,
        target_id=identity.target_id,
        operation_id=identity.operation_id,
        timestamp=identity.timestamp,
        outcome="blocked",
        mutation_attempted=False,
        blockers=blockers,
    )
