"""Open ``approval-request-*.md`` documents, surfaced WITHOUT a second trust path.

WHAT THIS IS -- AND EMPHATICALLY IS NOT
--------------------------------------
A table can sit at ``terminal_pass`` on every readiness stage while an owner
decision remains unanswered, because ``approval-request-*.md`` documents are
invisible to both product surfaces: ``seshat approvals`` globs only
``readiness-status.yaml`` (``approval_inbox.py``), and ``seshat next`` walks the
seven-stage spine. This module closes that gap for ``next`` (issue #517).

It does so by reading the request documents ONLY to learn *that they exist* and
which question id each names. **Nothing inside a request document is ever
trusted.** The question "is this request settled?" is answered exclusively from
``readiness-status.yaml``'s ``approvals[]``, through the same
``approval_is_shape_valid`` the gate rule and the approval inbox already use.

WHY -- the design this replaces
-------------------------------
PR #516 tried the other way and was reverted (``47a0f58``). It keyed on the
request's own ``status:`` field and corroborated it by parsing a sibling
``approval-decision-*.md``. That took three review rounds and never converged:

1. ``status: answered`` was forgeable -- a one-token edit silenced the request.
2. Corroboration accepted any nonempty ``owner``, so a ``metric_owner`` stub
   could close a ``report-owner`` request.
3. After an authority check was added, the bare role ``owner: report_owner``
   (no named person) still PASSED the substring test -- a live fail-open -- and
   presence-only field checks accepted ``date: TBD`` / ``rationale: <pending>``
   as a complete ruling.

Each round added a regex and the next round found a sharper stub, because the
design was wrong: it built a SECOND, markdown-parsed approval-trust path beside
the authoritative one this repo already validates. This module has no such path
to harden. An agent may write anything it likes into a request document; the
only way to silence a request is to record a shape-valid ``approvals[]`` entry
naming its decision record -- which requires a named human and is checked by
RS1, not here.

THE LINK BETWEEN A REQUEST AND ITS APPROVAL
-------------------------------------------
A request ``approval-request-<qid>.md`` is settled when some **shape-valid**
entry in ``approvals[]`` names ``approval-decision-<qid>.md`` in its ``note``.
That convention is already what the committed artifacts use, e.g.::

    - stage: "semantic_model_ready"
      owner: "Ahmed Shaaban (metric_owner)"
      at: "2026-07-05"
      note: "AMENDMENT ... record: approval-decision-H9-time-intel.md."

Shape-validity is delegated, never re-implemented: ``approval_is_shape_valid``
already requires a stage, a date, and a NAMED human owner, so the bare-role
bypass that defeated the reverted attempt cannot occur here.

FAIL-CLOSED POSTURE
-------------------
A request whose file cannot be read is REPORTED, never skipped (the #453
posture): an unreadable request cannot be shown to be settled, so it is
surfaced as a caveat rather than silently dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_REQUEST_GLOB = "approval-request-*.md"
_REQUEST_PREFIX = "approval-request-"
_DECISION_TEMPLATE = "approval-decision-{qid}.md"

#: Caveat kind for a request with no shape-valid approval naming its record.
OPEN_REQUEST_KIND = "open_approval_request"

#: Caveat kind for a request whose state could not be established at all.
UNPARSED_REQUEST_KIND = "unparsed_approval_request"

#: Action text when the only outstanding item is an unanswered owner decision.
#: It directs the agent to PRESENT the decision, never to answer it.
OPEN_REQUEST_ACTION = (
    "Present the open approval request(s) to the named owner -- every readiness "
    "stage passes, but an owner decision is unanswered. The agent never answers "
    "it itself."
)


def _question_id(path: Path) -> str:
    """The ``<qid>`` of ``approval-request-<qid>.md``."""
    return path.stem[len(_REQUEST_PREFIX) :]


def _settled_records(approvals: object) -> set[str]:
    """Decision-record filenames named by a SHAPE-VALID approval entry.

    Delegates shape-validity to ``readiness_status.approval_is_shape_valid`` --
    the same predicate the gate rule and the approval inbox use -- so this
    surface cannot drift from them, and so a malformed or unnamed-owner entry
    can never settle a request. An entry that fails the shape check contributes
    nothing, exactly as if it were absent.
    """
    from seshat.rules.readiness_status import approval_is_shape_valid

    if not isinstance(approvals, list):
        return set()
    records: set[str] = set()
    for item in approvals:
        if not isinstance(item, dict) or not approval_is_shape_valid(item):
            continue
        note = item.get("note")
        if isinstance(note, str):
            records.add(note)
    return records


def _is_settled(qid: str, notes: set[str]) -> bool:
    """True when a shape-valid approval names this request's decision record."""
    record = _DECISION_TEMPLATE.format(qid=qid)
    return any(record in note for note in notes)


def _readable(path: Path) -> bool:
    """Whether the request document can be read at all.

    The CONTENT is deliberately discarded -- reading proves only that the file
    exists and is decodable. Trusting anything inside it is the mistake this
    module exists to avoid.
    """
    try:
        path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False
    return True


def _open_caveat(qid: str, name: str) -> dict[str, str]:
    return {
        "kind": OPEN_REQUEST_KIND,
        "detail": (
            f"approval request {qid!r} has no shape-valid `approvals[]` entry "
            f"naming its decision record ({name}); present it to the named "
            f"owner -- the agent never answers it itself"
        ),
    }


def _unparsed_caveat(qid: str, name: str) -> dict[str, str]:
    return {
        "kind": UNPARSED_REQUEST_KIND,
        "detail": (
            f"approval request {qid!r} is unreadable ({name}); it cannot be "
            f"shown to be settled, so it is reported rather than skipped"
        ),
    }


def open_request_caveats(
    directory: Path | None, approvals: object
) -> list[dict[str, str]]:
    """Caveats for every request in ``directory`` that is not settled.

    ``directory`` is the table's ``mappings/<table>/``. ``None`` (or a path that
    does not exist) yields ``[]`` -- a caller with no directory context gets
    exactly the pre-#517 behavior rather than an error.

    A request is silent ONLY when a shape-valid ``approvals[]`` entry names its
    ``approval-decision-<qid>.md``. Everything else -- no such entry, a
    malformed entry, an unreadable request -- produces a caveat.
    """
    if directory is None or not directory.is_dir():
        return []
    notes = _settled_records(approvals)
    caveats: list[dict[str, str]] = []
    for path in sorted(directory.glob(_REQUEST_GLOB)):
        qid = _question_id(path)
        if not _readable(path):
            caveats.append(_unparsed_caveat(qid, path.name))
            continue
        if not _is_settled(qid, notes):
            caveats.append(_open_caveat(qid, path.name))
    return caveats


def has_open_request(caveats: list[dict[str, Any]]) -> bool:
    """Whether any caveat represents an outstanding owner decision.

    Both kinds count: an unreadable request is not known to be settled, so it
    must keep the table in view rather than fall through as clean.
    """
    kinds = {OPEN_REQUEST_KIND, UNPARSED_REQUEST_KIND}
    return any(c.get("kind") in kinds for c in caveats)
