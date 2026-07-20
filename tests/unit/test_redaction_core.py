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
    conninfo_component_values,
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


# ---------------------------------------------------------------------------
# #392 -- three DSN shapes the shared decomposition still under-scrubbed
# ---------------------------------------------------------------------------


def test_uri_component_values_yields_original_case_hostname() -> None:
    # urlsplit lowercases .hostname, but a driver error prints the host AS TYPED.
    # A case-sensitive str.replace then misses it, so the mixed-case host leaks.
    # The decomposition must yield the original-case host substring too (#392).
    values = uri_component_values("postgresql://u:pw@ProdHost.Example.COM/db")
    assert "ProdHost.Example.COM" in values  # as-typed form must be scrubbable
    assert "prodhost.example.com" in values  # lowercased form still yielded


def test_uri_component_values_scrubs_query_param_credentials() -> None:
    # libpq accepts credentials in the URI query string. Only netloc/path were
    # decomposed, so ?user=..&password=.. leaked entirely (#392).
    values = uri_component_values(
        "postgresql://h/db?user=admin&password=hunter2&sslpassword=k3y"
    )
    assert "admin" in values
    assert "hunter2" in values
    assert "k3y" in values


def test_conninfo_component_values_decomposes_libpq_keyword_string() -> None:
    # A DATABASE_URL may be a libpq keyword conninfo, not a URI. psycopg2 accepts
    # and connects with it, so its reformatted server error leaks user/host with
    # zero component scrub today. A dedicated parser must extract the creds (#392).
    values = conninfo_component_values(
        "host=dbhost.internal user=admin password=hunter2 dbname=prod"
    )
    assert "dbhost.internal" in values
    assert "admin" in values
    assert "hunter2" in values
    assert "prod" in values


def test_conninfo_component_values_non_conninfo_returns_empty() -> None:
    # A URI or a bare token is not keyword conninfo -> nothing to extract here
    # (the URI path handles URIs; this sibling only handles key=value shapes).
    assert conninfo_component_values("postgresql://u:pw@h/db") == ()
    assert conninfo_component_values("just-a-token") == ()


def test_uri_components_unions_conninfo_and_uri_shapes() -> None:
    # The public entry point must cover BOTH shapes so every consumer benefits.
    frags = uri_components(["host=h.internal user=admin password=hunter2 dbname=prod"])
    assert "admin" in frags
    assert "hunter2" in frags
    assert "h.internal" in frags


# ---------------------------------------------------------------------------
# #392 review follow-ups (adversarial gate on the #392/#393 PR)
# ---------------------------------------------------------------------------


def test_uri_component_values_empty_authority_uri_with_query_creds() -> None:
    # The PostgreSQL-manual URI form 'postgresql:///db?host=..&user=..&password=..'
    # has an EMPTY netloc but carries all credentials in the query. The netloc gate
    # must not short-circuit before the query extraction runs, or user/password/
    # host/dbname all leak (adversarial-review BLOCKER).
    values = uri_component_values(
        "postgresql:///mydb?host=localhost&user=admin&password=hunter2"
    )
    assert "admin" in values
    assert "hunter2" in values
    assert "localhost" in values


def test_original_case_host_not_masked_by_matching_userinfo() -> None:
    # When the (lowercase) userinfo equals the lowercased host, a first-occurrence
    # find() slices the userinfo run and the AS-TYPED host is never yielded, so it
    # leaks. Recovery must look only after the last '@' (adversarial-review MAJOR).
    values = uri_component_values(
        "postgresql://host.example.com:pw@Host.Example.COM/db"
    )
    assert "Host.Example.COM" in values  # as-typed host must be scrubbable


def test_conninfo_handles_spaces_around_equals() -> None:
    # libpq permits spaces around '=' ("host = h user = u"); psycopg2 connects with
    # it, so it must scrub too (honest-scope gap the review flagged).
    values = conninfo_component_values("host = h.internal user = admin password = pw")
    assert "admin" in values
    assert "pw" in values
    assert "h.internal" in values


def test_conninfo_strips_quotes_from_single_token_values() -> None:
    # A quoted single-token value (password='hunter2') must yield the bare form too,
    # else a server error printing 'hunter2' unquoted is missed.
    values = conninfo_component_values("user='admin' password='hunter2'")
    assert "hunter2" in values
    assert "admin" in values
