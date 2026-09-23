"""C2 content-scan helpers: secret-shape patterns, text decoding, per-line scan.

Split out of ``git_meta`` (which registers C2) so the scanning seam stays small
and testable on its own. This module registers NO rule. ``git_meta`` re-exports
the names its callers and tests already import.

Comment discipline: like ``git_meta`` before it, nothing in this file spells a
literal that its own patterns (or the release artifact inspector) would match.
Shapes are described in prose, never embedded as examples.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..core import Finding, Severity

# A real DigitalOcean endpoint: a concrete subdomain label (alnum start, then
# alnum/hyphen) directly before `.db.ondigitalocean.com`. `>` from an
# angle-bracket placeholder cannot sit in the label class, so a bracketed
# placeholder host does NOT match.
#
# ReDoS-safe: the label run is BOUNDED ({0,253}, the DNS host-name max) rather
# than an unbounded `*`, so backtracking is capped to a constant per start
# position and the match is O(n) over the line.
DO_ENDPOINT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,253}\.db\.ondigitalocean\.com")
CONN_URI_RE = re.compile(r"postgres(?:ql)?://[^@\s]+@")
# A DigitalOcean managed-database CLUSTER SLUG: `db-<engine>-<region><digit>-<id>`.
# Not a secret on its own, but real connection context the hard rule forbids.
# The `<...>` placeholder cannot appear inside the character classes, so a
# documented placeholder slug does NOT match.
DO_CLUSTER_SLUG_RE = re.compile(r"\bdb-[a-z]{2,}-[a-z]{2,}\d-\d{3,}\b")

# The VALUE class shared by the credential-keyword patterns. It deliberately
# excludes an angle-bracket token (documented placeholder), a curly brace (an
# f-string/format interpolation -- source code building the string), a `$` or
# parenthesis (a shell/Make substitution), quotes and square brackets (a code
# subscript or a quoted expression), and the separator / whitespace / slash (so
# prose naming the keywords side by side cannot look like an assignment).
_CRED_VALUE = r"[^;\s{}<>/$()\"'`\[\]]+"

# The two ODBC credential keywords in their canonical upper-case spelling, with
# no whitespace around the equals sign (the historical C2 shape).
ODBC_SECRET_RE = re.compile(r"\b(?:PWD|UID)=" + _CRED_VALUE)

# Connection-string keywords in ANY case, including the ADO.NET password
# keyword. Driver managers treat these keywords case-insensitively, so a
# lower-case credential is just as live. Because a lower-case keyword also
# appears in ordinary code (keyword arguments), this form requires
# connection-string CONTEXT: the pair must be preceded or followed by the `;`
# separator, with no whitespace around the equals sign (so a SQL predicate that
# compares a column of that name is not mistaken for a credential).
_CONN_KEYS = r"(?:pwd|uid|password)"
CONN_STRING_CRED_RE = re.compile(
    r"(?i)(?:;\s*"
    + _CONN_KEYS
    + "="
    + _CRED_VALUE
    + r"|\b"
    + _CONN_KEYS
    + "="
    + _CRED_VALUE
    + ";)"
)

# The scheme is assembled from parts so this source file never itself contains
# the full scheme-then-userinfo-then-at-sign literal shape the pattern catches.
_MYSQL_SCHEME = "mysql" + ":" + "//"
MYSQL_URI_RE = re.compile(re.escape(_MYSQL_SCHEME) + r"[^@\s<>]+@")

# Snowflake kwargs pair: an account key and a password key, each with a REAL
# value, on the same line. A value is accepted only when it is a quoted string
# OR an unquoted token NOT immediately followed by `.` or `(` (which would mark
# it as a name/attribute/call reference in source that builds the dict).
_SNOWFLAKE_KV_RE = re.compile(
    r"[\"']?(account|password)[\"']?\s*[:=]\s*([\"']?)([^,;\s\"'{}()<>]*)",
    re.IGNORECASE,
)

# A `.env`-style KEY=VALUE line whose KEY names a credential. Only applied to
# env-style files (see ``is_env_style``), where every line is an assignment.
_ENV_SECRET_KEY_RE = re.compile(
    r"(?i)^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|PWD)"
    r"[A-Z0-9_]*\s*=\s*(?P<value>\S.*)$"
)
_PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def _snowflake_kv_is_real(quote: str, value: str, line: str, end_pos: int) -> bool:
    if not value:
        return False
    is_unquoted = not quote
    has_next_char = end_pos < len(line)
    next_is_ref = has_next_char and line[end_pos] in ".("
    if is_unquoted and next_is_ref:
        return False  # unquoted + followed by '.'/'(' -> a name/call reference
    return True


def _has_snowflake_secret_pair(line: str) -> bool:
    seen: dict[str, bool] = {}
    for m in _SNOWFLAKE_KV_RE.finditer(line):
        key, quote, value = m.group(1).lower(), m.group(2), m.group(3)
        if _snowflake_kv_is_real(quote, value, line, m.end(3)):
            seen[key] = True
    return seen.get("account", False) and seen.get("password", False)


def scan_line_for_secret(line: str) -> bool:
    """True if ``line`` carries a committed connection string / secret shape.

    Excludes the DO cluster-slug shape, which ``scan_file_lines`` reports as a
    SEPARATE, less severe-sounding Finding message (not "a secret").
    """
    # DO_ENDPOINT_RE is gated behind an O(n) substring check: any real endpoint
    # MUST contain this literal, so the prefilter is a necessary condition and
    # only the pathological scan is skipped.
    do_hit = ".db.ondigitalocean.com" in line and bool(DO_ENDPOINT_RE.search(line))
    return (
        bool(CONN_URI_RE.search(line))
        or do_hit
        or bool(ODBC_SECRET_RE.search(line))
        or bool(CONN_STRING_CRED_RE.search(line))
        or bool(MYSQL_URI_RE.search(line))
        or _has_snowflake_secret_pair(line)
    )


def is_env_style(path: str) -> bool:
    """True for a `.env` file or a `.env.<suffix>` variant, at any depth."""
    name = PurePosixPath(path).name
    return name == ".env" or name.startswith(".env.")


def is_env_template(path: str) -> bool:
    """True for an env-style TEMPLATE (``*.example``), which may be tracked."""
    return is_env_style(path) and path.endswith(".example")


def env_line_has_secret(line: str) -> bool:
    """True for an env-style assignment of a non-placeholder credential value."""
    m = _ENV_SECRET_KEY_RE.match(line)
    if m is None or line.lstrip().startswith("#"):
        return False
    value = m.group("value").strip().strip("\"'")
    return bool(value) and not _PLACEHOLDER_RE.search(value)


def _finding(path: str, lineno: int, message: str) -> Finding:
    return Finding(
        rule_id="C2",
        severity=Severity.ERROR,
        message=message,
        locator=f"{path}:{lineno}",
    )


_SECRET_MESSAGE = "possible committed connection string / secret"
_SLUG_MESSAGE = (
    "committed DigitalOcean cluster slug (real connection context) -- move it "
    "to the gitignored .env"
)


def scan_file_lines(path: str, text: str) -> list[Finding]:
    """Findings for one file's content, one entry per offending line.

    A secret-shaped line and a cluster-slug line are reported with distinct
    messages (the slug is real connection context, not a secret). An env-style
    file additionally flags any credential-named key carrying a real value.
    """
    env_style = is_env_style(path)
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if scan_line_for_secret(line) or (env_style and env_line_has_secret(line)):
            findings.append(_finding(path, lineno, _SECRET_MESSAGE))
        elif DO_CLUSTER_SLUG_RE.search(line):
            findings.append(_finding(path, lineno, _SLUG_MESSAGE))
    return findings


_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


def _looks_utf16_without_bom(raw: bytes) -> str | None:
    """``utf-16-le``/``utf-16-be`` when ``raw`` is BOM-less UTF-16 text, else None.

    ASCII-range text in UTF-16 puts a NUL in every other byte; a binary file's
    NULs are not that regular. Judged on a bounded prefix.
    """
    head = raw[:512]
    if len(head) < 4:
        return None
    odd, even = head[1::2], head[0::2]
    if odd.count(0) >= 0.9 * len(odd) and even.count(0) == 0:
        return "utf-16-le"
    if even.count(0) >= 0.9 * len(even) and odd.count(0) == 0:
        return "utf-16-be"
    return None


def decode_for_scan(raw: bytes) -> str | None:
    """Decode a tracked file for the secret scan, or ``None`` for a binary file.

    Order: a UTF-16 BOM -> UTF-16; a UTF-8 BOM -> UTF-8; otherwise a NUL byte
    marks either BOM-less UTF-16 text (decoded) or a binary file (skipped); then
    UTF-8; then Latin-1, which never fails, so a cp1252 or other 8-bit text file
    is still scanned (the secret shapes are all ASCII).
    """
    if raw.startswith(_UTF16_BOMS):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    if b"\x00" in raw:
        codec = _looks_utf16_without_bom(raw)
        return raw.decode(codec, errors="replace") if codec else None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")
