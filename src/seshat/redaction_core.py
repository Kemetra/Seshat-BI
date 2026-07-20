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
