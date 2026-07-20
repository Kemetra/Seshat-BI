"""Direct guarantees of the shared URI-credential decomposition (issue #365).

``redaction_core`` is the single hardened source of truth reused by every
boundary redactor (cli, dbt, dagster_adapter, portfolio_enumerate,
readiness_evidence). Testing ``uri_component_values`` directly -- not only
through one consumer -- is what stops a future core refactor from silently
regressing all of them at once (adversarial review, #385 follow-through).
"""

from __future__ import annotations

import pytest

from seshat.redaction_core import (
    replace_fragments,
    uri_component_values,
    uri_components,
)

pytestmark = pytest.mark.unit


def test_uri_component_values_scheme_relative_dsn_is_decomposed() -> None:
    # A credential-bearing but scheme-relative DSN (`//user:pw@host/db`, no
    # `scheme://`) must still decompose: credentials live in the netloc, which
    # urlsplit populates from the leading `//`. Gating on scheme dropped these on
    # the floor -- the exact "weaker than the deleted code" gap the dedup created.
    values = uri_component_values("//admin:s3cret@prod-host/prod_db")
    assert "admin" in values
    assert "s3cret" in values
    assert "prod-host" in values
    assert "prod_db" in values  # db-name (path) too


def test_uri_component_values_full_scheme_dsn_still_decomposed() -> None:
    # Regression guard for the common case: the scheme+netloc path is unchanged.
    values = uri_component_values("postgresql://u:p@h:5432/db")
    assert {"u", "p", "h", "db"} <= set(values)


def test_uri_component_values_percent_decoded_forms_included() -> None:
    # Both the raw (percent-encoded) and decoded forms are yielded: a driver may
    # print either. Password 'p@ss' is stored as 'p%40ss'.
    values = uri_component_values("postgresql://u:p%40ss@h/db")
    assert "p%40ss" in values  # raw
    assert "p@ss" in values  # decoded


def test_uri_component_values_non_uri_returns_empty() -> None:
    # A bare non-URI secret (no netloc) has nothing to decompose.
    assert uri_component_values("just-a-plain-token") == ()
    assert uri_component_values("user:pw@host") == ()  # no leading // => no netloc


def test_uri_component_values_malformed_dsn_returns_empty_not_raises() -> None:
    # urlsplit raises ValueError on a bad IPv6 literal. The primitive must be TOTAL
    # -- return () rather than propagate -- so every boundary redactor that runs
    # WHILE formatting an error is shielded at the core, not case-by-case.
    assert uri_component_values("postgresql://u:pw@[::1") == ()
    assert uri_components(["postgresql://u:pw@[::1", "postgresql://a:b@h/db"]) == (
        # the well-formed sibling still decomposes; the malformed one contributes
        # nothing instead of crashing the whole call.
        *uri_components(["postgresql://a:b@h/db"]),
    )


def test_replace_fragments_replaces_each_fragment() -> None:
    out = replace_fragments("a b c", ("a", "c"), "X")
    assert out == "X b X"
