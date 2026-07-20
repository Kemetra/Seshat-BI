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

from collections.abc import Iterable
from urllib.parse import unquote, urlsplit


def uri_component_values(secret: str) -> tuple[str, ...]:
    """Return the individual credential components of a URI-shaped secret.

    A DATABASE_URL-only config stores the DSN as one opaque value; a *reformatted*
    driver error (`connection to server at "host" ... for user "u"`) contains the
    host/user components but neither the verbatim DSN nor a `scheme://`, so a
    whole-value replace misses them. Decomposing the URI lets each component be
    scrubbed on its own. Both the raw and percent-decoded form of every non-empty
    component are yielded (an error may print either). Non-URI secrets yield the
    empty tuple.
    """
    parsed = urlsplit(secret)
    if not parsed.scheme or not parsed.netloc:
        return ()
    raw = (parsed.username, parsed.password, parsed.hostname, parsed.path.lstrip("/"))
    return tuple(
        component for value in raw if value for component in (value, unquote(value))
    )


def uri_components(secrets: Iterable[str]) -> tuple[str, ...]:
    """Return the deduped union of every secret's URI components, longest first.

    Sorted by length descending so a component that is a substring of a longer
    one is replaced first, and no partial fragment survives.
    """
    components = {
        component for secret in secrets for component in uri_component_values(secret)
    }
    return tuple(sorted(components, key=len, reverse=True))


def replace_fragments(text: str, fragments: Iterable[str], token: str) -> str:
    """Replace every fragment in ``text`` with ``token`` (no-op when absent)."""
    for fragment in fragments:
        text = text.replace(fragment, token)
    return text
