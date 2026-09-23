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
from seshat.rules.decision_store import decision_shape_findings

#: The only state a successful write can report. A single-member tuple by design: the
#: type cannot express "approved" for an uncommitted decision (FR-140-021), so the
#: false claim is unrepresentable rather than merely discouraged.
RECEIPT_STATES: tuple[str, ...] = ("pending_commit",)

PENDING_COMMIT = RECEIPT_STATES[0]

#: Stated on every receipt so a consumer cannot mistake a write for a ruling.
_GATE_AUTHORITY = (
    "the static gate reads committed decisions at HEAD; this write is not authority"
)

#: Recorded on the entry rather than invented per call site. Both are members of the
#: shipped STATUS_VALUES and both are terminal (not in _OPEN_STATUSES). A decline is
#: `rejected`: recording it as `approved` let a declined ruling read as authorization.
_RECORDED_STATUS = "approved"
_DECLINED_STATUS = "rejected"

#: The answers that decline what was asked. Every other answer is the ruling itself.
DECLINE_ANSWERS: frozenset[str] = frozenset({"decline"})

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


@dataclass(frozen=True)
class HumanRuling:
    """What the NAMED HUMAN supplied: who they are and what they answered.

    Its own type because these two fields carry the whole of FR-140-009. Grouping them
    makes the rule enforceable by construction -- there is no way to build a ruling
    without a signer, so no code path can record an answer nobody signed for.
    """

    signer: str
    answer: str


@dataclass(frozen=True)
class ReviewBinding:
    """What the human reviewed, and when -- the provenance of the ruling.

    Separate from `HumanRuling` because these are SERVER-supplied facts about the
    review, not the person's judgement. Keeping the two apart in the type system means
    a reader can see at a glance which half the agent may fill in.
    """

    proposal_hash: str
    workspace_revision: str
    recorded_at: str
    reviewed_scope: str


def build_entry(
    *,
    decision_id: str,
    decision_type: str,
    scope: dict[str, Any],
    ruling: HumanRuling,
    binding: ReviewBinding,
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
        "status": status_for_answer(ruling.answer),
        "scope": scope,
        "answer": ruling.answer,
        "approval": {
            "approved_by": ruling.signer,
            "approved_at": binding.recorded_at,
            "source": _SOURCE,
            "evidence": f"proposal:{binding.proposal_hash}",
            "evidence_identity": (f"workspace_revision:{binding.workspace_revision}"),
            "reviewed_scope": binding.reviewed_scope,
        },
    }


def status_for_answer(answer: str) -> str:
    """`rejected` for a decline, `approved` for any other recorded ruling."""
    return _DECLINED_STATUS if answer in DECLINE_ANSWERS else _RECORDED_STATUS


def append_decision(
    repo_root: Path | str,
    rel_path: str,
    entry: dict[str, Any],
    authority: dict[str, frozenset[str]] | None,
) -> DecisionWriteReceipt:
    """Validate through the shipped predicate, then append atomically.

    Order matters and is part of the contract: validate first, so a refusal leaves the
    file byte-identical. Raises `WriteRefused` carrying the predicate's own reason.

    Beyond approval validity, the entry must pass DS1's shape checks, must not reuse
    an id already in the store, and must not open a DS4 active-scope conflict -- each
    is a finding the gate would raise the moment a human committed this write. Only
    the NEW entry is judged: a pre-existing defect in the store is the gate's to
    report, and refusing every future write over it would wedge the write path.

    A store file that does not exist yet is created (only for a shipped store path);
    the gate still reads nothing from it until a human commits it.
    """
    if rel_path not in decision_store.STORE_PATHS:
        raise WriteRefused(f"{rel_path!r} is not a decision store path")
    valid, reason = decision_store.approval_is_valid(entry, authority)
    if not valid:
        raise WriteRefused(reason or "approval invalid")

    target = Path(repo_root).joinpath(*rel_path.split("/"))
    existing = existing_decisions(target)
    _refuse_gate_findings(entry, existing, rel_path)
    _atomic_append(target, entry)
    return DecisionWriteReceipt(
        written_path=rel_path, decision_id=str(entry.get("id", ""))
    )


def existing_decisions(path: Path) -> list[dict[str, Any]]:
    """The decisions in the working-tree store file; [] when it is absent or empty.

    A present-but-malformed file is a refusal, not []: appending to a store that does
    not parse would bury the defect rather than surface it.
    """
    if not path.exists():
        return []
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise WriteRefused(
            f"the decision store could not be read ({type(error).__name__})"
        ) from error
    if document is None:
        return []
    if not isinstance(document, dict):
        raise WriteRefused("the decision store is not a mapping")
    decisions = document.get("decisions") or []
    return [item for item in decisions if isinstance(item, dict)]


def _refuse_gate_findings(
    entry: dict[str, Any], existing: list[dict[str, Any]], rel_path: str
) -> None:
    """Refuse the entry if committing it would raise a DS1 or DS4 ERROR."""
    shape = decision_shape_findings(entry, rel_path)
    if shape:
        raise WriteRefused("; ".join(finding.message for finding in shape))
    if any(item.get("id") == entry.get("id") for item in existing):
        raise WriteRefused(f"decision id {entry.get('id')!r} is already in the store")
    new_id = entry.get("id")
    for _dtype, key, ids in decision_store.active_scope_conflicts([*existing, entry]):
        if new_id in ids:
            raise WriteRefused(
                f"an active decision already covers {key} ({', '.join(ids)}); a "
                "second ruling must supersede it"
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
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    merged = _merge_text(current, _render_fragment(entry))
    _verify_merged(merged, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    _replace_atomically(path, merged)


def _render_fragment(entry: dict[str, Any]) -> str:
    """One decision entry as an indented YAML list item."""
    fragment = yaml.safe_dump(
        [entry], sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return "".join(
        f"  {line}\n" if line.strip() else "\n" for line in fragment.splitlines()
    )


def _merge_text(existing: str, indented: str) -> str:
    """Splice the fragment in as TEXT, leaving the existing bytes untouched.

    An empty `decisions: []` is REPLACED rather than appended to: a flow-style empty
    list cannot take a block item beneath it.
    """
    body = existing.rstrip("\n")
    if "decisions:" not in existing:
        return body + "\ndecisions:\n" + indented if body else "decisions:\n" + indented
    if "decisions: []" in existing:
        return body.replace("decisions: []", "decisions:") + "\n" + indented
    return body + "\n" + indented


def _verify_merged(merged: str, entry: dict[str, Any]) -> None:
    """Re-parse before writing; raise rather than persist a malformed store."""
    parsed = yaml.safe_load(merged)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("decisions"), list):
        raise WriteRefused("append would produce a malformed decision store")
    if not parsed["decisions"] or parsed["decisions"][-1].get("id") != entry.get("id"):
        raise WriteRefused("append did not land the new entry last")


def _replace_atomically(path: Path, merged: str) -> None:
    """Stage beside the target, then one rename (atomic on POSIX and Windows)."""
    handle_fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as staged:
            staged.write(merged)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
