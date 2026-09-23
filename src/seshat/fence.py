"""SESHAT-KIT fenced-region reader/writer (feature 070).

Writes generated orientation prose into a constitution-governed file (AGENTS.md /
CLAUDE.md) WITHOUT ever touching content outside a delimited fence. This is the
mechanical half of `retail init`'s substrate write; it does NO DB, NO network, NO
profiling, NO prompt/menu (Principle VIII; stdlib-only).

Contract: ``specs/070-retail-init-bootstrap/contracts/fence.contract.md``.

- F1/F2: only the bytes between the two markers change; every byte outside is
  identical before/after.
- F3: idempotent -- exactly one fenced region; an identical body is a no-op.
- F4: if the markers are absent, append ONE fresh fenced block at end of file; if
  the file is malformed (a lone START or END, or END-before-START), STOP and report
  -- never rewrite the file.
- F5: the ``SESHAT-KIT`` markers never collide with the existing ``SPECKIT`` fence.

A NEW fence in a file with no line-ending history is written UTF-8 without BOM
with ``\\n`` line endings (Principle IX). An existing file keeps its own BOM and
its dominant line ending: the fenced block is spliced into the original text
with that newline, so F1/F2 hold for CRLF and BOM-prefixed files too (a
``core.autocrlf`` checkout of AGENTS.md/CLAUDE.md is CRLF on Windows).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

START = "<!-- SESHAT-KIT START -->"
END = "<!-- SESHAT-KIT END -->"


@dataclass(frozen=True)
class FenceResult:
    """Outcome of a ``write_fence`` call.

    ``changed`` is False when the fenced body already matched (idempotent no-op).
    ``stopped_reason`` is set (and ``ok`` False) when placement was unsafe and the
    file was left untouched.
    """

    path: Path
    changed: bool = False
    inserted: bool = False
    stopped_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.stopped_reason is None


_BOM = "﻿"


def _render_block(body: str, newline: str = "\n") -> str:
    """The full fenced block for ``body`` (markers on their own lines)."""
    lines = body.replace("\r\n", "\n").replace("\n", newline)
    return f"{START}{newline}{lines}{newline}{END}"


def _read_exact(path: Path) -> tuple[str, str, str]:
    """``(bom, text, newline)`` of ``path`` with every character preserved.

    Decoded from bytes, NOT ``read_text``: universal-newline reading silently
    turns CRLF into LF, so writing the text back rewrote every line outside the
    fence. ``newline`` is the file's dominant line ending (LF when it has none).
    """
    text = path.read_bytes().decode("utf-8")
    bom = _BOM if text.startswith(_BOM) else ""
    text = text[len(bom) :]
    crlf = text.count("\r\n")
    newline = "\r\n" if crlf and crlf >= text.count("\n") - crlf else "\n"
    return bom, text, newline


def _locate(text: str) -> tuple[int, int] | None | str:
    """Locate the fenced region in ``text``.

    Returns ``(start_index, end_index_past_END)`` for a well-formed single fence,
    ``None`` when NO markers are present, or a string error when the markers are
    malformed (lone marker, END before START, or more than one of either).
    """
    n_start = text.count(START)
    n_end = text.count(END)
    if n_start == 0 and n_end == 0:
        return None
    if n_start != 1 or n_end != 1:
        return (
            f"malformed SESHAT-KIT fence: found {n_start} START and {n_end} END "
            "marker(s); expected exactly one of each"
        )
    start = text.index(START)
    end = text.index(END)
    if end < start:
        return "malformed SESHAT-KIT fence: END marker precedes START marker"
    return (start, end + len(END))


def write_fence(path: Path | str, body: str) -> FenceResult:
    """Write ``body`` into the SESHAT-KIT fence of ``path`` (fence-only).

    Replaces an existing fenced body, or appends one fresh fence if none exists.
    STOPS (no write) on a malformed fence. Idempotent when the body is unchanged.
    """
    path = Path(path)
    bom, text, newline = _read_exact(path)

    located = _locate(text)
    if isinstance(located, str):
        return FenceResult(path=path, stopped_reason=located)

    block = _render_block(body, newline)

    if located is None:
        # F4: no markers -> append one fresh fenced block at end of file.
        sep = "" if text == "" or text.endswith("\n") else newline
        new_text = f"{text}{sep}{block}{newline}"
        inserted = True
    else:
        start, end = located
        existing = text[start:end]
        if existing == block:
            # F3: identical body -> idempotent no-op (no write, no mtime churn).
            return FenceResult(path=path, changed=False, inserted=False)
        new_text = text[:start] + block + text[end:]
        inserted = False

    _write_exact(path, bom + new_text)
    return FenceResult(path=path, changed=True, inserted=inserted)


def read_fence_body(path: Path | str) -> str | None:
    """Return the current fenced body of ``path``, or None if there is no fence.

    Raises no error on a malformed fence -- returns None (the caller re-runs
    ``write_fence`` which reports the malformation).
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    located = _locate(text)
    if not isinstance(located, tuple):
        return None
    start, end = located
    block = text[start:end]
    inner = block[len(START) : -len(END)]
    return inner.strip("\n")


def _write_exact(path: Path, text: str) -> None:
    """Write ``text`` as UTF-8 with NO newline translation.

    ``text`` already carries the file's own BOM and line endings; translating
    here would undo the preservation :func:`_read_exact` exists for.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
