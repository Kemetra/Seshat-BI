"""Append-only writes into the Decision Store (spec 140, FR-140-011/021/022/023).

Separate from `decision_store` by design. That module is the READ side the static gate
depends on, and `approval_is_valid` there is documented as "The ONE approval-validity
predicate shared by DS2 and the gate". Keeping mutation out of it means the gate's
module stays read-only by construction, and the whole mutation surface is auditable in
one file.

The security claim: **writing a decision is not granting one.** This module may append
a named human's answer to a store file in the working tree. Authority arrives only when
a human commits the file, after which the gate reads it at HEAD -- `store_files()`
selects from TRACKED paths. Nothing here runs git; committing is a human act
(FR-140-023).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from seshat import decision_store

#: The only state a successful write can report. A single-member tuple by design: the
#: type cannot express "approved" for an uncommitted decision (FR-140-021), so the
#: false claim is unrepresentable rather than merely discouraged.
RECEIPT_STATES: tuple[str, ...] = ("pending_commit",)

PENDING_COMMIT = RECEIPT_STATES[0]

#: Stated on every receipt so a consumer cannot mistake a write for a ruling.
_GATE_AUTHORITY = (
    "the static gate reads committed decisions at HEAD; this write is not authority"
)

#: Recorded on the entry rather than invented per call site. `approved` is a member of
#: the shipped STATUS_VALUES and is terminal (not in _OPEN_STATUSES).
_RECORDED_STATUS = "approved"

_SOURCE = "seshat-studio"


class WriteRefused(Exception):
    """The entry did not pass the shipped validators. Nothing was written."""


@dataclass(frozen=True)
class DecisionWriteReceipt:
    """What was written, and an explicit statement that it is not authority."""

    written_path: str
    decision_id: str
    state: str = PENDING_COMMIT
    gate_authority: str = _GATE_AUTHORITY


class _Committed(Protocol):
    """The minimum a caller must provide to read committed state.

    Narrow on purpose: this module reads HEAD through a caller-supplied accessor rather
    than shelling out to git itself, which keeps FR-140-023 structural -- there is no
    git invocation here to accidentally widen into a commit.
    """

    def file_at_head(self, relative: str) -> str | None: ...


def build_entry(
    *,
    decision_id: str,
    decision_type: str,
    scope: dict[str, Any],
    signer: str,
    answer: str,
    proposal_hash: str,
    workspace_revision: str,
    recorded_at: str,
    reviewed_scope: str,
) -> dict[str, Any]:
    """Assemble one decision entry.

    Every argument is keyword-only and required. `signer` and `answer` in particular
    have NO default anywhere in this module: FR-140-009 forbids the agent supplying,
    choosing, or inferring a named-human answer, so absent must mean a TypeError rather
    than a quietly filled blank.

    Validation is the caller's next step (`append_decision`), not this function's.
    """
    return {
        "id": decision_id,
        "decision_type": decision_type,
        "status": _RECORDED_STATUS,
        "scope": scope,
        "answer": answer,
        "approval": {
            "approved_by": signer,
            "approved_at": recorded_at,
            "source": _SOURCE,
            "evidence": f"proposal:{proposal_hash}",
            "evidence_identity": f"workspace_revision:{workspace_revision}",
            "reviewed_scope": reviewed_scope,
        },
    }


def append_decision(
    repo_root: Path | str,
    rel_path: str,
    entry: dict[str, Any],
    authority: dict[str, frozenset[str]] | None,
) -> DecisionWriteReceipt:
    """Validate through the shipped predicate, then append atomically.

    Order matters and is part of the contract: validate first, so a refusal leaves the
    file byte-identical. Raises `WriteRefused` carrying the predicate's own reason.
    """
    valid, reason = decision_store.approval_is_valid(entry, authority)
    if not valid:
        raise WriteRefused(reason or "approval invalid")

    target = Path(repo_root).joinpath(*rel_path.split("/"))
    _atomic_append(target, entry)
    return DecisionWriteReceipt(
        written_path=rel_path, decision_id=str(entry.get("id", ""))
    )


def decisions_at_head(committed: _Committed, rel_path: str) -> list[dict[str, Any]]:
    """The decisions visible in COMMITTED state, which is the only authority.

    An uncommitted append is absent here by construction: this reads HEAD, not the
    working tree. Returns [] when the path is absent at HEAD or holds no decisions.
    """
    text = committed.file_at_head(rel_path)
    if not text:
        return []
    document = yaml.safe_load(text)
    if not isinstance(document, dict):
        return []
    decisions = document.get("decisions")
    return [item for item in decisions if isinstance(item, dict)] if decisions else []


def _atomic_append(path: Path, entry: dict[str, Any]) -> None:
    """Append one decision by TEXT append, then replace the file atomically.

    Deliberately not a parse-mutate-dump round trip. `yaml.safe_load` +
    `yaml.safe_dump` would drop every comment and reflow the whole document; appending
    text leaves the existing bytes untouched by construction, which is a stronger
    guarantee than reformatting carefully. The repo is pyyaml-only by design, so a
    round-trip loader is not available anyway.

    The merged-document re-parse is the safety net that makes a text append safe:
    without it a malformed fragment could corrupt the store and only surface later, in
    the gate.
    """
    existing = path.read_text(encoding="utf-8")

    fragment = yaml.safe_dump(
        [entry], sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    indented = "".join(
        f"  {line}\n" if line.strip() else "\n" for line in fragment.splitlines()
    )

    body = existing.rstrip("\n")
    if "decisions:" in existing:
        # An empty `decisions: []` cannot take an appended block item; replace it.
        merged = (
            body.replace("decisions: []", "decisions:") + "\n" + indented
            if "decisions: []" in existing
            else body + "\n" + indented
        )
    else:
        merged = (
            body + "\ndecisions:\n" + indented if body else "decisions:\n" + indented
        )

    parsed = yaml.safe_load(merged)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("decisions"), list):
        raise WriteRefused("append would produce a malformed decision store")
    if not parsed["decisions"] or parsed["decisions"][-1].get("id") != entry.get("id"):
        raise WriteRefused("append did not land the new entry last")

    handle_fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as staged:
            staged.write(merged)
        os.replace(temporary, path)  # atomic on POSIX and Windows
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
