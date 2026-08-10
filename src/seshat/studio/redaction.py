"""Studio boundary redaction (FR-026).

FR-026: "Studio MUST redact DSNs, passwords, tokens, authorization headers, and
credential-shaped values before any agent event or error reaches the browser."
Three classes, handled differently on purpose:

* **Session material** (bootstrap tokens, cookie values) -- high-entropy, matched
  exactly, replaced wholesale. Nothing useful is lost by removing them.
* **Credentials** (DSNs, passwords, tokens, authorization headers, credential-shaped
  assignments) -- see :func:`redact_credentials`. The KEY survives and only the value
  is replaced, so a diagnostic still says WHICH credential is misconfigured.
* **Absolute filesystem paths** -- rewritten to a workspace-relative reference when
  they are contained by the pinned root, so the reader still learns WHICH file is at
  fault without learning the operator's directory layout. A path outside the root
  has no safe relative form and becomes a label.

**Relationship to `seshat.redaction_core`.** DSN decomposition delegates to that
module -- the ONE hardened libpq/URI authority the repo's other boundary redactors
share -- via ``uri_component_values`` and ``replace_fragments``. An earlier revision
of this docstring argued Studio needed no DSN handling because its secrets were "a
different class, no DSN". That was wrong: FR-026 names DSNs first, and the omission
leaked full connection strings until an adversarial review caught it. Nothing here
re-implements that decomposition.

**Over-redaction is a defect.** ``seshat/dbt/redaction.py`` records the incident:
treating every configured value as a secret rewrote innocent substrings, so the
English word "require" corrupted the governed const "named-human approval required"
and a bare port number matched unrelated digits. Studio exists to project truth, so
a redactor that mangles evidence defeats the feature. Hence the minimum-length
refusal, the credential rules keyed on NAMES rather than key/value shape, and
relative references passing through untouched.

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

from seshat.redaction_core import replace_fragments, uri_component_values

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
    # LONGEST FIRST. `replace_fragments` substitutes in the order given, so a short
    # secret that prefixes a longer one consumed its own text and left the longer
    # secret's remainder in the clear: redacting "abcdefghijklmnop" before
    # "abcdefghijklmnop1234567890" produced "<redacted>1234567890".
    return replace_fragments(text, sorted(usable, key=len, reverse=True), REDACTED)


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
#: The leading lookbehind is load-bearing. Without any lookbehind the bare ``/``
#: alternative matched mid-token, so the RELATIVE reference
#: ``mappings/retail_store_sales/source-map.yaml`` was rewritten from its first
#: slash onward -- the exact over-redaction defect this module warns about. A real
#: absolute path starts a token.
#:
#: The UNC branch (``\\\\server\\share``) is listed FIRST and matched before the
#: others: a UNC path carries no drive letter and does not begin with a single
#: ``/``, so both remaining branches missed it and leaked the server and share
#: names verbatim. Found by adversarial probing, not by the first test pass.
#:
#: ``(?![/\\])`` after the POSIX root rejects ``//`` and ``/\``, so a URL's
#: ``http://host/path`` is not treated as a filesystem path -- the scheme's double
#: slash is what distinguishes it.
#:
#: The lookbehind admits any DELIMITER, not just whitespace and quotes. An earlier
#: revision used ``(?<![^\s"'])``, which required the path to follow whitespace or a
#: quote -- so ``repo=C:\Users\...``, ``(C:\Users\...)``, ``path:C:\Users\...`` and
#: ``[C:\Users\...]`` all leaked the operator's full layout. Those are the COMMONEST
#: diagnostic shapes, and every path test had placed the path after a space, so the
#: gap survived the first green. Found by adversarial review.
#:
#: A word character before the root is still NOT a delimiter: that is what keeps a
#: URL's ``http://...`` and a relative ``mappings/x.yaml`` intact.
_PATH_DELIMITERS = r"\s\"'(<\[{=:,;|"
_ABSOLUTE_PATH = re.compile(
    rf"(?<![^{_PATH_DELIMITERS}])"
    r"(?:"
    r"[\\]{2}[^\s\"'<>|\\/]+[\\/][^\s\"'<>|)\]}]*"  # UNC: \\server\share\...
    r"|[A-Za-z]:[\\/][^\s\"'<>|)\]}]*"  # drive-letter root
    r"|/(?![/\\])[^\s\"'<>|)\]}]*"  # POSIX root, not a URL's //
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


#: Credential NAMES, matched case-insensitively as a whole word inside a key. Keyed
#: on the name rather than on key/value SHAPE: `status: blocked` and
#: `stage: mapping` are key-shaped and carry nothing secret, so a shape-only rule
#: would corrupt the truthful projection Studio exists to provide.
_CREDENTIAL_NAMES = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "authorization",
    "sslpassword",
)

#: `<key-containing-a-credential-name> = <value>` or `: <value>`, to end of line.
#: The KEY is preserved and only the VALUE replaced, so the reader still learns
#: WHICH credential is misconfigured -- the whole point of a diagnostic.
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?P<key>[\w.\-]*(?:" + "|".join(_CREDENTIAL_NAMES) + r")[\w.\-]*)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)

#: `Authorization: Bearer <token>` / `Basic <base64>`. Matched separately because the
#: scheme word must survive while the credential after it must not.
_AUTHORIZATION_HEADER = re.compile(
    r"(?P<scheme>\b(?:Bearer|Basic|Token)\s+)(?P<value>[A-Za-z0-9._~+/=\-]+)",
    re.IGNORECASE,
)


def redact_credentials(text: str) -> str:
    """Redact FR-026's named classes: DSNs, passwords, tokens, auth headers.

    DSN handling delegates to :mod:`seshat.redaction_core`, the ONE hardened libpq
    and URI decomposition every other boundary redactor in this repo uses. An
    earlier revision of this module argued Studio needed no DSN handling because its
    secrets were "a different class" -- but FR-026 names DSNs first, so that
    reasoning was wrong and the omission leaked full connection strings.
    """
    scrubbed = text

    # DSNs first: decompose with the shared authority, then remove every component
    # form it reports. Doing this before the assignment pass means a conninfo
    # `password=...` inside a DSN is already gone.
    for match in _DSN_SHAPED.findall(text):
        components = [
            component
            for component in uri_component_values(match)
            if len(component) >= _MINIMUM_SECRET_LENGTH
        ]
        if components:
            scrubbed = replace_fragments(scrubbed, components, REDACTED)
        scrubbed = scrubbed.replace(match, REDACTED)

    # Auth headers BEFORE assignments, and the order is load-bearing.
    #
    # `_CREDENTIAL_ASSIGNMENT`'s value pattern stops at whitespace, so on
    # `Authorization: Bearer <token>` it consumes only the word `Bearer` and leaves
    # the token itself in the clear. Running the header rule first consumes the
    # scheme AND the token together.
    #
    # The cost is cosmetic: "authorization" is also a credential NAME, so the
    # assignment rule then re-redacts the already-redacted value and the output
    # reads `Authorization: <redacted> <redacted>`. A doubled marker is strictly
    # better than a leaked bearer token, so this order stays.
    scrubbed = _AUTHORIZATION_HEADER.sub(
        lambda m: f"{m.group('scheme')}{REDACTED}", scrubbed
    )
    scrubbed = _CREDENTIAL_ASSIGNMENT.sub(
        lambda m: f"{m.group('key')}{m.group('sep')}{REDACTED}", scrubbed
    )
    return scrubbed


#: A URI-shaped connection string with credentials. Deliberately narrow: it must not
#: match a plain `http://host/path`, which carries no credential.
_DSN_SHAPED = re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s\"'<>|]*@[^\s\"'<>|]*")


def scrub_payload(
    payload: object,
    *,
    secrets: Sequence[str | None] = (),
    workspace_root: Path | None = None,
) -> object:
    """Apply :func:`redact_for_boundary` to every STRING inside a nested payload.

    The response boundary hands out dicts and lists, not strings, so a string-only
    redactor is never actually applied there -- the gap an adversarial review flagged
    as "the module claims it is applied to browser responses; it is applied nowhere".

    Keys are left alone: they are contract field names, fixed by `studio-api.yaml`, and
    rewriting one would produce a payload that fails its own schema. Only VALUES can
    carry a secret or a path.
    """
    if isinstance(payload, str):
        return redact_for_boundary(
            payload, secrets=secrets, workspace_root=workspace_root
        )
    if isinstance(payload, dict):
        return {
            key: scrub_payload(value, secrets=secrets, workspace_root=workspace_root)
            for key, value in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [
            scrub_payload(item, secrets=secrets, workspace_root=workspace_root)
            for item in payload
        ]
    return payload


def redact_for_boundary(
    text: str,
    *,
    secrets: Sequence[str | None] = (),
    workspace_root: Path | None = None,
) -> str:
    """The single entry point for anything crossing the Studio boundary.

    Secrets first, then paths: a token that happened to contain path-like characters
    must be removed before the path pass can echo any part of it.

    **Never raises.** :func:`redact` refuses a secret shorter than
    ``_MINIMUM_SECRET_LENGTH`` because applying it would corrupt innocent text -- but
    letting that ``ValueError`` escape THIS function fails OPEN: it returns control
    to a caller still holding the unsafe text, which then logs or renders it. A short
    secret is genuinely a secret (a 14-character password is real), so the boundary
    replaces every whole-word occurrence of it instead of refusing, and falls back to
    withholding the payload entirely if even that cannot be done.
    """
    try:
        scrubbed = redact(text, secrets)
    except ValueError:
        scrubbed = _redact_short_secrets(text, secrets)

    scrubbed = redact_credentials(scrubbed)
    if workspace_root is not None:
        scrubbed = redact_paths(scrubbed, workspace_root)
    return scrubbed


def _redact_short_secrets(text: str, secrets: Iterable[str | None]) -> str:
    """Whole-word replacement for secrets too short for substring matching.

    Anchoring on word boundaries is what makes a short secret safe to apply: it
    removes ``hunter2hunter2`` as a token without rewriting the letters wherever they
    appear inside unrelated words, which is the corruption
    ``_MINIMUM_SECRET_LENGTH`` exists to prevent.
    """
    scrubbed = text
    for secret in sorted((value for value in secrets if value), key=len, reverse=True):
        scrubbed = re.sub(rf"(?<!\w){re.escape(secret)}(?!\w)", REDACTED, scrubbed)
    return scrubbed
