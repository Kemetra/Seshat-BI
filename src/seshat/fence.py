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

All writes are UTF-8 without BOM, ``\\n`` line endings (Windows-stable, Principle IX).
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


def _render_block(body: str) -> str:
    """The full fenced block for ``body`` (markers on their own lines)."""
    return f"{START}\n{body}\n{END}"


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
    text = path.read_text(encoding="utf-8-sig")  # tolerate a pre-existing BOM on read

    located = _locate(text)
    if isinstance(located, str):
        return FenceResult(path=path, stopped_reason=located)

    block = _render_block(body)

    if located is None:
        # F4: no markers -> append one fresh fenced block at end of file.
        sep = "" if text == "" or text.endswith("\n") else "\n"
        new_text = f"{text}{sep}{block}\n"
        inserted = True
    else:
        start, end = located
        existing = text[start:end]
        if existing == block:
            # F3: identical body -> idempotent no-op (no write, no mtime churn).
            return FenceResult(path=path, changed=False, inserted=False)
        new_text = text[:start] + block + text[end:]
        inserted = False

    _write_text(path, new_text)
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


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 without BOM and ``\\n`` line endings (Windows-stable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
