"""The ONE parser for ``mappings/<table>/unresolved-questions.md``.

The dbt Mapping Ready gate and the Dagster gate readers both read this mirror.
They used to carry separate parsers that disagreed: on the heading form of the
``Gate status`` line, on how many status lines are allowed, on which column
holds a row's Status, and on which tokens count as answered. One human ruling
could therefore unlock one engine and block the other. Both gates now call
:func:`parse_mirror`, so a committed mirror has exactly one meaning.

The rules, all fail-closed:

- ``Gate status`` is read from a line-anchored ``Gate status:`` marker, as a
  bullet (``- **Gate status:** `CLEARED```) or a heading (``## Gate status:
  CLEARED``). Zero markers read as ``MISSING``; more than one reads as
  ``AMBIGUOUS``. Neither is ever CLEARED.
- A question row (``| Q<id> | ... |``) is answered only when its Status cell,
  located by name from the table's header row, is exactly ``answered``. A row
  with no preceding header naming a ``Status`` column counts as open.

Stdlib-only and read-only: callers pass text they have already read (the
COMMITTED blob, never the worktree).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MISSING = "MISSING"
AMBIGUOUS = "AMBIGUOUS"

_GATE_STATUS_RE = re.compile(
    r"^[ \t]*(?:[-*>][ \t]*)?(?:#{1,6}[ \t]*)?\*{0,2}Gate status:\*{0,2}"
    r"[ \t]*`?([A-Za-z]+)`?",
    re.IGNORECASE | re.MULTILINE,
)
_QUESTION_ROW_RE = re.compile(r"^\|\s*Q[0-9A-Za-z_-]*\s*\|", re.IGNORECASE)
_ANSWERED = "answered"


@dataclass(frozen=True)
class MirrorState:
    """The parsed verdict of one unresolved-questions mirror."""

    gate_status: str  # "CLEARED" | "OPEN" | MISSING | AMBIGUOUS | verbatim token
    open_rows: int

    @property
    def cleared(self) -> bool:
        """True only for exactly one ``CLEARED`` marker and zero open rows."""
        return self.gate_status == "CLEARED" and self.open_rows == 0


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip().strip("`*_ ").strip().lower() for cell in body.split("|")]


def _gate_status(text: str) -> str:
    statuses = [match.upper() for match in _GATE_STATUS_RE.findall(text)]
    if not statuses:
        return MISSING
    if len(statuses) > 1:
        return AMBIGUOUS
    return statuses[0]


def _status_index(line: str) -> int | None:
    cells = _cells(line)
    return cells.index("status") if "status" in cells else None


def _open_rows(text: str) -> int:
    open_rows = 0
    status_index: int | None = None
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        if _QUESTION_ROW_RE.match(line.strip()):
            cells = _cells(line)
            answered = (
                status_index is not None
                and status_index < len(cells)
                and cells[status_index] == _ANSWERED
            )
            open_rows += 0 if answered else 1
            continue
        index = _status_index(line)
        if index is not None:
            status_index = index
    return open_rows


def parse_mirror(text: str) -> MirrorState:
    """Parse mirror ``text`` into its gate status and open-question count."""
    return MirrorState(gate_status=_gate_status(text), open_rows=_open_rows(text))
