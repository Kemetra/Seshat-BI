"""Studio boundary redaction: session material and absolute paths (FR-026).

Applied to errors, diagnostics, logs, and browser responses. Two secret classes,
handled differently on purpose:

* **Session material** (bootstrap tokens, cookie values) -- high-entropy, matched
  exactly, replaced wholesale. Nothing useful is lost by removing them.
* **Absolute filesystem paths** -- rewritten to a workspace-relative reference when
  they are contained by the pinned root, so the reader still learns WHICH file is at
  fault without learning the operator's directory layout. A path outside the root
  has no safe relative form and becomes a label.

**Why this is not `seshat.redaction_core`.** That module is the hardened DSN
decomposition -- libpq conninfo, URI components, connection secrets -- and the five
existing boundary redactors delegate to it precisely so nobody hand-rolls a second
copy. Studio's secrets are a DIFFERENT class (session tokens and paths, no DSN), so
this module does not duplicate that logic; it borrows only the
``replace_fragments`` primitive for the actual substitution.

**Over-redaction is a defect.** ``seshat/dbt/redaction.py`` records the incident:
treating every configured value as a secret rewrote innocent substrings, so the
English word "require" corrupted the governed const "named-human approval required"
and a bare port number matched unrelated digits. Studio exists to project truth, so
a redactor that mangles evidence defeats the feature. Hence the minimum-length
refusal below, and hence relative references pass through untouched.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from seshat.redaction_core import replace_fragments

#: Replacement for session material.
REDACTED = "<redacted>"

#: Replacement for an absolute path with no safe workspace-relative form.
REDACTED_PATH = "<redacted-path>"

#: A secret shorter than this is refused rather than applied. High-entropy session
#: material is 43+ characters; anything this short is either a caller mistake or a
#: dictionary word that would corrupt the payload wherever it happened to appear.
_MINIMUM_SECRET_LENGTH = 16


def redact(text: str, secrets: Iterable[str | None]) -> str:
    """Replace every occurrence of each secret in ``text``.

    Empty and ``None`` secrets are dropped -- an empty needle would otherwise become
    a match-everything pattern. A short-but-nonempty secret raises: silently
    ignoring it would leave the caller believing a value was protected, and applying
    it would corrupt innocent text.
    """
    usable: list[str] = []
    for secret in secrets:
        if not secret:
            continue
        if len(secret) < _MINIMUM_SECRET_LENGTH:
            raise ValueError(
                f"refusing to redact a {len(secret)}-character secret: it is too "
                f"short to match safely and would corrupt unrelated text. Session "
                f"material is at least {_MINIMUM_SECRET_LENGTH} characters."
            )
        usable.append(secret)

    if not usable:
        return text
    return replace_fragments(text, usable, REDACTED)


#: How the pinned root itself is named. ``relative_to(root)`` yields ``"."`` for the
#: root, which is safe but tells the reader nothing -- a diagnostic reading
#: "root is ." is worse than useless.
WORKSPACE_ROOT_LABEL = "<workspace root>"


def _relative_or_label(candidate: str, workspace_root: Path) -> str:
    """A workspace-relative reference when contained, else an opaque label."""
    try:
        resolved = Path(candidate).resolve()
    except (OSError, ValueError):  # pragma: no cover - defensive on odd input
        return REDACTED_PATH

    root = workspace_root.resolve()
    if resolved == root:
        return WORKSPACE_ROOT_LABEL
    if root in resolved.parents:
        return resolved.relative_to(root).as_posix()
    return REDACTED_PATH


#: Absolute paths only: a drive-letter root (``C:\\...`` / ``C:/...``) or a POSIX
#: root (``/...``). Deliberately anchored on an absolute root so RELATIVE references
#: -- the safe form Studio is supposed to show -- are never rewritten.
#:
#: The leading ``(?<![^\s"'])`` is load-bearing. Without it the bare ``/``
#: alternative matched mid-token, so the RELATIVE reference
#: ``mappings/retail_store_sales/source-map.yaml`` was rewritten from its first
#: slash onward -- the exact over-redaction defect this module warns about. A real
#: absolute path starts a token: at the beginning of the string, or after
#: whitespace or a quote.
#:
#: The UNC branch (``\\\\server\\share``) is listed FIRST and matched before the
#: others: a UNC path carries no drive letter and does not begin with a single
#: ``/``, so both remaining branches missed it and leaked the server and share
#: names verbatim. Found by adversarial probing, not by the first test pass.
#:
#: ``(?![/\\])`` after the POSIX root rejects ``//`` and ``/\``, so a URL's
#: ``http://host/path`` is not treated as a filesystem path -- the scheme's double
#: slash is what distinguishes it.
_ABSOLUTE_PATH = re.compile(
    r"(?<![^\s\"'])"
    r"(?:"
    r"[\\]{2}[^\s\"'<>|\\/]+[\\/][^\s\"'<>|]*"  # UNC: \\server\share\...
    r"|[A-Za-z]:[\\/][^\s\"'<>|]*"  # drive-letter root
    r"|/(?![/\\])[^\s\"'<>|]*"  # POSIX root, not a URL's //
    r")"
    r"(?<![.,;:])"
)


def redact_paths(text: str, workspace_root: Path) -> str:
    """Rewrite absolute paths in ``text`` to safe references or labels.

    Relative references are left intact: they are already safe, and rewriting them
    would destroy the evidence the reader needs.
    """

    def _replace(match: re.Match[str]) -> str:
        return _relative_or_label(match.group(0), workspace_root)

    return _ABSOLUTE_PATH.sub(_replace, text)


def redact_for_boundary(
    text: str,
    *,
    secrets: Sequence[str | None] = (),
    workspace_root: Path | None = None,
) -> str:
    """The single entry point for anything crossing the Studio boundary.

    Secrets first, then paths: a token that happened to contain path-like characters
    must be removed before the path pass can echo any part of it.
    """
    scrubbed = redact(text, secrets)
    if workspace_root is not None:
        scrubbed = redact_paths(scrubbed, workspace_root)
    return scrubbed
