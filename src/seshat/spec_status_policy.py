"""The Seshat-owned policy for a spec's ``**Status**:`` line (ADR 0019).

ADR 0019 closed the spec status vocabulary to four values and required each to
carry its evidence. It chose documentation-and-test enforcement rather than a
shipped rule, and the consequence was that the policy came to live inside
``.specify/templates/spec-template.md`` -- a file upstream Spec Kit owns and
regenerates. Any ordinary re-init or upgrade silently reverted a ratified
governance decision, and the only code declaration of the vocabulary sat inside
the test that read that template to learn what to check.

This module is the replacement (spec 151): Spec Kit owns Spec Kit, Seshat owns
Seshat governance. It is the ONE executable authority for what a Seshat spec
status may say.

WHAT THIS MODULE IS NOT
-----------------------
Not a state machine: it does not model transitions between values, does not
decide whether ``ratified -> implemented`` is permitted, and tracks no history.
It validates one line against a vocabulary and that value's evidence rule.

Not an approval authority: whether a human really ratified a spec remains the
git-blame provenance check in ``.claude/workflows/implement.js``. This module
describes the SHAPE of a ratified line; it never certifies who wrote it.

Not a readiness surface: it has nothing to do with the seven-stage spine and
must not import it.

Not a template reader: deriving the expectation from the artifact under
validation is precisely the circularity spec 151 removes (FR-004). This module
opens no Spec Kit file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: The closed vocabulary. ADR 0019, ratified 2026-07-30.
VOCABULARY: tuple[str, ...] = ("draft", "ratified", "implemented", "superseded")

#: The line a spec's status is authored on. A ``**Status history**:`` line is a
#: DIFFERENT line and is deliberately not matched here -- conflating the two is
#: how a widened grammar starts refusing correctly ratified specs.
_STATUS_PREFIX = "**Status**:"

_HISTORY_PREFIX = "**Status history**:"

#: `ratified -- Name, YYYY-MM-DD`
#:
#: ``\S`` before the rest of the name is load-bearing: with a plain ``.+?`` the
#: ``\s+`` after ``--`` backtracks, so ``ratified --  , 2026-08-08`` captured a
#: single space as the ratifier and satisfied the "named human" requirement with
#: no name at all (Codex P2 on PR #600).
_RATIFIED = re.compile(
    r"^ratified\s+--\s+(?P<who>\S.*?),\s*(?P<when>\d{4}-\d{2}-\d{2})\s*$"
)

#: `implemented -- artifact `path``
_IMPLEMENTED = re.compile(r"^implemented\s+--\s+artifact\s+`(?P<artifact>[^`]+)`\s*$")

#: `superseded -- by spec NNN` (free-form tail; it must merely name something)
_SUPERSEDED = re.compile(r"^superseded\s+--\s+\S+.*$")


class StatusPolicyError(ValueError):
    """Raised when a line cannot be handled without guessing at intent."""


@dataclass(frozen=True)
class Verdict:
    """Whether one status line satisfies the policy, and why not if it does not."""

    ok: bool
    value: str | None = None
    detail: str = ""


def is_vocabulary_value(value: str) -> bool:
    """Whether ``value`` is one of the four canonical values.

    Case-sensitive on purpose. Capital ``Draft`` is NOT a vocabulary value: the
    upstream-seeded form is handled by :func:`normalize_status_line` at scaffold
    time, never by an exception here. FR-006 carries no exception list.
    """
    return value in VOCABULARY


def canonical_case(value: str) -> str:
    """The canonical spelling of a vocabulary value."""
    return value.strip().lower()


def _evidence_verdict(rest: str, value: str) -> Verdict:
    """Whether the tail of the line carries the evidence this value requires."""
    if value == "draft":
        return Verdict(True, value)
    if value == "ratified":
        if _RATIFIED.match(rest):
            return Verdict(True, value)
        return Verdict(
            False,
            value,
            "`ratified` requires a named human and a date, "
            "e.g. `**Status**: ratified -- Person Name, YYYY-MM-DD`",
        )
    if value == "implemented":
        if _IMPLEMENTED.match(rest):
            return Verdict(True, value)
        return Verdict(
            False,
            value,
            "`implemented` requires a tracked artifact, "
            "e.g. ``**Status**: implemented -- artifact `src/seshat/foo.py```",
        )
    if _SUPERSEDED.match(rest):
        return Verdict(True, value)
    return Verdict(
        False,
        value,
        "`superseded` requires the superseding spec id, "
        "e.g. `**Status**: superseded -- by spec 152`",
    )


def validate_status_line(line: str) -> Verdict:
    """Validate one authored ``**Status**:`` line.

    Fails closed: an empty line, a line without the prefix, and a line whose
    value is outside the vocabulary are all defects, never a pass.
    """
    stripped = line.strip()
    if not stripped.startswith(_STATUS_PREFIX):
        return Verdict(False, None, f"line does not begin with `{_STATUS_PREFIX}`")

    rest = stripped[len(_STATUS_PREFIX) :].strip()
    if not rest:
        return Verdict(False, None, f"`{_STATUS_PREFIX}` carries no value")

    value = rest.split()[0]
    if not is_vocabulary_value(value):
        return Verdict(
            False,
            None,
            f"{value!r} is outside the closed vocabulary "
            f"({', '.join(VOCABULARY)}); see ADR 0019",
        )
    return _evidence_verdict(rest, value)


def status_line_of(text: str) -> str | None:
    """The authored status line in ``text``, or ``None``.

    A ``**Status history**:`` line is never returned: it records a PREVIOUS
    value and is not the spec's current status.
    """
    for line in text.splitlines():
        if line.startswith(_HISTORY_PREFIX):
            continue
        if line.startswith(_STATUS_PREFIX):
            return line
    return None


def validate_spec_file(path: Path) -> Verdict:
    """Validate the status line of a spec file, reporting read failure."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return Verdict(False, None, f"spec could not be read: {exc}")

    line = status_line_of(text)
    if line is None:
        return Verdict(False, None, f"spec carries no `{_STATUS_PREFIX}` line")
    return validate_status_line(line)


