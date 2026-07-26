"""Shared URI-credential decomposition + fragment replacement (issue #365).

The single source of truth for splitting a DSN-shaped secret into its individual
credential components and for the token-parameterized fragment replace that every
boundary redactor performs. Extracted from three previously-duplicated copies
(``seshat.dbt.redaction``, ``seshat.dagster_adapter.redaction``,
``seshat.portfolio_enumerate``) so the hardened decomposition lives in ONE place.

Callers keep their own replacement token (``[REDACTED-ENV]`` vs ``<redacted>``)
by passing it to :func:`replace_fragments`; the decomposition itself is
token-agnostic. This module is a stdlib-only leaf -- it imports nothing from
``seshat``, so it can never introduce an import cycle.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import unquote, urlsplit

# libpq credential keywords that may appear either as URI query params
# (`?user=..&password=..`) or as keyword conninfo (`user=.. password=..`). Host
# and dbname are connection CONTEXT that also leaks in a reformatted driver error.
_LIBPQ_SECRET_KEYS = ("user", "password", "sslpassword", "host", "hostaddr", "dbname")


def _both_forms(values: Iterable[str]) -> set[str]:
    """Every non-empty value plus its percent-decoded form (a driver prints either)."""
    return {form for value in values if value for form in (value, unquote(value))}


def _secret_key_value(pair: str) -> str | None:
    """The value of one ``key=value`` fragment when ``key`` names a libpq secret.

    The single shared gate for both the URI-query and keyword-conninfo parsers:
    split on the first ``=``, require a non-empty value, and require the key to be
    a credential keyword. Returns ``None`` otherwise, so each caller stays a flat
    comprehension (no compound conditional inline).
    """
    key, sep, value = pair.partition("=")
    if not sep or not value:
        return None
    return value if key.strip().lower() in _LIBPQ_SECRET_KEYS else None


def _original_case_host(netloc: str, hostname: str | None) -> tuple[str, ...]:
    """Recover the host substring AS TYPED in ``netloc``.

    ``urlsplit(...).hostname`` is lowercased, but a driver error prints the host in
    its original case, so a case-sensitive replace of the lowercased form misses it
    (#392). Slice the original-case run back out of the netloc's HOST portion --
    the part after the last ``@`` -- so a userinfo that equals the lowercased host
    cannot mask it (first-occurrence ``find`` would otherwise slice the userinfo
    and leak the real host; adversarial-review MAJOR). Over-recovery is harmless
    (the redactor's fail-safe direction); a miss falls back to the lowercased form.
    """
    if not hostname:
        return ()
    host_portion = netloc.rpartition("@")[2]  # drop any user:pw@ prefix
    idx = host_portion.lower().find(hostname)
    if idx == -1:
        return ()
    return (host_portion[idx : idx + len(hostname)],)


def _query_secret_values(query: str) -> set[str]:
    """Credential values carried in a URI query string (``user=..&password=..``).

    libpq allows credentials in the query; both raw and percent-decoded forms are
    yielded. Split manually (not ``parse_qs``) so RFC-3986 semantics hold -- a
    literal ``+`` in a password stays ``+`` rather than being turned into a space.
    """
    values = [value for pair in query.split("&") if (value := _secret_key_value(pair))]
    return _both_forms(values)


def uri_component_values(secret: str) -> tuple[str, ...]:
    """Return the individual credential components of a URI-shaped secret.

    A DATABASE_URL-only config stores the DSN as one opaque value; a *reformatted*
    driver error (`connection to server at "host" ... for user "u"`) contains the
    host/user components but neither the verbatim DSN nor a `scheme://`, so a
    whole-value replace misses them. Decomposing the URI lets each component be
    scrubbed on its own. Both the raw and percent-decoded form of every non-empty
    component are yielded (an error may print either). Non-URI secrets yield the
    empty tuple.

    The netloc-derived parts are gated on ``netloc`` presence, NOT ``scheme``:
    credentials live in the netloc (``//user:pw@host``), and a scheme-relative DSN
    carries them without a ``scheme://``. Requiring a scheme dropped those on the
    floor. urlsplit itself is TOTAL here -- a malformed URI (e.g. a bad IPv6 literal
    raises ValueError) yields ``()`` rather than propagating, so every boundary
    redactor that runs WHILE formatting an error is shielded at the core, once,
    instead of each caller guarding case-by-case (#385 follow-through).

    Coverage additionally spans (#392): the host in its ORIGINAL case (urlsplit
    lowercases it) and credentials carried in the URI QUERY string
    (``?user=..&password=..``), which libpq accepts. The query is handled even when
    the authority is EMPTY (``postgresql:///db?host=..&user=..&password=..`` -- a
    PostgreSQL-manual form that carries every credential in the query), so the
    netloc gate must not short-circuit before it (adversarial-review BLOCKER).
    """
    try:
        parsed = urlsplit(secret)
    except ValueError:
        return ()
    components = _query_secret_values(parsed.query)
    if parsed.netloc:
        components |= _both_forms(
            (
                parsed.username,
                parsed.password,
                parsed.hostname,
                parsed.path.lstrip("/"),
            )
        )
        components.update(_original_case_host(parsed.netloc, parsed.hostname))
    return tuple(components)


def dsn_dbname(dsn: str) -> str | None:
    """The DATABASE NAME carried by a DSN, or ``None`` when it carries none.

    A narrow, single-purpose accessor added for the #485 provenance comparison,
    which needs one named component rather than the undifferentiated credential
    soup :func:`uri_components` returns. It lives HERE, beside the hardened
    decomposition, rather than in the caller: a second hand-rolled DSN parser is
    exactly the drift the #365/#366 consolidation removed.

    Covers both shapes a ``DATABASE_URL`` may take, because psycopg2 connects with
    either:

      * the URI form (scheme, then ``userinfo``, then ``@host:port/dbname``) -> the
        path segment, percent-DECODED (a database name may legitimately contain an
        escaped character, and the server echoes the decoded name). Described in
        words rather than shown: a literal scheme-userinfo-at-sign sequence in this
        file is the shape the C2 secret-scanner (correctly) flags as a possibly
        committed DSN, exactly as ``validate.resolve_dsn`` notes at its own
        assembly;
      * the libpq KEYWORD conninfo form ``host=h dbname=d user=u`` -> the
        ``dbname=`` value, with matching single quotes stripped.

    Returns ``None`` for an empty/absent name, a malformed URI (``urlsplit`` can
    raise on a bad IPv6 literal -- total here, like every other function in this
    module), or a string that declares no database at all. The caller must treat
    ``None`` as "cannot determine", never as agreement.
    """
    try:
        parsed = urlsplit(dsn)
    except ValueError:
        return None
    name = unquote(parsed.path.lstrip("/")).strip()
    if name and (parsed.netloc or parsed.scheme):
        return name
    return _conninfo_dbname(dsn)


def dsn_host(dsn: str) -> str | None:
    """The HOST carried by a DSN, lowercased, or ``None`` when it carries none.

    The sibling of :func:`dsn_dbname`, added for the same #485 comparison and
    living here for the same reason: one hardened decomposition, never a second
    hand-rolled parser. Covers the URI authority (``//user:pw@host:5432/db``) and
    the libpq keyword form (``host=h dbname=d``), and reads the URI QUERY too
    (``postgresql:///db?host=h`` -- a PostgreSQL-manual form that carries the host
    there).

    Lowercased deliberately: hostnames are case-insensitive, so ``DB.Example.com``
    and ``db.example.com`` are the SAME target and must digest identically. This
    is the opposite of the redaction path's original-case recovery -- redaction
    over-recovers to avoid a leak, whereas comparison must normalize to avoid a
    false mismatch.

    Returns ``None`` for an absent host or a malformed URI (total, like every
    other function here). The caller must treat ``None`` as "cannot determine",
    never as agreement.
    """
    try:
        parsed = urlsplit(dsn)
    except ValueError:
        return None
    if parsed.hostname:
        return parsed.hostname.strip().lower() or None
    return _conninfo_value(dsn, "host") or _query_value(dsn, "host")


def dsn_port(dsn: str) -> str | None:
    """The PORT carried by a DSN as a string, or ``None`` when it carries none.

    A string, not an int, because it is a digest component and the digest must be
    byte-stable: ``"5432"`` and ``5432`` would otherwise depend on the caller's
    formatting. Covers the URI authority, the libpq ``port=`` keyword, and the URI
    query. Malformed input yields ``None`` (total, like every function here) --
    ``urlsplit.port`` raises ValueError on a non-numeric port, which is caught.
    """
    try:
        parsed = urlsplit(dsn)
        if parsed.port is not None:
            return str(parsed.port)
    except ValueError:
        return _conninfo_value(dsn, "port")
    return _conninfo_value(dsn, "port") or _query_value(dsn, "port")


def _query_value(dsn: str, key: str) -> str | None:
    """The value of one query-string key, lowercased, or ``None``."""
    try:
        query = urlsplit(dsn).query
    except ValueError:
        return None
    for pair in query.split("&"):
        name, sep, value = pair.partition("=")
        if sep and name.strip().lower() == key and value:
            return unquote(value).strip().lower() or None
    return None


def _conninfo_dbname(dsn: str) -> str | None:
    """The ``dbname=`` value of a libpq keyword conninfo string, or ``None``."""
    return _conninfo_value(dsn, "dbname", lower=False)


def _conninfo_value(dsn: str, key: str, *, lower: bool = True) -> str | None:
    """The value of one keyword-conninfo key, or ``None``.

    Shares :func:`_is_single_quoted` with the redaction path so a quoted value
    (``host='db.example.com'``) yields its bare form here too.
    """
    if "=" not in dsn:
        return None
    normalized = re.sub(r"\s*=\s*", "=", dsn)
    for token in normalized.split():
        name, sep, value = token.partition("=")
        if sep and name.strip().lower() == key and value:
            bare = value[1:-1] if _is_single_quoted(value) else value
            bare = bare.strip()
            return (bare.lower() if lower else bare) or None
    return None


def _is_single_quoted(value: str) -> bool:
    """True when ``value`` is wrapped in matching single quotes (length >= 2).

    A lone ``'`` is NOT quoted; excluding it keeps the empty bare-form out of
    :func:`_unquote_single` (an empty fragment would make ``replace_fragments`` an
    insert-everywhere hazard).
    """
    if len(value) < 2:
        return False
    return value.startswith("'") and value.endswith("'")


def _unquote_single(value: str) -> tuple[str, ...]:
    """A value plus, if it is wrapped in matching single quotes, its bare form."""
    return (value, value[1:-1]) if _is_single_quoted(value) else (value,)


def _conninfo_secret_forms(token: str) -> tuple[str, ...]:
    """The scrubbable forms of one ``key=value`` token whose key names a secret.

    Yields the value as-written AND, when it is wrapped in matching single quotes,
    the quote-stripped form too (a server error prints the bare value). Returns
    ``()`` for a non-``key=value`` token, an empty value, or a non-credential key.
    """
    value = _secret_key_value(token)
    return _unquote_single(value) if value is not None else ()


def conninfo_component_values(secret: str) -> tuple[str, ...]:
    """Return the credential components of a libpq KEYWORD conninfo string.

    A ``DATABASE_URL`` may be a libpq keyword/value string
    (``host=h user=u password=p dbname=d``) rather than a URI. psycopg2 accepts and
    CONNECTS with it, so its reformatted server error leaks user/host with no scrub
    unless the keyword form is decomposed too (#392). This is the sibling of
    :func:`uri_component_values` for the non-URI shape; keeping them separate keeps
    each parser single-purpose and directly testable.

    Handles the whitespace-separated ``key=value`` form, spaces around ``=``
    (``host = h`` -- libpq permits it), and a single-token quoted value
    (``password='hunter2'`` yields both the quoted and bare forms).

    SCOPE (honest): does NOT implement full libpq quoting -- a QUOTED value that
    itself contains whitespace (``password='a b'``) is not reassembled (the ``a``
    and ``b`` tokens are seen separately), and backslash escapes are not decoded.
    A string with no ``=`` yields ``()``. This is deliberately a narrow, low-risk
    extractor, not a complete libpq parser.
    """
    if "=" not in secret:
        return ()
    # Collapse optional spaces around '=' so `host = h` tokenizes like `host=h`.
    normalized = re.sub(r"\s*=\s*", "=", secret)
    values = [
        form for token in normalized.split() for form in _conninfo_secret_forms(token)
    ]
    return tuple(dict.fromkeys(values))


def uri_components(secrets: Iterable[str]) -> tuple[str, ...]:
    """Return the deduped union of every secret's components, longest first.

    Covers BOTH the URI shape (:func:`uri_component_values`) and the libpq keyword
    conninfo shape (:func:`conninfo_component_values`), so every boundary redactor
    scrubs credentials regardless of which DSN form the config used. Sorted by
    length descending so a component that is a substring of a longer one is
    replaced first, and no partial fragment survives.
    """
    components = {
        component
        for secret in secrets
        for component in (
            *uri_component_values(secret),
            *conninfo_component_values(secret),
        )
    }
    return tuple(sorted(components, key=len, reverse=True))


def replace_fragments(text: str, fragments: Iterable[str], token: str) -> str:
    """Replace every fragment in ``text`` with ``token`` (no-op when absent)."""
    for fragment in fragments:
        text = text.replace(fragment, token)
    return text