def normalize_status_line(line: str) -> str:
    """Return ``line`` with its status value in canonical case.

    This exists for exactly one reason (FR-025): the upstream Spec Kit template
    seeds ``**Status**: Draft``, and Seshat must not modify that template to
    change what it seeds. A Seshat-owned post-scaffold step normalizes the
    OUTPUT instead. It reads whatever it finds rather than restoring a known
    string, so a future upstream change to the seeded value does not break it.

    Idempotent. A ``**Status history**:`` line is returned untouched. Fails
    closed (FR-025a): a value that is not a case variant of a vocabulary value
    raises rather than being silently rewritten into something plausible.
    """
    stripped = line.strip()
    if stripped.startswith(_HISTORY_PREFIX):
        return line
    if not stripped.startswith(_STATUS_PREFIX):
        raise StatusPolicyError(f"not a status line: {line!r}")

    rest = stripped[len(_STATUS_PREFIX) :].strip()
    if not rest:
        raise StatusPolicyError("status line carries no value")

    head, _, tail = rest.partition(" ")
    lowered = canonical_case(head)
    if not is_vocabulary_value(lowered):
        raise StatusPolicyError(
            f"{head!r} is not a case variant of a vocabulary value "
            f"({', '.join(VOCABULARY)}); refusing to guess"
        )
    normalized = f"{_STATUS_PREFIX} {lowered}"
    return f"{normalized} {tail.strip()}" if tail.strip() else normalized


def normalize_spec_file(path: Path) -> bool:
    """Normalize a scaffolded spec's status line ON DISK. Returns whether it changed.

    This is the production seam for FR-025 and the reason
    :func:`normalize_status_line` exists at all: ``create-new-feature.ps1``
    copies the upstream template verbatim, so a freshly scaffolded spec carries
    ``**Status**: Draft`` -- capital, and outside the closed vocabulary. Seshat
    must not edit the upstream template to change what it seeds, so the fix acts
    on the scaffolded OUTPUT instead.

    Idempotent: normalizing an already-canonical file rewrites nothing and
    returns ``False``. Fails closed: an unreadable file, a file with no status
    line, or a value that is not a case variant of a vocabulary value raises
    rather than leaving the spec in an unknown state (FR-025a).
    """
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise StatusPolicyError(f"spec could not be read: {exc}") from exc

    line = status_line_of(text)
    if line is None:
        raise StatusPolicyError(f"spec carries no `{_STATUS_PREFIX}` line: {target}")

    normalized = normalize_status_line(line)
    if normalized == line:
        return False

    target.write_text(text.replace(line, normalized, 1), encoding="utf-8")
    return True
